# -*- coding: utf-8 -*-
"""La mise en page de la bulle, sans ecran : rien ne se chevauche."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import bulle  # noqa: E402


def _mesurer(texte, style):
    # Une police a chasse fixe : 8 pixels par lettre, 9 en gras.
    return len(texte) * (9 if style in ("choix", "touche") else 8)


@pytest.mark.parametrize("mot,propositions", [
    ("bonj", ["bonjour", "bonjours", "bonjourner"]),
    ("aujourdhui", ["aujourd'hui"]),
    ("", ["vraiment", "vrai"]),
])
def test_les_elements_se_suivent_sans_se_chevaucher(mot, propositions):
    elements, largeur = bulle.disposer(mot, propositions, "Tab", _mesurer)
    # La touche et son texte vivent dans la pastille ; le reste se suit.
    a_plat = [e for e in elements if e.genre not in ("choix", "touche", "touche_texte")]
    for avant, apres in zip(a_plat, a_plat[1:]):
        assert avant.x + avant.largeur <= apres.x
    assert a_plat[-1].x + a_plat[-1].largeur < largeur


def test_la_premiere_proposition_et_sa_touche_tiennent_dans_la_pastille():
    elements, _ = bulle.disposer("bonj", ["bonjour"], "Tab", _mesurer)
    pastille = next(e for e in elements if e.genre == "pastille")
    for genre in ("choix", "touche", "touche_texte"):
        e = next(e for e in elements if e.genre == genre)
        assert pastille.x < e.x and e.x + e.largeur < pastille.x + pastille.largeur
    assert next(e for e in elements if e.genre == "choix").texte == "bonjour"


def test_sans_mot_tape_pas_de_fleche():
    elements, _ = bulle.disposer("", ["vraiment"], "Tab", _mesurer)
    assert not any(e.genre in ("mot", "fleche") for e in elements)


def test_le_theme_suit_windows_et_sombre_ailleurs():
    assert bulle.palette("clair") is bulle.CLAIR
    assert bulle.palette("sombre") is bulle.SOMBRE
    if sys.platform != "win32":
        assert bulle.theme_windows() == "sombre"
