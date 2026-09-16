# -*- coding: utf-8 -*-
"""La palette, les espacements, la typographie.

Ces valeurs n'ont besoin de rien : ni tkinter, ni Pillow. C'est voulu.
L'icone de la barre des taches et les images de l'installateur les emploient
sans avoir a charger une bibliotheque graphique dont elles n'ont que faire,
et il n'existe qu'un seul endroit ou changer une couleur.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------

FOND = "#0e1014"          # le fond de la fenetre
SURFACE = "#161922"       # les panneaux poses dessus
SURFACE_HAUTE = "#1e2230" # les champs, et le survol
BORDURE = "#272c3a"
BORDURE_VIVE = "#39405420"

TEXTE = "#e9ebf0"
TEXTE_DOUX = "#8b93a7"
TEXTE_ETEINT = "#5e6579"

ACCENT = "#5b8cff"
ACCENT_VIF = "#7aa2ff"
ACCENT_SOURD = "#22305c"
SUCCES = "#3ecf8e"
ALERTE = "#ffb454"

# ---------------------------------------------------------------------------
# Espacements et typographie
# ---------------------------------------------------------------------------

PETIT, MOYEN, GRAND, TRES_GRAND = 4, 8, 16, 24

FAMILLE = "Segoe UI"


def police(taille: int = 10, gras: bool = False) -> tuple:
    return (FAMILLE, taille, "bold") if gras else (FAMILLE, taille)
