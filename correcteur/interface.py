# -*- coding: utf-8 -*-
"""Icone dans la zone de notification et notifications systeme."""

from __future__ import annotations

import os
import subprocess
import sys

from . import config as config_mod


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

    def __init__(self, app):
        self.app = app
        self.icone = None
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
            print(f"[{titre}] {message}")

    # -- entrees du menu ----------------------------------------------------

    def _basculer(self, icone, _element) -> None:
        actif = self.app.basculer()
        icone.icon = _icone(actif)
        icone.title = self._titre()
        self.notifier(
            "Correcteur", "Correction activee" if actif else "Correction en pause"
        )

    def _ouvrir_config(self, _icone=None, _element=None) -> None:
        chemin = config_mod.chemin_config()
        config_mod.charger()  # cree le fichier s'il manque
        if os.name == "nt":
            os.startfile(chemin)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(chemin)])
        else:
            subprocess.Popen(["xdg-open", str(chemin)])

    def _quitter(self, icone, _element) -> None:
        self.app.arreter()
        icone.stop()

    def _titre(self) -> str:
        etat = "actif" if self.app.actif else "en pause"
        return f"Correcteur ({etat}) — {self.app.config['raccourci']}"

    # -- boucle principale --------------------------------------------------

    def lancer(self) -> None:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda _: "Mettre en pause" if self.app.actif else "Reprendre",
                self._basculer,
            ),
            pystray.MenuItem("Ouvrir les reglages", self._ouvrir_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", self._quitter),
        )
        self.icone = pystray.Icon(
            "correcteur", _icone(True), self._titre(), menu
        )
        self.app.demarrer()
        self.app.prechauffer()
        self.icone.run()
