# -*- coding: utf-8 -*-
"""Tests de la marque.

Le logo sort a toutes les tailles, de l'icone de seize pixels a l'image
d'installateur. Ce qu'on verifie ici n'est pas qu'il est beau — c'est qu'il
sort, qu'il est carre, et que le SVG et le trace Pillow parlent bien du meme
dessin.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import couleurs, logo  # noqa: E402


@pytest.mark.parametrize("taille", [16, 32, 64, 128, 256])
def test_le_logo_sort_carre_a_toutes_les_tailles(taille):
    image = logo.dessiner(taille)
    assert image.size == (taille, taille)


def test_sans_fond_l_image_est_transparente():
    """Une icone doit pouvoir se poser sur n'importe quel fond."""
    image = logo.dessiner(64)
    assert image.mode == "RGBA"
    assert image.getpixel((1, 1))[3] == 0


def test_avec_un_fond_l_image_est_pleine():
    image = logo.dessiner(64, fond=couleurs.FOND)
    assert image.mode == "RGB"


def test_la_bulle_occupe_le_centre_sans_toucher_les_bords():
    """Une icone qui touche ses bords parait plus grosse que ses voisines."""
    image = logo.dessiner(64)
    assert image.getpixel((32, 20))[3] > 200, "la bulle devrait couvrir le centre"
    for coin in ((0, 0), (63, 0), (0, 63), (63, 63)):
        assert image.getpixel(coin)[3] == 0, f"le coin {coin} devrait etre vide"


def test_le_degrade_eclaircit_vers_le_haut():
    image = logo.dessiner(128)
    haut = image.getpixel((64, 26))
    bas = image.getpixel((64, 78))
    assert sum(haut[:3]) > sum(bas[:3])


def test_le_svg_decrit_le_meme_dessin():
    trace = logo.svg(48)
    assert trace.startswith("<svg") and trace.endswith("</svg>")
    assert 'viewBox="0 0 100 100"' in trace
    assert trace.count("<circle") == len(logo.POINTS_X)
    assert couleurs.ACCENT in trace


def test_deux_svg_sur_la_meme_page_ne_se_melangent_pas():
    """Deux degrades du meme identifiant, et le second efface le premier."""
    un = logo.svg(24, identifiant="entete")
    deux = logo.svg(24, identifiant="pied")
    assert 'id="entete"' in un and 'url(#entete)' in un
    assert 'id="pied"' in deux and 'url(#entete)' not in deux


def test_le_svg_ne_laisse_pas_de_nombre_illisible():
    """Les fractions se lisent sur une grille de cent, pas en 0.30000000004."""
    for nombre in re.findall(r'"(-?\d+\.?\d*)"', logo.svg(32)):
        assert len(nombre.split(".")[-1]) <= 4, nombre
