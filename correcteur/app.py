# -*- coding: utf-8 -*-
"""Assemblage de l'application : raccourci -> selection -> correction -> collage."""

from __future__ import annotations

import sys
import threading
import traceback
from typing import Callable

from . import config as config_mod
from . import demarrage, frappe as frappe_mod, lexique, moteur, presse_papier
from .raccourci import Raccourci


class Application:
    """Le correcteur, pret a etre pilote par une interface ou en ligne de commande."""

    def __init__(self, config: dict | None = None,
                 journal: Callable[[str], None] | None = None):
        self.config = config or config_mod.charger()
        # Le journal part sur la sortie d'erreur : « --texte » doit pouvoir
        # etre redirige sans ramasser les messages de chargement.
        self.journal = journal or (lambda message: print(message, file=sys.stderr))
        self.actif = True
        self._correcteur: moteur.Correcteur | None = None
        self._verrou = threading.Lock()
        self._ecoute: frappe_mod.EcouteClavier | None = None

        # Les mots que l'utilisateur a retablis a la main : ce sont ceux qu'il
        # veut voir entrer dans son dictionnaire, et la fenetre les lui
        # proposera.
        self.mots_retablis: list[str] = []

        self.raccourci = Raccourci(self.config["raccourci"], self.sur_raccourci)
        self.raccourci_annuler = Raccourci(
            self.config["raccourci_annuler"], self.annuler
        )

    # -- preparation --------------------------------------------------------

    @property
    def correcteur(self) -> moteur.Correcteur:
        """Construit le moteur au premier usage.

        Lire le dictionnaire prend une fraction de seconde : le faire a la
        demande permet a l'icone d'apparaitre immediatement au lancement.
        """
        if self._correcteur is None:
            with self._verrou:
                if self._correcteur is None:
                    self.journal("Chargement du dictionnaire...")
                    correcteur = moteur.depuis_config(self.config)
                    correcteur.prechauffer()
                    self._correcteur = correcteur
                    self.journal("Correcteur pret.")
        return self._correcteur

    @property
    def ecoute(self) -> frappe_mod.EcouteClavier:
        """La correction au fil de la frappe, construite au premier besoin."""
        if self._ecoute is None:
            self._ecoute = frappe_mod.EcouteClavier(
                frappe_mod.Frappe(self.correcteur),
                delai_oubli=self.config.get("delai_oubli", 5.0),
                sur_correction=self._signaler_correction,
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
                # La frappe ne s'ecoute qu'une fois le dictionnaire en place :
                # un crochet clavier qui met un dixieme de seconde a repondre
                # se sent tout de suite.
                if self.config.get("correction_auto", True):
                    self.ecoute.activer()
                    self.journal("Correction au fil de la frappe active.")
            except lexique.LexiqueIntrouvable as e:
                self.journal(str(e))
                self.notifier("Dictionnaire introuvable", str(e).split("\n")[0])
            except Exception:
                self.journal(traceback.format_exc())
                self.notifier("Correcteur indisponible",
                              "Le dictionnaire n'a pas pu etre charge.")

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
        raccourcis_changes = (
            config.get("raccourci") != self.config.get("raccourci")
            or config.get("raccourci_annuler") != self.config.get("raccourci_annuler")
        )
        self.config = config
        self._correcteur = None

        if self._ecoute is not None:
            self._ecoute.desactiver()
            self._ecoute = None

        if raccourcis_changes:
            self.raccourci.desactiver()
            self.raccourci_annuler.desactiver()
            self.raccourci = Raccourci(config["raccourci"], self.sur_raccourci)
            self.raccourci_annuler = Raccourci(
                config["raccourci_annuler"], self.annuler
            )
            self.raccourci.activer()
            self.raccourci_annuler.activer()

        self.prechauffer()

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
        self.raccourci.activer()
        self.raccourci_annuler.activer()
        self.journal(
            f"Correcteur actif. Raccourci : {self.config['raccourci']} · "
            f"annuler : {self.config['raccourci_annuler']}"
        )

    def arreter(self) -> None:
        self.raccourci.desactiver()
        self.raccourci_annuler.desactiver()
        if self._ecoute is not None:
            self._ecoute.desactiver()

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
