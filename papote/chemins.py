# -*- coding: utf-8 -*-
"""Ou l'application se trouve, et ou elle range ses donnees.

L'application doit fonctionner de trois facons : depuis les sources, depuis
un .exe compile, et depuis une cle USB. Centraliser ces chemins ici evite
que chaque module refasse la distinction a sa maniere.
"""

from __future__ import annotations

import sys
from pathlib import Path


def racine_application() -> Path:
    """Dossier de l'application, compilee en .exe ou lancee depuis les sources."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def dossier_donnees() -> Path:
    """Dossier contenant le lexique francais.

    PyInstaller deplie les donnees embarquees dans un dossier temporaire
    (`sys._MEIPASS`) en mode fichier unique, et dans `_internal` en mode
    dossier. On teste les trois emplacements possibles.
    """
    candidats = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidats.append(Path(meipass) / "donnees")

    racine = racine_application()
    candidats.append(racine / "donnees")
    candidats.append(racine / "_internal" / "donnees")

    for candidat in candidats:
        if (candidat / "lexique_fr.txt.gz").is_file():
            return candidat

    # Aucun trouve : renvoyer le chemin attendu produit un message d'erreur
    # plus parlant que l'echec d'une recherche silencieuse.
    return candidats[-1]


def dossier_web() -> Path:
    """Dossier de la page qui sert de fenetre.

    Meme recherche que pour le lexique, aux memes trois endroits : la page
    voyage avec l'application, deballee dans un dossier temporaire par
    PyInstaller ou posee a cote des sources.
    """
    candidats = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidats.append(Path(meipass) / "papote" / "web")

    racine = racine_application()
    candidats.append(racine / "papote" / "web")
    candidats.append(racine / "_internal" / "papote" / "web")
    # Depuis les sources, `papote/` est le dossier de ce fichier.
    candidats.append(Path(__file__).resolve().parent / "web")

    for candidat in candidats:
        if (candidat / "index.html").is_file():
            return candidat
    return candidats[-1]
