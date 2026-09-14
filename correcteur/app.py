# -*- coding: utf-8 -*-
"""Assemblage de l'application : raccourci -> selection -> correction -> collage."""

from __future__ import annotations

import threading
import traceback
from typing import Callable

from . import config as config_mod
from . import moteur, presse_papier, regles
from .raccourci import Raccourci


class Application:
    """Le correcteur, pret a etre pilote par une interface ou en ligne de commande."""

    def __init__(self, config: dict | None = None,
                 journal: Callable[[str], None] = print):
        self.config = config or config_mod.charger()
        self.journal = journal
        self.actif = True
        self._correcteur = None
        self._verrou = threading.Lock()
        self.raccourci = Raccourci(self.config["raccourci"], self.sur_raccourci)
        self._appliquer_lexique_perso()

    # -- preparation --------------------------------------------------------

    def _appliquer_lexique_perso(self) -> None:
        """Ajoute les mots de l'utilisateur a la liste des mots intouchables."""
        for mot in self.config.get("lexique_perso", []):
            regles.LEXIQUE_PROTEGE.add(mot.strip().lower())

    @property
    def correcteur(self):
        """Construit le moteur au premier usage.

        LanguageTool met quelques secondes a demarrer : le faire a la demande
        permet a l'icone d'apparaitre immediatement au lancement.
        """
        if self._correcteur is None:
            with self._verrou:
                if self._correcteur is None:
                    self.journal("Demarrage du moteur de correction...")
                    self._correcteur = moteur.construire(
                        regles_optionnelles=self.config.get("regles_optionnelles"),
                    )
                    self.journal("Moteur pret.")
        return self._correcteur

    def prechauffer(self) -> None:
        """Demarre le moteur en arriere-plan pour que la 1re correction soit rapide."""
        threading.Thread(target=lambda: self.correcteur, daemon=True).start()

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
        except Exception:
            self.journal(traceback.format_exc())
            self.notifier("Erreur", "La correction a echoue. Voir la console.")

    # -- retours a l'utilisateur --------------------------------------------

    def notifier(self, titre: str, message: str) -> None:
        """Surchargee par l'interface graphique ; par defaut, on journalise."""
        if self.config.get("notifications", True):
            self.journal(f"[{titre}] {message}")

    # -- cycle de vie -------------------------------------------------------

    def demarrer(self) -> None:
        self.raccourci.activer()
        self.journal(
            f"Correcteur actif. Raccourci : {self.config['raccourci']}"
        )

    def arreter(self) -> None:
        self.raccourci.desactiver()

    def basculer(self) -> bool:
        """Active ou met en pause la correction. Renvoie le nouvel etat."""
        self.actif = not self.actif
        return self.actif
