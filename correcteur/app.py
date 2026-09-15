# -*- coding: utf-8 -*-
"""Assemblage de l'application : raccourci -> selection -> correction -> collage."""

from __future__ import annotations

import sys
import threading
import traceback
from typing import Callable

from . import config as config_mod
from . import demarrage, lexique, moteur, presse_papier
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
        self.raccourci = Raccourci(self.config["raccourci"], self.sur_raccourci)

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
                    correcteur = moteur.construire(
                        regles_optionnelles=self.config.get("regles_optionnelles"),
                        lexique_perso=self.config.get("lexique_perso"),
                    )
                    correcteur.prechauffer()
                    self._correcteur = correcteur
                    self.journal("Correcteur pret.")
        return self._correcteur

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
        self.journal(
            f"Correcteur actif. Raccourci : {self.config['raccourci']}"
        )

    def arreter(self) -> None:
        self.raccourci.desactiver()

    def basculer(self) -> bool:
        """Active ou met en pause la correction. Renvoie le nouvel etat."""
        self.actif = not self.actif
        return self.actif

    # -- demarrage automatique ----------------------------------------------

    @property
    def demarrage_auto(self) -> bool:
        return demarrage.actif()

    def basculer_demarrage_auto(self) -> bool:
        """Inscrit ou retire l'application du demarrage de Windows."""
        return demarrage.basculer()
