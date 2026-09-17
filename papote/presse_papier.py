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

    Et quand rien ne vient, on rend ce qu'on avait pris. Le raccourci est
    global : il s'actionne aussi par erreur, ou dans une fenetre qui ne
    contient aucun texte selectionnable. Le vidage detruisait alors ce que
    l'utilisateur venait de copier — sans le dire, et sans retour possible.
    """
    clavier = _clavier()
    precedent = _sans_bruit_lire()
    ecrire("")

    clavier.send("ctrl+c")

    echeance = time.time() + delai
    while time.time() < echeance:
        time.sleep(0.01)
        # Une lecture qui echoue — une image dans le presse-papiers, un
        # autre programme qui le tient — ne doit pas sortir d'ici sur une
        # exception : le presse-papiers est vide a cet instant, et personne
        # ne le remplirait.
        contenu = _sans_bruit_lire()
        if contenu:
            return contenu

    _sans_bruit_ecrire(precedent)
    return None


def _sans_bruit_lire() -> str:
    """Le presse-papiers, ou rien. Une sauvegarde ne doit pas faire echouer."""
    try:
        return lire()
    except ErreurPressePapier:
        return ""


def _sans_bruit_ecrire(texte: str) -> None:
    if not texte:
        return
    try:
        ecrire(texte)
    except ErreurPressePapier:
        pass


def coller(texte: str, delai: float = 0.08) -> None:
    """Place `texte` dans le presse-papiers et simule Ctrl+V."""
    ecrire(texte)
    # Laisser le temps au presse-papiers de se propager avant de coller :
    # certaines applications lisent trop tot et collent l'ancien contenu.
    time.sleep(delai)
    _clavier().send("ctrl+v")
