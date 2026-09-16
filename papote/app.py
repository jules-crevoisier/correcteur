# -*- coding: utf-8 -*-
"""Assemblage de l'application : raccourci -> selection -> correction -> collage."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
import traceback
from typing import Callable

from . import apprentissage as apprentissage_mod
from . import config as config_mod
from . import demarrage, frappe as frappe_mod, journal as journal_mod
from . import lexique, maj, moteur
from . import politique as politique_mod
from . import presse_papier
from .raccourci import Raccourci, RaccourciInvalide


class Application:
    """Le correcteur, pret a etre pilote par une interface ou en ligne de commande."""

    def __init__(self, config: dict | None = None,
                 journal: Callable[[str], None] | None = None):
        self.config = config or config_mod.charger()
        # Le journal part sur la sortie d'erreur — « --texte » doit pouvoir
        # etre redirige sans ramasser les messages de chargement — et dans le
        # fichier, seul endroit ou l'on puisse relire ce qui s'est passe une
        # fois l'application compilee.
        self.journal = journal or self._consigner
        self.actif = True
        self._correcteurs: dict[str, moteur.Correcteur] = {}
        self._lexique: lexique.Lexique | None = None
        self._verrou = threading.Lock()
        self._ecoute: frappe_mod.EcouteClavier | None = None

        self.politique = politique_mod.depuis_config(self.config)
        self.journal_habitudes = apprentissage_mod.charger()
        self._corrections_depuis_sauvegarde = 0

        # Les mots que l'utilisateur a retablis a la main : ce sont ceux qu'il
        # veut voir entrer dans son dictionnaire, et la fenetre les lui
        # proposera.
        self.mots_retablis: list[str] = []
        # Les regles qu'il annule sans cesse : la fenetre proposera de les
        # eteindre.
        self.regles_contestees: list[str] = []

        # La version telechargee qui attend le prochain demarrage, s'il y en a.
        self.maj_prete: maj.Version | None = None

        self.raccourcis: list[Raccourci] = []
        self._installer_raccourcis()

    @staticmethod
    def _consigner(message: str) -> None:
        print(message, file=sys.stderr)
        journal_mod.ecrire(message)

    # -- raccourcis ---------------------------------------------------------

    def _installer_raccourcis(self) -> None:
        """Relit les combinaisons choisies par l'utilisateur."""
        self.raccourcis = [
            Raccourci(self.config.get("raccourci", ""), self.sur_raccourci),
            Raccourci(self.config.get("raccourci_annuler", ""), self.annuler),
            Raccourci(self.config.get("raccourci_fenetre", ""), self.ouvrir_fenetre),
            Raccourci(self.config.get("raccourci_relecture", ""), self.relire),
        ]

    def _activer_raccourcis(self) -> None:
        for raccourci in self.raccourcis:
            try:
                raccourci.activer()
            except RaccourciInvalide as e:
                self.journal(str(e))
                self.notifier("Raccourci refusé", str(e))

    def _desactiver_raccourcis(self) -> None:
        for raccourci in self.raccourcis:
            raccourci.desactiver()

    def _lancer(self, *arguments: str) -> bool:
        """Relance Papote avec d'autres arguments, dans un processus a part.

        pystray occupe deja la boucle d'evenements du processus et tkinter
        exige la sienne ; les faire cohabiter est une source de blocages, un
        second processus n'en est pas une.
        """
        commande = ([sys.executable] if getattr(sys, "frozen", False)
                    else [sys.executable, "-m", "papote"])
        try:
            subprocess.Popen(commande + list(arguments))
            return True
        except OSError as e:
            self.notifier("Fenêtre", f"Ouverture impossible : {e}")
            return False

    def ouvrir_fenetre(self) -> None:
        self._lancer("--fenetre")

    def relire(self) -> None:
        """Capture la selection et montre les corrections avant de les poser."""
        threading.Thread(target=self._relire, daemon=True).start()

    def _relire(self) -> None:
        try:
            texte = presse_papier.capturer_selection(
                delai=self.config.get("delai_copie", 0.35)
            )
        except Exception:
            self.journal(traceback.format_exc())
            return

        if not texte:
            self.notifier("Rien à relire",
                          "Sélectionnez d'abord le texte à relire.")
            return

        # On rend sa selection au presse-papiers : la capture l'avait videe.
        try:
            presse_papier.ecrire(texte)
        except Exception:
            pass

        chemin = config_mod.dossier_config() / "relecture.txt"
        try:
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(texte, encoding="utf-8")
        except OSError as e:
            self.notifier("Relecture", f"Impossible : {e}")
            return

        self._lancer("--relecture", str(chemin))

    # -- preparation --------------------------------------------------------

    @property
    def correcteur(self) -> moteur.Correcteur:
        """Le correcteur du registre par defaut."""
        return self.correcteur_pour(self.config.get("registre", politique_mod.PARLE))

    def correcteur_pour(self, registre: str) -> moteur.Correcteur:
        """Le correcteur d'un registre donne, construit au premier usage.

        Les deux registres partagent le meme dictionnaire : seul le jeu de
        regles change, et il ne coute rien.
        """
        if registre in self._correcteurs:
            return self._correcteurs[registre]

        with self._verrou:
            if registre in self._correcteurs:
                return self._correcteurs[registre]
            if self._lexique is None:
                self.journal("Chargement du dictionnaire...")
                self._lexique = lexique.Lexique()
                self._lexique.charger()
                self.journal("Papote pret.")
            self._correcteurs[registre] = moteur.depuis_config(
                self.config, self._lexique, registre
            )
        return self._correcteurs[registre]

    @property
    def ecoute(self) -> frappe_mod.EcouteClavier:
        """La correction au fil de la frappe, construite au premier besoin."""
        if self._ecoute is None:
            self._ecoute = frappe_mod.EcouteClavier(
                frappe_mod.Frappe(self.correcteur),
                delai_oubli=self.config.get("delai_oubli", 5.0),
                sur_correction=self._signaler_correction,
                sur_annulation=self._signaler_annulation,
                politique=self.politique,
                correcteur_pour=self.correcteur_pour,
            )
        return self._ecoute

    def prechauffer(self) -> None:
        """Charge le dictionnaire en arriere-plan, pour que la 1re correction soit rapide.

        Un echec ici — des donnees manquantes, par exemple — doit se voir tout
        de suite. Lancee au demarrage de Windows, l'application serait sinon
        presente dans la barre des taches sans jamais rien corriger.
        """
        def _demarrer():
            try:
                self.correcteur  # noqa: B018 — declenche le chargement
            except lexique.LexiqueIntrouvable as e:
                journal_mod.erreur("dictionnaire introuvable", e)
                self.notifier("Dictionnaire introuvable", str(e).split("\n")[0])
                return
            except Exception as e:
                journal_mod.erreur("le dictionnaire n'a pas pu etre charge", e)
                self.notifier("Papote indisponible",
                              "Le dictionnaire n'a pas pu être chargé. "
                              "Détails dans le journal.")
                return

            if not self.config.get("correction_auto", True):
                return

            # La frappe ne s'ecoute qu'une fois le dictionnaire en place : un
            # crochet clavier qui met un dixieme de seconde a repondre se sent
            # tout de suite.
            #
            # Et son echec n'est pas celui du dictionnaire : le crochet peut
            # etre refuse par le systeme sans que rien d'autre soit casse. Le
            # dire clairement evite d'envoyer chercher un probleme la ou il
            # n'est pas — le raccourci, lui, continue de fonctionner.
            try:
                self.ecoute.activer()
                self.journal("Correction au fil de la frappe active.")
            except Exception as e:
                journal_mod.erreur(
                    "la correction au fil de la frappe n'a pas pu demarrer", e)
                self.notifier(
                    "Correction automatique indisponible",
                    f"Le raccourci {self.config.get('raccourci', '')} reste "
                    f"actif. Détails dans Réglages → Ouvrir le journal.",
                )

        threading.Thread(target=_demarrer, daemon=True).start()

    # -- correction ---------------------------------------------------------

    def corriger_texte(self, texte: str) -> tuple[str, list]:
        return self.correcteur.corriger(texte)

    def sur_raccourci(self) -> None:
        """Reaction a l'appui du raccourci global."""
        if not self.actif:
            return
        # Le traitement part dans un thread : rendre la main tout de suite au
        # gestionnaire de touches evite de bloquer le clavier de l'utilisateur.
        threading.Thread(target=self._corriger_selection, daemon=True).start()

    def _corriger_selection(self) -> None:
        try:
            texte = presse_papier.capturer_selection(
                delai=self.config.get("delai_copie", 0.35)
            )
            if not texte:
                self.notifier("Rien a corriger",
                              "Selectionnez d'abord le texte a corriger.")
                return

            corrige, corrections = self.corriger_texte(texte)

            if not corrections:
                self.notifier("Aucune faute", "Le texte est deja correct.")
                # Restituer la selection d'origine : on avait vide le
                # presse-papiers pour la capturer.
                presse_papier.ecrire(texte)
                return

            if self.config.get("collage_auto", True):
                presse_papier.coller(
                    corrige, delai=self.config.get("delai_collage", 0.08)
                )
            else:
                presse_papier.ecrire(corrige)

            resume = " · ".join(str(c) for c in corrections[:4])
            if len(corrections) > 4:
                resume += f" · (+{len(corrections) - 4})"
            self.notifier(
                f"{len(corrections)} correction"
                f"{'s' if len(corrections) > 1 else ''}",
                resume,
            )
        except lexique.LexiqueIntrouvable as e:
            self.journal(str(e))
            self.notifier("Dictionnaire introuvable", str(e).split("\n")[0])
        except Exception:
            self.journal(traceback.format_exc())
            self.notifier("Erreur", "La correction a echoue. Voir la console.")

    # -- correction au fil de la frappe -------------------------------------

    def _signaler_correction(self, remplacement) -> None:
        """Appelee a chaque correction automatique."""
        self.journal(f"[auto] {remplacement}")
        if not self.config.get("apprentissage", True):
            return
        self.journal_habitudes.correction_appliquee(
            remplacement.avant, remplacement.ecrire
        )
        self._corrections_depuis_sauvegarde += 1
        if self._corrections_depuis_sauvegarde >= 20:
            self.enregistrer_habitudes()

    def _signaler_annulation(self, remplacement) -> None:
        """Appelee quand une correction automatique est defaite.

        C'est le moment le plus instructif de la journee : refuser une
        correction, c'est en apprendre une.
        """
        mot = remplacement.avant.strip(" \t\n.,;:!?…")
        if mot and mot not in self.mots_retablis:
            self.mots_retablis.append(mot)
            del self.mots_retablis[:-20]

        if not self.config.get("apprentissage", True):
            return

        lecons = []
        for regle in remplacement.regles or ("",):
            lecons += self.journal_habitudes.correction_annulee(mot, regle)
        for lecon in lecons:
            self._appliquer_lecon(lecon)
        self.enregistrer_habitudes()

    def _appliquer_lecon(self, lecon) -> None:
        """Tire les consequences d'un refus repete."""
        if lecon.genre == "mot":
            mots = list(self.config.get("mots_perso", []))
            if lecon.valeur in mots:
                return
            mots.append(lecon.valeur)
            self.config["mots_perso"] = mots
            self._sauvegarder_config()
            self.journal_habitudes.oublier_mot(lecon.valeur)
            self._correcteurs.clear()
            self.notifier("Papote a compris",
                          f"« {lecon.valeur} » ne sera plus corrigé.")
        else:
            # Desactiver une regle est une decision plus lourde : on la
            # propose, on ne la prend pas.
            self.regles_contestees.append(lecon.valeur)
            del self.regles_contestees[:-10]
            self.notifier(
                "Une règle vous dérange",
                f"Vous avez annulé {lecon.compte} fois la règle {lecon.valeur}. "
                f"Vous pouvez l'éteindre depuis la fenêtre.",
            )

    def enregistrer_habitudes(self) -> None:
        self._corrections_depuis_sauvegarde = 0
        try:
            self.journal_habitudes.enregistrer(apprentissage_mod.chemin_journal())
        except OSError:
            pass

    def _sauvegarder_config(self) -> None:
        try:
            config_mod.sauvegarder(self.config)
        except OSError:
            pass

    # -- applications -------------------------------------------------------

    @property
    def application_courante(self) -> str | None:
        """La derniere application dans laquelle on a tape."""
        if self._ecoute is not None and self._ecoute.derniere_application:
            return self._ecoute.derniere_application
        return politique_mod.application_active()

    def exclure_application(self, application: str) -> None:
        """Ne plus corriger dans cette application."""
        exclues = list(self.config.get("applications_exclues", []))
        if application in exclues:
            return
        exclues.append(application)
        self.config["applications_exclues"] = exclues
        self.politique.exclure(application)
        self._sauvegarder_config()
        self.notifier("Papote se tait",
                      f"Plus aucune correction automatique dans {application}.")

    def annuler(self) -> None:
        """Remet ce qui etait ecrit avant la derniere correction automatique."""
        if self._ecoute is None:
            return
        remplacement = self._ecoute.annuler()
        if remplacement is None:
            self.notifier("Rien a annuler",
                          "Aucune correction automatique recente.")
            return

        mot = remplacement.avant.strip(" \t\n.,;:!?…")
        if mot and mot not in self.mots_retablis:
            self.mots_retablis.append(mot)
            del self.mots_retablis[:-20]

        self.notifier(
            "Correction annulee",
            f"« {mot} » est retabli. Ouvrez la fenetre pour l'ajouter a "
            f"votre dictionnaire.",
        )

    @property
    def correction_auto(self) -> bool:
        return bool(self.config.get("correction_auto", True))

    def basculer_correction_auto(self) -> bool:
        """Active ou coupe la correction au fil de la frappe, et s'en souvient."""
        actif = not self.correction_auto
        self.config["correction_auto"] = actif
        try:
            config_mod.sauvegarder(self.config)
        except OSError:
            pass

        if actif:
            self.ecoute.activer()
        elif self._ecoute is not None:
            self._ecoute.desactiver()
        return actif

    def recharger(self, config: dict) -> None:
        """Reprend les reglages a zero, sans redemarrer l'application."""
        raccourcis_changes = any(
            config.get(cle) != self.config.get(cle)
            for cle in ("raccourci", "raccourci_annuler", "raccourci_fenetre")
        )
        self.config = config
        self._correcteurs.clear()
        self.politique = politique_mod.depuis_config(config)

        if self._ecoute is not None:
            self._ecoute.desactiver()
            self._ecoute = None

        if raccourcis_changes:
            self._desactiver_raccourcis()
            self._installer_raccourcis()
            self._activer_raccourcis()

        self.prechauffer()

    # -- mises a jour -------------------------------------------------------

    # Une fois par jour : une application de bureau n'a pas a interroger un
    # serveur plus souvent que cela.
    INTERVALLE_MAJ = 24 * 3600

    def surveiller_versions(self) -> None:
        """Cherche une nouvelle version, puis recommence une fois par jour."""
        if not maj.compilee():
            return

        def boucler():
            # Laisser l'application demarrer avant d'aller sur le reseau.
            time.sleep(20)
            while True:
                self.chercher_mise_a_jour()
                time.sleep(self.INTERVALLE_MAJ)

        threading.Thread(target=boucler, daemon=True).start()

    def chercher_mise_a_jour(self, prevenir_si_a_jour: bool = False) -> maj.Version | None:
        """Telecharge la derniere version si elle est plus recente.

        Elle n'est pas mise en place tout de suite : elle attend le prochain
        demarrage. Remplacer l'executable sous les pieds de quelqu'un qui
        ecrit serait le plus sur moyen de lui faire perdre sa phrase.
        """
        try:
            version = maj.disponible()
        except maj.MiseAJourImpossible as e:
            self.journal(f"Verification des mises a jour impossible : {e}")
            if prevenir_si_a_jour:
                self.notifier("Mise à jour", f"Vérification impossible : {e}")
            return None

        if version is None:
            if prevenir_si_a_jour:
                self.notifier("Mise à jour", "Vous êtes déjà à jour.")
            return None

        try:
            maj.installer_maintenant(version)
        except maj.MiseAJourImpossible as e:
            self.journal(f"Telechargement de {version} impossible : {e}")
            return None

        self.maj_prete = version
        self.notifier(
            f"Version {version} téléchargée",
            "Elle prendra la place de l'actuelle au prochain démarrage.",
        )
        return version

    # -- retours a l'utilisateur --------------------------------------------

    def notifier(self, titre: str, message: str) -> None:
        """Surchargee par l'interface graphique ; par defaut, on journalise."""
        if self.config.get("notifications", True):
            self.journal(f"[{titre}] {message}")

    # -- cycle de vie -------------------------------------------------------

    def demarrer(self) -> None:
        # Si l'application a ete deplacee ou recompilee, la commande inscrite
        # au registre pointe dans le vide : on la remet a jour.
        try:
            demarrage.synchroniser()
        except OSError:
            pass
        self._activer_raccourcis()
        self.journal(
            f"Papote actif. Raccourci : {self.config['raccourci']} · "
            f"annuler : {self.config['raccourci_annuler']}"
        )
        if self.config.get("verifier_maj", True):
            self.surveiller_versions()

    def arreter(self) -> None:
        self._desactiver_raccourcis()
        if self._ecoute is not None:
            self._ecoute.desactiver()
        self.enregistrer_habitudes()

    def basculer(self) -> bool:
        """Met tout en pause, ou repart. Renvoie le nouvel etat."""
        self.actif = not self.actif
        if self._ecoute is not None:
            self._ecoute.actif = self.actif and self.correction_auto
        return self.actif

    # -- demarrage automatique ----------------------------------------------

    @property
    def demarrage_auto(self) -> bool:
        return demarrage.actif()

    def basculer_demarrage_auto(self) -> bool:
        """Inscrit ou retire l'application du demarrage de Windows."""
        return demarrage.basculer()
