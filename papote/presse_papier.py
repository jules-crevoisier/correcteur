# -*- coding: utf-8 -*-
"""Capture de la selection et recollage, via le presse-papiers.

Il n'existe pas d'API portable pour lire le texte selectionne dans une
application tierce. La methode universelle consiste a simuler Ctrl+C, lire le
presse-papiers, puis simuler Ctrl+V avec le texte corrige. Tout ce module
gere les details penibles de cette manoeuvre.
"""

from __future__ import annotations

import time


class ErreurPressePapier(RuntimeError):
    """Le presse-papiers n'a pas pu etre lu ou ecrit."""


def _pyperclip():
    import pyperclip
    return pyperclip


def _clavier():
    import keyboard
    return keyboard


def lire() -> str:
    try:
        return _pyperclip().paste() or ""
    except Exception as e:
        raise ErreurPressePapier(str(e)) from e


def ecrire(texte: str) -> None:
    try:
        _pyperclip().copy(texte)
    except Exception as e:
        raise ErreurPressePapier(str(e)) from e


def capturer_selection(delai: float = 0.35) -> str | None:
    """Copie la selection courante et la renvoie.

    Renvoie None si rien n'etait selectionne.

    On vide le presse-papiers avant de simuler Ctrl+C : sans cela, une
    selection identique au contenu deja present serait indiscernable d'une
    absence de selection. On attend ensuite que quelque chose y apparaisse,
    plutot que de dormir un delai fixe — l'application cible repond souvent
    en quelques millisecondes.
    """
    clavier = _clavier()
    ecrire("")

    clavier.send("ctrl+c")

    echeance = time.time() + delai
    while time.time() < echeance:
        time.sleep(0.01)
        contenu = lire()
        if contenu:
            return contenu
    return None


def coller(texte: str, delai: float = 0.08) -> None:
    """Place `texte` dans le presse-papiers et simule Ctrl+V."""
    ecrire(texte)
    # Laisser le temps au presse-papiers de se propager avant de coller :
    # certaines applications lisent trop tot et collent l'ancien contenu.
    time.sleep(delai)
    _clavier().send("ctrl+v")
