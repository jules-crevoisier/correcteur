# -*- coding: utf-8 -*-
"""Assemble une distribution autonome apres la compilation PyInstaller.

PyInstaller n'embarque que le code Python. Cette etape ajoute les deux gros
composants externes — le moteur Java et le dictionnaire francais — a cote de
l'executable, pour que le dossier produit fonctionne sur une machine ou ni
Python ni Java ne sont installes.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DISTRIBUTION = RACINE / "dist" / "Correcteur"


def _taille(dossier: Path) -> str:
    octets = sum(f.stat().st_size for f in dossier.rglob("*") if f.is_file())
    return f"{octets / 1_048_576:.0f} Mo"


def _copier(source: Path, cible: Path, libelle: str) -> bool:
    if cible.exists():
        shutil.rmtree(cible)
    print(f"  Copie de {libelle} ({_taille(source)})...")
    shutil.copytree(source, cible, symlinks=True)
    return True


def source_moteur() -> Path | None:
    """Dossier ou language_tool_python a installe LanguageTool."""
    depuis_env = os.environ.get("LTP_PATH")
    candidats = [Path(depuis_env)] if depuis_env else []
    candidats.append(Path.home() / ".cache" / "language_tool_python")

    for candidat in candidats:
        if not candidat.is_dir():
            continue
        # Le dossier contient un sous-dossier « LanguageTool-x.y ».
        if any(candidat.glob("LanguageTool-*")):
            return candidat
    return None


def main() -> int:
    if not DISTRIBUTION.is_dir():
        print(f"[X] {DISTRIBUTION} est introuvable. Lancez d'abord PyInstaller.",
              file=sys.stderr)
        return 1

    print(f"Assemblage dans {DISTRIBUTION}")

    # -- Java portable
    jre = RACINE / "jre"
    if jre.is_dir():
        _copier(jre, DISTRIBUTION / "jre", "Java portable")
    else:
        print("  [!] Aucun dossier 'jre' : Java devra etre installe sur la")
        print("      machine de destination. Lancez outils\\installer_java.ps1")
        print("      puis relancez ce script pour une distribution autonome.")

    # -- Dictionnaire francais
    moteur = source_moteur()
    if moteur is not None:
        _copier(moteur, DISTRIBUTION / "moteur", "dictionnaire francais")
    else:
        print("  [!] LanguageTool introuvable : il sera telecharge au premier")
        print("      lancement. Lancez 'python -m correcteur --verifier' puis")
        print("      relancez ce script pour l'embarquer.")

    # -- Reglages d'exemple, pour que l'utilisateur sache ou regarder
    lisez_moi = DISTRIBUTION / "LISEZ-MOI.txt"
    lisez_moi.write_text(
        "Correcteur\n"
        "==========\n\n"
        "Lancez Correcteur.exe. Une icone bleue apparait pres de l'horloge.\n\n"
        "Selectionnez du texte n'importe ou, appuyez sur Ctrl+Alt+C :\n"
        "le texte corrige remplace la selection.\n\n"
        "Clic droit sur l'icone pour mettre en pause, ouvrir les reglages\n"
        "ou activer le lancement au demarrage de Windows.\n\n"
        "Ce dossier est autonome et deplacable. Si vous le deplacez alors\n"
        "que le demarrage automatique est actif, l'application corrige\n"
        "le chemin toute seule au lancement suivant.\n",
        encoding="utf-8",
    )

    print(f"\nTermine. Taille totale : {_taille(DISTRIBUTION)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
