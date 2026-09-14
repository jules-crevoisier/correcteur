# -*- coding: utf-8 -*-
"""Raccourci clavier global."""

from __future__ import annotations

from typing import Callable


class Raccourci:
    """Associe une combinaison de touches a une action, partout dans le systeme."""

    def __init__(self, combinaison: str, action: Callable[[], None]):
        self.combinaison = combinaison
        self.action = action
        self._enregistre = None

    def activer(self) -> None:
        import keyboard

        if self._enregistre is not None:
            return
        # suppress=True empeche la combinaison d'atteindre l'application
        # sous-jacente, qui pourrait lui avoir donne un autre sens.
        self._enregistre = keyboard.add_hotkey(
            self.combinaison, self.action, suppress=True
        )

    def desactiver(self) -> None:
        import keyboard

        if self._enregistre is None:
            return
        try:
            keyboard.remove_hotkey(self._enregistre)
        except (KeyError, ValueError):
            # Deja retire : rien a faire.
            pass
        self._enregistre = None

    @property
    def actif(self) -> bool:
        return self._enregistre is not None
