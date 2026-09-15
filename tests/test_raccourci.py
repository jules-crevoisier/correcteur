# -*- coding: utf-8 -*-
"""Tests des raccourcis : lecture des touches et refus des combinaisons fausses."""

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from correcteur.raccourci import (  # noqa: E402
    MODIFICATEURS,
    Raccourci,
    RaccourciInvalide,
    nom_de_touche,
)


@pytest.mark.parametrize("keysym,attendu", [
    ("Control_L", "ctrl"),
    ("Control_R", "ctrl"),
    ("Alt_L", "alt"),
    ("Shift_R", "shift"),
    ("Super_L", "windows"),
    ("space", "space"),
    ("Return", "enter"),
    ("F5", "f5"),
    ("f12", "f12"),
    ("a", "a"),
    ("A", "a"),        # la majuscule ne fait pas une autre touche
    ("1", "1"),
])
def test_les_touches_utiles_sont_traduites(keysym, attendu):
    assert nom_de_touche(keysym) == attendu


@pytest.mark.parametrize("keysym", ["Escape", "Caps_Lock", "KP_5", "Menu", ""])
def test_les_touches_sans_usage_sont_ecartees(keysym):
    assert nom_de_touche(keysym) is None


def test_les_modificateurs_sont_ceux_attendus():
    assert set(MODIFICATEURS) == {"ctrl", "alt", "shift", "windows"}


class FauxClavier(types.ModuleType):
    """Un `keyboard` factice qui sait refuser une combinaison."""

    def __init__(self, refuse=()):
        super().__init__("keyboard")
        self.refuse = set(refuse)
        self.poses = []

    def add_hotkey(self, combinaison, action, suppress=False):
        if combinaison in self.refuse:
            raise ValueError(f"combinaison inconnue : {combinaison}")
        self.poses.append(combinaison)
        return combinaison

    def remove_hotkey(self, identifiant):
        self.poses.remove(identifiant)


@pytest.fixture
def clavier(monkeypatch):
    faux = FauxClavier(refuse={"ctrl+alt+¤"})
    monkeypatch.setitem(sys.modules, "keyboard", faux)
    return faux


def test_un_raccourci_valide_est_pose(clavier):
    raccourci = Raccourci("ctrl+alt+c", lambda: None)
    raccourci.activer()
    assert clavier.poses == ["ctrl+alt+c"]
    assert raccourci.actif


def test_un_raccourci_vide_est_simplement_ignore(clavier):
    """On doit pouvoir se passer d'un raccourci sans que rien ne casse."""
    raccourci = Raccourci("", lambda: None)
    raccourci.activer()
    assert clavier.poses == []
    assert not raccourci.actif


def test_une_combinaison_incomprehensible_est_signalee(clavier):
    raccourci = Raccourci("ctrl+alt+¤", lambda: None)
    with pytest.raises(RaccourciInvalide):
        raccourci.activer()
    assert not raccourci.actif


def test_desactiver_libere_la_combinaison(clavier):
    raccourci = Raccourci("f9", lambda: None)
    raccourci.activer()
    raccourci.desactiver()
    assert clavier.poses == []
    assert not raccourci.actif
