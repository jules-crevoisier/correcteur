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
from . import memoire as memoire_mod
from . import config as config_mod
from . import demarrage, frappe as frappe_mod, grammaire, journal as journal_mod
from . import lexique, maj, moteur
from . import morphologie
from . import politique as politique_mod
from . import presse_papier
from .raccourci import Raccourci, RaccourciInvalide


def _mot_connu(lexique_, mot: str) -> bool:
    """Ce mot est-il du francais, elision comprise ?

    « j'ai » ne figure pas au dictionnaire : il y a « ai », et « j' »
    devant. Sans separer les deux, la correction la plus courante du
    francais parle etait jugee inconnue — et « Vos fautes » restait vide de
    tout ce qui porte une apostrophe, c'est-a-dire de presque tout.
    """
    mot = mot.strip(".,;:!?…\u00a0")
    if not mot:
        return False
    if lexique_.connait(mot):
        return True
    elision, noyau = grammaire.separer_clitique(mot)
    return bool(elision) and bool(noyau) and lexique_.connait(noyau)


def _trace_sans_texte(remplacement) -> str:
    """Ce qu'on a le droit d'ecrire dans le journal : la forme, pas le fond.

    « ORTHOGRAPHE 12→13 » suffit a comprendre ce qui s'est passe quand on
    cherche une panne, et ne dit rien de ce qui a ete tape.
    """
    regles = getattr(remplacement, "regles", ()) or ("CORRECTION",)
    avant = len(getattr(remplacement, "avant", "") or "")
    apres = len(getattr(remplacement, "ecrire", "") or "")
    return f"{'+'.join(regles)} {avant}\u2192{apres}"


def _dire_la_regle(nom: str) -> str:
    """Le message francais d'une regle, plutot que son identifiant.

    L'utilisateur recevait « la règle PARTICIPE_APRES_AUXILIAIRE ». Ce nom
    ne sert qu'au code ; chaque regle porte deja une phrase ecrite pour
    etre lue, et c'est celle-la qu'il faut montrer.
    """
    from . import grammaire

    for regle in grammaire.REGLES:
        if regle.nom == nom:
            return regle.message
    return "cette correction"


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
        self._morphologie: morphologie.Morphologie | None = None
        self._verrou = threading.Lock()
        self._ecoute: frappe_mod.EcouteClavier | None = None

        self.politique = politique_mod.depuis_config(self.config)
        self.journal_habitudes = apprentissage_mod.charger()
        # Les mots que vous employez, et ceux qui en suivent
        # d'autres : c'est tout le contexte dont dispose la
        # prediction, et il ne sort pas de cette machine.
        self.memoire_frappe = memoire_mod.charger()
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

        # Le texte que le raccourci de relecture vient de capturer, en
        # attendant que la fenetre le reclame. Il ne vit qu'en memoire, et
        # seulement dans le processus qui affiche la fenetre.
        self.texte_a_relire: str = ""

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
            # L'environnement doit etre deballe : voir « environnement_de_relance ».
            subprocess.Popen(commande + list(arguments),
                             env=maj.environnement_de_relance())
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
                self._morphologie = morphologie.Morphologie()
                self._morphologie.charger()
                self.journal("Papote prêt.")
            self._correcteurs[registre] = moteur.depuis_config(
                self.config, self._lexique, registre, self._morphologie
            )
        return self._correcteurs[registre]

    @property
    def ecoute(self) -> frappe_mod.EcouteClavier:
        """La correction au fil de la frappe, construite au premier besoin."""
        if self._ecoute is None:
            self._ecoute = frappe_mod.EcouteClavier(
                frappe_mod.Frappe(self.correcteur,
                                  predicteur=self._predicteur(),
                                  memoire=self._memoire()),
                delai_oubli=self.config.get("delai_oubli", 5.0),
                sur_correction=self._signaler_correction,
                sur_annulation=self._signaler_annulation,
                politique=self.politique,
                correcteur_pour=self.correcteur_pour,
                bulle=self._bulle(),
                touche_prediction=self.config.get("touche_prediction", "tab"),
            )
        return self._ecoute

    def _predicteur(self):
        """Le devineur de mots, ou rien si la prediction est eteinte."""
        if not self.config.get("prediction", True):
            return None
        from . import prediction

        # `correcteur` a deja force le chargement du dictionnaire : le
        # predicteur s'appuie dessus plutot que d'en ouvrir un second.
        self.correcteur  # noqa: B018
        return prediction.Predicteur(self._lexique, self._memoire())

    def _memoire(self):
        """Les habitudes de frappe, si l'apprentissage est autorise.

        Le meme reglage gouverne les deux apprentissages : celui des
        corrections annulees et celui des tournures. Quelqu'un qui refuse
        qu'on retienne ses habitudes les refuse toutes.
        """
        if not self.config.get("apprentissage", True):
            return None
        return self.memoire_frappe

    def _bulle(self):
        """La bulle de propositions, ou une doublure inerte."""
        from . import bulle as bulle_mod

        if not self.config.get("prediction", True):
            return bulle_mod.BulleMuette()
        return bulle_mod.Bulle(self.config.get("position_bulle", "bas-droite"))

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
                    "la correction au fil de la frappe n'a pas pu démarrer", e)
                self.notifier(
                    "Correction automatique indisponible",
                    f"Le raccourci {self.config.get('raccourci', '')} reste "
                    f"actif. Détails dans Réglages → Quand quelque chose ne va pas.",
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
                self.notifier("Rien à corriger",
                              "Sélectionnez d'abord le texte à corriger.")
                return

            corrige, corrections = self.corriger_texte(texte)

            if not corrections:
                self.notifier("Aucune faute", "Le texte est déjà correct.")
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
            self.notifier("Erreur", "La correction a échoué. Détails dans "
                          "Réglages → Quand quelque chose ne va pas.")

    # -- correction au fil de la frappe -------------------------------------

    def _signaler_correction(self, remplacement) -> None:
        """Appelee a chaque correction automatique.

        Rien de ce qui est ecrit ici ne doit contenir le texte tape.

        Papote promet que ce qu'on tape ne quitte pas la machine ; il promet
        aussi de ne retenir que des mots du dictionnaire. La memoire de
        frappe tenait cette seconde promesse, ces deux chemins-ci non : le
        journal recevait « Motdepase123 → Motdepasse123 », et le fichier
        d'habitudes aussi. Un mot de passe mal tape est exactement ce qui
        declenche une correction d'orthographe.
        """
        self.journal(f"[auto] {_trace_sans_texte(remplacement)}")
        if not self.config.get("apprentissage", True):
            return
        # Seule la forme corrigee est examinee, parce que seule elle est
        # retenue : le cote gauche est la faute, et une faute n'est par
        # definition pas un mot du dictionnaire. Exiger qu'elle en soit un
        # revenait a ne rien compter du tout.
        if self._mots_connus(remplacement.ecrire):
            self.journal_habitudes.correction_appliquee(
                remplacement.avant, remplacement.ecrire
            )
        self._corrections_depuis_sauvegarde += 1
        if self._corrections_depuis_sauvegarde >= 20:
            self.enregistrer_habitudes()

    def _mots_connus(self, *morceaux: str) -> bool:
        """Tous ces morceaux sont-ils des mots du dictionnaire ?

        C'est le meme test que celui de la memoire de frappe, et pour la
        meme raison : ce qui n'est pas un mot du francais n'a rien a faire
        dans un fichier qui survit a la session.
        """
        try:
            lexique_ = self.correcteur.lexique
        except Exception:                          # noqa: BLE001
            return False
        for morceau in morceaux:
            mots = [m for m in (morceau or "").split() if m.strip()]
            if not mots:
                return False
            for mot in mots:
                if not _mot_connu(lexique_, mot):
                    return False
        return True

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
                f"Vous avez annulé {lecon.compte} fois la même correction : "
                f"{_dire_la_regle(lecon.valeur)}. Le mot que vous rétablissez "
                f"peut aussi rejoindre votre dictionnaire.",
            )

    def enregistrer_habitudes(self) -> None:
        self._corrections_depuis_sauvegarde = 0
        try:
            self.journal_habitudes.enregistrer(apprentissage_mod.chemin_journal())
        except OSError:
            pass
        self.memoire_frappe.enregistrer(memoire_mod.chemin_memoire())

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
            self.notifier("Rien à annuler",
                          "Aucune correction automatique récente.")
            return

        mot = remplacement.avant.strip(" \t\n.,;:!?…")
        if mot and mot not in self.mots_retablis:
            self.mots_retablis.append(mot)
            del self.mots_retablis[:-20]

        self.notifier(
            "Correction annulée",
            f"« {mot} » est rétabli. Ouvrez la fenêtre pour l'ajouter à "
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
            self.journal(f"Vérification des mises à jour impossible : {e}")
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
            self.journal(f"Téléchargement de {version} impossible : {e}")
            return None

        self.maj_prete = version
        self.notifier(
            f"Version {version} téléchargée",
            "Cliquez l'icône Papote près de l'horloge pour redémarrer et "
            "l'installer maintenant — sinon, elle attendra le prochain "
            "démarrage.",
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
