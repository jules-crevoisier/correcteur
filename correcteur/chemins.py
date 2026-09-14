# -*- coding: utf-8 -*-
"""Ou l'application se trouve, et ou elle range ses composants.

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


def dossiers_jre() -> list[Path]:
    """Emplacements possibles d'un Java portable livre avec l'application."""
    racine = racine_application()
    return [racine / "jre", racine / "_internal" / "jre"]


def dossier_moteur() -> Path | None:
    """Dossier LanguageTool livre avec l'application, s'il existe.

    Sa presence rend l'installation portable : le moteur n'est plus cherche
    dans le profil de l'utilisateur mais a cote de l'executable.
    """
    for candidat in (racine_application() / "moteur",
                     racine_application() / "_internal" / "moteur"):
        if candidat.is_dir():
            return candidat
    return None
