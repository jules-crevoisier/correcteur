# -*- coding: utf-8 -*-
"""Papote se retire des jeux, et ne s'interpose plus sur Ctrl.

Le retard sur Ctrl pendant les parties venait de deux choses : les
raccourcis globaux etaient poses avec `suppress=True` — un crochet bloquant
sur chaque touche de la combinaison — et le crochet de frappe restait branche
pendant les parties. Ces tests tiennent les deux.
"""

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import jeu  # noqa: E402
from papote.frappe import EcouteClavier, Frappe  # noqa: E402
from papote.raccourci import (  # noqa: E402
    MOD_ALT, MOD_CONTROL, MOD_SHIFT, Raccourci, RaccourciInvalide,
    analyser_combinaison,
)


# -- les raccourcis ---------------------------------------------------------

class ClavierEspion(types.ModuleType):
    def __init__(self):
        super().__init__("keyboard")
        self.appels = []

    def add_hotkey(self, combinaison, action, suppress=False, **_):
        self.appels.append((combinaison, suppress))
        return combinaison

    def remove_hotkey(self, identifiant):
        pass


def test_un_raccourci_n_est_jamais_pose_en_bloquant(monkeypatch):
    """`suppress=True` rendrait chaque appui sur Ctrl tributaire de Python."""
    faux = ClavierEspion()
    monkeypatch.setitem(sys.modules, "keyboard", faux)
    # Sous Windows, RegisterHotKey passe d'abord : on teste le repli.
    monkeypatch.setattr(Raccourci, "_activer_par_le_systeme", lambda self: False)
    Raccourci("ctrl+alt+c", lambda: None).activer()
    assert faux.appels == [("ctrl+alt+c", False)]


@pytest.mark.parametrize("combinaison,attendu", [
    ("ctrl+alt+c", (MOD_CONTROL | MOD_ALT, ord("C"))),
    ("Ctrl+Shift+F5", (MOD_CONTROL | MOD_SHIFT, 0x74)),
    ("alt+space", (MOD_ALT, 0x20)),
    ("ctrl+alt+page up", (MOD_CONTROL | MOD_ALT, 0x21)),
    ("ctrl+7", (MOD_CONTROL, ord("7"))),
])
def test_les_combinaisons_sont_traduites_pour_windows(combinaison, attendu):
    assert analyser_combinaison(combinaison) == attendu


def test_un_caractere_de_ponctuation_suit_la_disposition_du_clavier():
    assert analyser_combinaison("ctrl+;", lambda c: 0xBA) == (MOD_CONTROL, 0xBA)


@pytest.mark.parametrize("combinaison", ["", "a", "ctrl", "ctrl+a+b", "ctrl+é",
                                         "ctrl+f99"])
def test_les_combinaisons_sans_sens_sont_refusees(combinaison):
    with pytest.raises(RaccourciInvalide):
        analyser_combinaison(combinaison)


# -- reconnaitre un jeu -----------------------------------------------------

def test_hors_windows_on_ne_reconnait_jamais_un_jeu(monkeypatch):
    monkeypatch.setattr(jeu.os, "name", "posix")
    assert jeu.jeu_au_premier_plan(["eldenring.exe"], "eldenring.exe") is False


def test_un_programme_designe_est_un_jeu(monkeypatch):
    monkeypatch.setattr(jeu.os, "name", "nt")
    monkeypatch.setattr(jeu, "_fenetre_plein_ecran", lambda: False)
    assert jeu.jeu_au_premier_plan(["EldenRing"], "eldenring.exe") is True


def test_un_navigateur_en_plein_ecran_n_est_pas_un_jeu(monkeypatch):
    monkeypatch.setattr(jeu.os, "name", "nt")
    monkeypatch.setattr(jeu, "_fenetre_plein_ecran", lambda: True)
    assert jeu.jeu_au_premier_plan([], "chrome.exe") is False


def test_un_inconnu_en_plein_ecran_est_un_jeu(monkeypatch):
    monkeypatch.setattr(jeu.os, "name", "nt")
    monkeypatch.setattr(jeu, "_fenetre_plein_ecran", lambda: True)
    assert jeu.jeu_au_premier_plan([], "valorant.exe") is True


# -- la veille --------------------------------------------------------------

class ClavierAccroche(types.ModuleType):
    def __init__(self):
        super().__init__("keyboard")
        self.crochets = []

    def hook(self, fonction):
        self.crochets.append(fonction)
        return fonction

    def unhook(self, fonction):
        self.crochets.remove(fonction)

    def is_pressed(self, _touche):
        return False

    def add_hotkey(self, *_a, **_k):
        return object()

    def remove_hotkey(self, _id):
        pass


@pytest.fixture
def clavier(monkeypatch):
    faux = ClavierAccroche()
    monkeypatch.setitem(sys.modules, "keyboard", faux)
    monkeypatch.setitem(sys.modules, "mouse", None)   # import refuse : pas de souris
    return faux


def test_un_jeu_decroche_le_clavier_puis_le_raccroche(correcteur, clavier):
    en_jeu = [False]
    signaux = []
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None,
                           detecteur_jeu=lambda: en_jeu[0],
                           sur_veille=signaux.append)
    ecoute.activer()
    try:
        assert len(clavier.crochets) == 1

        en_jeu[0] = True
        ecoute._surveiller_le_jeu()
        assert clavier.crochets == []
        assert ecoute.en_veille and signaux == [True]

        # Rien ne s'accumule si la partie dure.
        ecoute._surveiller_le_jeu()
        assert signaux == [True]

        en_jeu[0] = False
        ecoute._surveiller_le_jeu()
        assert len(clavier.crochets) == 1
        assert not ecoute.en_veille and signaux == [True, False]
    finally:
        ecoute.desactiver()
    assert clavier.crochets == []


def test_desactiver_pendant_une_partie_ne_rebranche_rien(correcteur, clavier):
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None,
                           detecteur_jeu=lambda: True)
    ecoute.activer()
    ecoute._surveiller_le_jeu()
    ecoute.desactiver()
    assert clavier.crochets == []
    # Une seconde activation repart proprement.
    ecoute.activer()
    assert len(clavier.crochets) == 1
    ecoute.desactiver()


def test_un_detecteur_qui_plante_ne_met_pas_en_veille(correcteur, clavier):
    def casse():
        raise OSError("boum")

    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None,
                           detecteur_jeu=casse)
    ecoute.activer()
    try:
        ecoute._surveiller_le_jeu()
        assert not ecoute.en_veille and len(clavier.crochets) == 1
    finally:
        ecoute.desactiver()
