# -*- coding: utf-8 -*-
"""Localisation du moteur Java.

LanguageTool tourne sur Java et le cherche avec `shutil.which("java")`,
c'est-a-dire dans le PATH. Ce module elargit cette recherche a un JRE
portable livre a cote de l'application, ce qui evite a l'utilisateur
d'installer Java lui-meme — un point critique pour une application lancee
au demarrage, ou un echec passerait inapercu.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .chemins import dossiers_jre, racine_application

# LanguageTool 6.x exige Java 17 ou plus recent.
VERSION_MINIMALE = 17


class JavaIntrouvable(RuntimeError):
    """Aucun Java utilisable n'a ete trouve sur la machine."""


def _candidats() -> list[Path]:
    """Emplacements ou chercher un executable java, par ordre de preference."""
    noms = ["java.exe", "java"] if os.name == "nt" else ["java"]

    candidats: list[Path] = []

    # 1. JRE portable livre avec l'application.
    for dossier in dossiers_jre():
        for nom in noms:
            candidats.append(dossier / "bin" / nom)

    # 2. JAVA_HOME, s'il est defini.
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        for nom in noms:
            candidats.append(Path(java_home) / "bin" / nom)

    # 3. Le PATH.
    trouve = shutil.which("java")
    if trouve:
        candidats.append(Path(trouve))

    # 4. Emplacements d'installation habituels sous Windows.
    if os.name == "nt":
        for base in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        ):
            for editeur in ("Eclipse Adoptium", "Java", "Microsoft", "Zulu"):
                dossier = base / editeur
                if not dossier.is_dir():
                    continue
                try:
                    for install in sorted(dossier.iterdir(), reverse=True):
                        candidats.append(install / "bin" / "java.exe")
                except OSError:
                    continue

    return candidats


def version(executable: Path) -> int | None:
    """Numero de version majeur de ce Java, ou None s'il est inutilisable."""
    try:
        resultat = subprocess.run(
            [str(executable), "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            # Ne pas faire clignoter une fenetre de console sous Windows.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    # `java -version` ecrit sur la sortie d'erreur, pas la sortie standard.
    texte = (resultat.stderr or "") + (resultat.stdout or "")
    for morceau in texte.replace('"', " ").split():
        tete = morceau.split(".")[0]
        if tete.isdigit():
            majeure = int(tete)
            # Java 8 s'annonce « 1.8.0_xxx » : la majeure est le second nombre.
            if majeure == 1:
                parties = morceau.split(".")
                if len(parties) > 1 and parties[1].isdigit():
                    return int(parties[1])
                continue
            return majeure
    return None


def trouver() -> Path:
    """Renvoie un executable Java utilisable, ou leve JavaIntrouvable."""
    trop_vieux: list[tuple[Path, int]] = []

    for candidat in _candidats():
        if not candidat.is_file():
            continue
        majeure = version(candidat)
        if majeure is None:
            continue
        if majeure >= VERSION_MINIMALE:
            return candidat
        trop_vieux.append((candidat, majeure))

    if trop_vieux:
        chemin, majeure = trop_vieux[0]
        raise JavaIntrouvable(
            f"Java {majeure} detecte ({chemin}), mais le moteur de correction "
            f"exige Java {VERSION_MINIMALE} ou plus recent.\n"
            "Installez-le depuis https://adoptium.net/ puis relancez."
        )

    raise JavaIntrouvable(
        "Java est introuvable ; le moteur de correction en a besoin.\n"
        "Relancez installer.bat, qui l'installera automatiquement, "
        "ou installez-le depuis https://adoptium.net/."
    )


def preparer() -> Path:
    """Rend Java visible pour LanguageTool et renvoie son chemin.

    LanguageTool appelle `shutil.which("java")` : il suffit donc de placer le
    dossier du Java retenu en tete du PATH du processus.
    """
    executable = trouver()
    dossier = str(executable.parent)
    chemins = os.environ.get("PATH", "").split(os.pathsep)
    if dossier not in chemins:
        os.environ["PATH"] = os.pathsep.join([dossier] + chemins)
    os.environ.setdefault("JAVA_HOME", str(executable.parent.parent))
    return executable
