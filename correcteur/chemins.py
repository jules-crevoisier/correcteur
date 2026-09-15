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
