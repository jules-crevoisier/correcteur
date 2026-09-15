# -*- coding: utf-8 -*-
"""Raccourci clavier global, et lecture des combinaisons choisies."""

from __future__ import annotations

from typing import Callable


# Ce que tkinter appelle une touche, et ce que la bibliotheque `keyboard`
# attend en retour.
TOUCHES_TKINTER = {
    "Control_L": "ctrl", "Control_R": "ctrl",
    "Alt_L": "alt", "Alt_R": "alt", "ISO_Level3_Shift": "alt",
    "Shift_L": "shift", "Shift_R": "shift",
    "Super_L": "windows", "Super_R": "windows",
    "Win_L": "windows", "Win_R": "windows",
    "space": "space", "Return": "enter", "Tab": "tab",
    "Prior": "page up", "Next": "page down",
    "Insert": "insert", "Home": "home", "End": "end",
    "Up": "up", "Down": "down", "Left": "left", "Right": "right",
}

MODIFICATEURS = ("ctrl", "alt", "shift", "windows")


def nom_de_touche(keysym: str) -> str | None:
    """Traduit la touche annoncee par tkinter. None si elle ne sert a rien."""
    if keysym in TOUCHES_TKINTER:
        return TOUCHES_TKINTER[keysym]
    if len(keysym) == 1:
        return keysym.lower()
    if keysym.lower().startswith("f") and keysym[1:].isdigit():
        return keysym.lower()
    return None


class RaccourciInvalide(ValueError):
    """La combinaison n'est pas comprise par le systeme."""


class Raccourci:
    """Associe une combinaison de touches a une action, partout dans le systeme."""

    def __init__(self, combinaison: str, action: Callable[[], None]):
        self.combinaison = combinaison
        self.action = action
        self._enregistre = None

    def activer(self) -> None:
        import keyboard

        if self._enregistre is not None or not self.combinaison:
            return
        try:
            # suppress=True empeche la combinaison d'atteindre l'application
            # sous-jacente, qui pourrait lui avoir donne un autre sens.
            self._enregistre = keyboard.add_hotkey(
                self.combinaison, self.action, suppress=True
            )
        except (ValueError, KeyError) as e:
            # Une combinaison saisie a la main peut etre incomprehensible :
            # « ctrl+alt+é » sur un clavier qui n'en a pas, par exemple.
            raise RaccourciInvalide(
                f"« {self.combinaison} » n'est pas une combinaison valide."
            ) from e

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
