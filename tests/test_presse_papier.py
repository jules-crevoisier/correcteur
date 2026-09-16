# -*- coding: utf-8 -*-
"""Le presse-papiers, et ce qu'il ne faut pas y perdre.

Papote s'en sert comme d'un passage : il le vide, simule Ctrl+C, lit ce qui
arrive. La manoeuvre marche — mais elle porte le contenu de quelqu'un
d'autre, et le raccourci est global. Il s'actionne aussi par erreur.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import presse_papier  # noqa: E402


class FauxPressePapier:
    """Un presse-papiers en memoire, et un clavier qui y depose ou non."""

    def __init__(self, contenu="", selection=None):
        self.contenu = contenu
        self.selection = selection
        self.copies = 0

    # -- cote pyperclip
    def paste(self):
        return self.contenu

    def copy(self, texte):
        self.contenu = texte

    # -- cote keyboard
    def send(self, raccourci):
        if raccourci == "ctrl+c":
            self.copies += 1
            if self.selection is not None:
                self.contenu = self.selection


@pytest.fixture
def faux(monkeypatch):
    def poser(contenu="", selection=None):
        objet = FauxPressePapier(contenu, selection)
        monkeypatch.setattr(presse_papier, "_pyperclip", lambda: objet)
        monkeypatch.setattr(presse_papier, "_clavier", lambda: objet)
        return objet
    return poser


def test_la_selection_est_rendue(faux):
    objet = faux(contenu="ce que j'avais copié", selection="ma sélection")
    assert presse_papier.capturer_selection(delai=0.2) == "ma sélection"


def test_sans_selection_le_presse_papiers_est_rendu(faux):
    """Le raccourci presse par erreur ne doit rien detruire."""
    objet = faux(contenu="un mot de passe que je venais de copier")
    assert presse_papier.capturer_selection(delai=0.05) is None
    assert objet.contenu == "un mot de passe que je venais de copier"


def test_un_presse_papiers_vide_le_reste(faux):
    objet = faux(contenu="")
    assert presse_papier.capturer_selection(delai=0.05) is None
    assert objet.contenu == ""


def test_un_presse_papiers_illisible_ne_leve_pas(faux, monkeypatch):
    """Une image dans le presse-papiers : pyperclip refuse de la lire.

    A cet instant le presse-papiers est vide — c'est nous qui l'avons vide.
    Une exception qui sort d'ici le laisserait ainsi, et personne ne le
    remplirait.
    """
    faux(selection="ma sélection")

    def refuser():
        raise presse_papier.ErreurPressePapier("pas du texte")

    monkeypatch.setattr(presse_papier, "lire", refuser)
    assert presse_papier.capturer_selection(delai=0.05) is None
