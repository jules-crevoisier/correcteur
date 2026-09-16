# -*- coding: utf-8 -*-
"""Fabrique les images de l'installateur a partir des icones du programme.

Windows Installer reclame deux bitmaps a des dimensions fixes, heritees des
annees quatre-vingt-dix : une banniere de 493 x 58 en haut des pages, et un
fond de 493 x 312 pour la premiere et la derniere. Les dessiner a la main
serait du travail perdu : ce sont les memes pixels que l'application, en plus
grand.

    python outils/images_installateur.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

DESTINATION = RACINE / "installateur"

BANNIERE = (493, 58)
FOND = (493, 312)


def _couleur(valeur: str) -> tuple[int, int, int]:
    from papote.icones import _en_rvba

    return _en_rvba(valeur)[:3]


def _poser_icone(image, nom: str, couleurs: dict, taille: int, position):
    from papote import icones

    sprite = icones.image_pil(nom, couleurs, taille)
    image.paste(sprite, position, sprite)


def _ecrire(image, texte: str, position, taille: int, couleur):
    """Ecrit sans dependre d'une police du systeme : chaque lettre est dessinee.

    Une police manquante sur la machine de compilation donnerait une image
    differente a chaque fois ; les pixels, eux, ne bougent pas.
    """
    from PIL import ImageDraw

    dessin = ImageDraw.Draw(image)
    dessin.text(position, texte, fill=couleur)


def construire() -> list[Path]:
    from PIL import Image

    from papote import couleurs, icones

    fond = _couleur(couleurs.FOND)
    accent = _couleur(couleurs.ACCENT)
    palette = icones.palette(couleurs.ACCENT, couleurs.FOND,
                             lumiere=couleurs.ACCENT_VIF)

    DESTINATION.mkdir(parents=True, exist_ok=True)
    ecrits = []

    # -- l'icone du programme, en plusieurs tailles dans un seul fichier :
    #    Windows choisit la bonne selon l'endroit ou il l'affiche.
    icone = icones.image_pil("papote", palette, 256)
    chemin = DESTINATION / "papote.ico"
    icone.save(chemin, sizes=[(taille, taille)
                              for taille in (16, 24, 32, 48, 64, 128, 256)])
    ecrits.append(chemin)

    # -- la banniere : la bulle a gauche, sur le fond sombre
    banniere = Image.new("RGB", BANNIERE, fond)
    _poser_icone(banniere, "papote", palette, 40, (18, 9))
    _ecrire(banniere, "Papote", (70, 20), 18, accent)
    chemin = DESTINATION / "banniere.bmp"
    banniere.save(chemin)
    ecrits.append(chemin)

    # -- le fond : une grande bulle, centree en haut a gauche
    grand = Image.new("RGB", FOND, fond)
    _poser_icone(grand, "papote", palette, 128, (40, 60))
    _ecrire(grand, "Papote", (40, 200), 24, accent)
    _ecrire(grand, "Le correcteur qui vous laisse parler", (40, 220), 12,
            _couleur(couleurs.TEXTE_DOUX))
    chemin = DESTINATION / "fond.bmp"
    grand.save(chemin)
    ecrits.append(chemin)

    return ecrits


def main() -> int:
    for chemin in construire():
        print(f"  {chemin.relative_to(RACINE)} "
              f"({chemin.stat().st_size // 1024} Ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
