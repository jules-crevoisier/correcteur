# -*- mode: python ; coding: utf-8 -*-
"""Recette PyInstaller : un seul fichier Papote.exe, dictionnaire compris.

    pyinstaller --noconfirm --clean papote.spec

Le resultat tient dans « dist/Papote.exe » et ne demande ni Python ni
quoi que ce soit d'autre sur la machine de destination.
"""

from pathlib import Path

RACINE = Path(SPECPATH)

# L'icone est fabriquee par « outils/images_installateur.py ». Si elle n'est
# pas la — compilation rapide en local — PyInstaller met la sienne.
ICONE = RACINE / "installateur" / "papote.ico"

analyse = Analysis(
    ["lancement.py"],
    pathex=[str(RACINE)],
    binaries=[],
    # Le dictionnaire francais voyage avec l'executable ; « chemins.py » le
    # retrouve dans le dossier temporaire ou PyInstaller le deplie. Seuls les
    # fichiers lus a l'execution sont embarques : « fr.dic » et « fr.aff »
    # ne servent qu'a les regenerer.
    datas=[
        (str(RACINE / "donnees" / "lexique_fr.txt.gz"), "donnees"),
        (str(RACINE / "donnees" / "frequences_fr.txt.gz"), "donnees"),
        (str(RACINE / "donnees" / "LICENCES.md"), "donnees"),
        # La fenetre est une page web : elle voyage avec le reste.
        (str(RACINE / "papote" / "web"), "papote/web"),
    ],
    # « webview » choisit son moteur au moment de demarrer, par un import
    # calcule que PyInstaller ne sait pas suivre : sans cette ligne, la
    # fenetre se replierait sur l'ancienne une fois compilee.
    hiddenimports=["pystray._win32", "webview.platforms.edgechromium",
                   "clr_loader", "pythonnet"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib", "PySide6", "PyQt5", "test"],
    noarchive=False,
)

pyz = PYZ(analyse.pure)

exe = EXE(
    pyz,
    analyse.scripts,
    analyse.binaries,
    analyse.datas,
    [],
    name="Papote",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # Aucune fenetre de console : l'application vit dans la zone de
    # notification.
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICONE) if ICONE.exists() else None,
)
