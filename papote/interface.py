# -*- coding: utf-8 -*-
"""Icone dans la zone de notification et notifications systeme."""

from __future__ import annotations

import subprocess
import sys
import threading
import time

from . import __version__, config as config_mod
from . import demarrage, icones, maj, theme


def _icone(actif: bool = True):
    """La bulle de Papote, en pixel art. Grise quand l'outil est en pause."""
    trait = theme.ACCENT if actif else theme.TEXTE_ETEINT
    creux = "#0e1014" if actif else "#1a1c22"
    return icones.image_pil(
        "papote",
        icones.palette(trait, creux, lumiere=theme.ACCENT_VIF if actif else trait),
        taille=64,
    )


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
        self.app.ouvrir_fenetre()

    def _chercher_maj(self, _icone=None, _element=None) -> None:
        threading.Thread(
            target=self.app.chercher_mise_a_jour,
            kwargs={"prevenir_si_a_jour": True},
            daemon=True,
        ).start()

    def _redemarrer(self, icone, _element) -> None:
        """Relance l'application : la version telechargee prend alors la place."""
        self.app.arreter()
        commande = ([sys.executable] if getattr(sys, "frozen", False)
                    else [sys.executable, "-m", "papote"])
        try:
            subprocess.Popen(commande)
        except OSError as e:
            self.notifier("Redémarrage", f"Impossible : {e}")
            return
        icone.stop()

    def _libelle_maj(self) -> str:
        if self.app.maj_prete is not None:
            return f"Redémarrer pour installer la version {self.app.maj_prete}"
        return f"Rechercher une mise à jour (version {__version__})"

    def _basculer_correction_auto(self, icone, _element) -> None:
        actif = self.app.basculer_correction_auto()
        icone.title = self._titre()
        self.notifier(
            "Papote",
            "Le texte se corrige pendant que vous écrivez." if actif
            else "La correction automatique est coupée ; le raccourci reste actif.",
        )

    def _annuler(self, _icone, _element) -> None:
        self.app.annuler()

    def _relire(self, _icone=None, _element=None) -> None:
        self.app.relire()

    def _exclure_application(self, icone, _element) -> None:
        application = self.app.application_courante
        if not application:
            self.notifier("Applications",
                          "Papote ne sait pas dans quel programme vous écrivez.")
            return
        self.app.exclure_application(application)
        icone.title = self._titre()

    def _libelle_exclusion(self) -> str:
        application = self.app.application_courante
        if not application:
            return "Ne plus corriger dans cette application"
        return f"Ne plus corriger dans {application}"

    def _basculer(self, icone, _element) -> None:
        actif = self.app.basculer()
        icone.icon = _icone(actif)
        icone.title = self._titre()
        self.notifier(
            "Papote", "Correction activée" if actif else "Correction en pause"
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
            return "Papote (en pause)"
        if self.app.correction_auto:
            return "Papote — corrige pendant que vous écrivez"
        return f"Papote — {self.app.config['raccourci']}"

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

            # La fenetre demande parfois qu'on se relance — apres avoir
            # telecharge une mise a jour, par exemple.
            if maj.redemarrage_demande() and self.icone is not None:
                self._redemarrer(self.icone, None)
                return

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
            pystray.MenuItem("Relire la sélection…", self._relire),
            pystray.MenuItem(lambda _: self._libelle_exclusion(),
                             self._exclure_application),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: self._libelle_maj(),
                lambda icone, element: (
                    self._redemarrer(icone, element)
                    if self.app.maj_prete is not None
                    else self._chercher_maj(icone, element)
                ),
                visible=maj.compilee(),
            ),
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
            "papote", _icone(True), self._titre(), menu
        )
        self.app.demarrer()
        self.app.prechauffer()
        threading.Thread(target=self._surveiller_config, daemon=True).start()
        self.icone.run()
