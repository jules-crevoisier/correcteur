# -*- coding: utf-8 -*-
"""Icone dans la zone de notification et notifications systeme."""

from __future__ import annotations

import subprocess
import sys
import threading
import time

from . import config as config_mod
from . import demarrage


def _icone(actif: bool = True):
    """Dessine l'icone : un « A » sur pastille ronde, grise quand en pause."""
    from PIL import Image, ImageDraw

    taille = 64
    image = Image.new("RGBA", (taille, taille), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(image)
    fond = (43, 122, 222, 255) if actif else (128, 128, 128, 255)
    dessin.ellipse([2, 2, taille - 2, taille - 2], fill=fond)
    # Un accent aigu au-dessus du A : le propos de l'outil en un coup d'oeil.
    dessin.line([(26, 12), (36, 6)], fill="white", width=5)
    dessin.line([(20, 52), (32, 20)], fill="white", width=6)
    dessin.line([(32, 20), (44, 52)], fill="white", width=6)
    dessin.line([(25, 40), (39, 40)], fill="white", width=5)
    return image


class InterfaceBarre:
    """Enveloppe l'application dans une icone de zone de notification."""

    # Intervalle de relecture du fichier de reglages, en secondes. La fenetre
    # tourne dans un autre processus : c'est par le fichier qu'elle nous parle.
    SURVEILLANCE = 2.0

    def __init__(self, app):
        self.app = app
        self.icone = None
        self._empreinte = self._empreinte_config()
        # L'application delegue ses messages a la vraie notification systeme.
        app.notifier = self.notifier

    def notifier(self, titre: str, message: str) -> None:
        if not self.app.config.get("notifications", True):
            return
        try:
            if self.icone is not None:
                self.icone.notify(message, titre)
        except Exception:
            # Toutes les plateformes ne savent pas afficher de bulle ;
            # ce n'est jamais une raison d'interrompre une correction.
            print(f"[{titre}] {message}", file=sys.stderr)

    # -- entrees du menu ----------------------------------------------------

    def _ouvrir_fenetre(self, _icone=None, _element=None) -> None:
        """Ouvre la fenetre de correction dans un processus a part.

        pystray occupe deja la boucle d'evenements du processus ; tkinter
        exige la sienne. Les faire cohabiter est une source de blocages, un
        second processus n'en est pas une.
        """
        commande = ([sys.executable, "--fenetre"] if getattr(sys, "frozen", False)
                    else [sys.executable, "-m", "correcteur", "--fenetre"])
        try:
            subprocess.Popen(commande)
        except OSError as e:
            self.notifier("Fenêtre", f"Ouverture impossible : {e}")

    def _basculer_correction_auto(self, icone, _element) -> None:
        actif = self.app.basculer_correction_auto()
        icone.title = self._titre()
        self.notifier(
            "Correcteur",
            "Le texte se corrige pendant que vous écrivez." if actif
            else "La correction automatique est coupée ; le raccourci reste actif.",
        )

    def _annuler(self, _icone, _element) -> None:
        self.app.annuler()

    def _basculer(self, icone, _element) -> None:
        actif = self.app.basculer()
        icone.icon = _icone(actif)
        icone.title = self._titre()
        self.notifier(
            "Correcteur", "Correction activée" if actif else "Correction en pause"
        )

    def _basculer_demarrage(self, _icone, _element) -> None:
        try:
            actif = self.app.basculer_demarrage_auto()
        except Exception as e:
            self.notifier("Démarrage automatique", f"Échec : {e}")
            return
        self.notifier(
            "Démarrage automatique",
            "Le correcteur se lancera avec Windows." if actif
            else "Le correcteur ne se lancera plus avec Windows.",
        )

    def _quitter(self, icone, _element) -> None:
        self.app.arreter()
        icone.stop()

    def _titre(self) -> str:
        if not self.app.actif:
            return "Correcteur (en pause)"
        if self.app.correction_auto:
            return "Correcteur — corrige pendant que vous écrivez"
        return f"Correcteur — {self.app.config['raccourci']}"

    # -- reglages modifies depuis la fenetre --------------------------------

    def _empreinte_config(self):
        try:
            return config_mod.chemin_config().stat().st_mtime_ns
        except OSError:
            return None

    def _surveiller_config(self) -> None:
        """Relit les reglages quand la fenetre les a changes.

        La fenetre vit dans un autre processus : elle ecrit le fichier, on le
        relit. Deux secondes de retard valent mieux qu'un canal de
        communication a maintenir.
        """
        while True:
            time.sleep(self.SURVEILLANCE)
            empreinte = self._empreinte_config()
            if empreinte is None or empreinte == self._empreinte:
                continue
            self._empreinte = empreinte
            try:
                self.app.recharger(config_mod.charger())
            except Exception:
                continue
            if self.icone is not None:
                self.icone.title = self._titre()

    # -- boucle principale --------------------------------------------------

    def lancer(self) -> None:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Ouvrir la fenêtre", self._ouvrir_fenetre,
                             default=True),
            pystray.MenuItem(
                "Corriger pendant que j'écris",
                self._basculer_correction_auto,
                checked=lambda _: self.app.correction_auto,
            ),
            pystray.MenuItem("Annuler la dernière correction", self._annuler),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: "Mettre en pause" if self.app.actif else "Reprendre",
                self._basculer,
            ),
            pystray.MenuItem(
                "Lancer au démarrage de Windows",
                self._basculer_demarrage,
                checked=lambda _: self.app.demarrage_auto,
                visible=demarrage.disponible(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", self._quitter),
        )
        self.icone = pystray.Icon(
            "correcteur", _icone(True), self._titre(), menu
        )
        self.app.demarrer()
        self.app.prechauffer()
        threading.Thread(target=self._surveiller_config, daemon=True).start()
        self.icone.run()
