# -*- coding: utf-8 -*-
"""Fabrique l'icone du programme et les images de l'installateur.

Windows Installer reclame deux bitmaps a des dimensions fixes, heritees des
annees quatre-vingt-dix : une banniere de 493 x 58 en haut des pages
interieures, et un fond de 493 x 312 pour la premiere page et la derniere.

Ces dimensions imposent la composition, parce que WixUI ecrit son propre
texte par-dessus, toujours au meme endroit :

    fond 493 x 312     le titre et le paragraphe d'accueil occupent la droite,
                       a partir de x = 135. Le dessin tient donc dans la
                       colonne de gauche, et le reste lui sert de page.

    banniere 493 x 58  le titre de la page est ecrit a gauche. La marque va
                       donc a droite.

C'est l'inverse de ce qui se faisait ici : la bulle, posee a gauche en 128
pixels d'une icone prevue pour seize, chevauchait le texte de Windows et
montrait ses escaliers.

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

# La colonne laissee libre par WixUI sur la page d'accueil.
COLONNE = 135

# Les polices cherchees, dans l'ordre. La premiere trouvee gagne. Segoe UI
# est celle de Windows, ou l'installateur sera lu ; DejaVu permet de voir le
# resultat ailleurs. Sans aucune des deux, Pillow rend sa police de secours,
# moche mais lisible — et la compilation ne s'arrete pas pour si peu.
POLICES = {
    "grasse": ("segoeuisb.ttf", "seguisb.ttf", "segoeuib.ttf",
               "DejaVuSans-Bold.ttf"),
    "normale": ("segoeui.ttf", "DejaVuSans.ttf"),
}

DOSSIERS_POLICES = (
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype"),
    Path("/usr/share/fonts"),
)


def _police(genre: str, taille: int):
    from PIL import ImageFont

    for nom in POLICES[genre]:
        for dossier in DOSSIERS_POLICES:
            chemin = dossier / nom
            if chemin.is_file():
                return ImageFont.truetype(str(chemin), taille)
        # Certaines installations rangent les polices en sous-dossiers.
        for dossier in DOSSIERS_POLICES:
            if dossier.is_dir():
                trouve = next(dossier.rglob(nom), None)
                if trouve is not None:
                    return ImageFont.truetype(str(trouve), taille)
    return ImageFont.load_default()


def _rvb(valeur: str) -> tuple[int, int, int]:
    valeur = valeur.lstrip("#")[:6]
    return tuple(int(valeur[i:i + 2], 16) for i in (0, 2, 4))


def _degrade_vertical(taille, haut: str, bas: str):
    """Un fond qui s'eclaircit vers le bas : une page plutot qu'un aplat.

    Entre deux gris sombres, un degre de vingt-quatre bits ne compte qu'une
    dizaine de valeurs sur trois cents pixels : le degrade sort en bandes
    horizontales, bien visibles. Un grain d'un point casse les bandes sans
    se voir — c'est le tramage qu'employaient les ecrans a peu de couleurs,
    et il sert encore.
    """
    import random

    from PIL import Image, ImageDraw

    largeur, hauteur = taille
    image = Image.new("RGB", (1, hauteur))
    peinture = ImageDraw.Draw(image)
    debut, fin = _rvb(haut), _rvb(bas)
    for y in range(hauteur):
        part = y / max(hauteur - 1, 1)
        peinture.point(
            (0, y),
            fill=tuple(round(a + (b - a) * part) for a, b in zip(debut, fin)),
        )
    image = image.resize((largeur, hauteur))

    grain = random.Random(0)          # le meme grain a chaque compilation
    pixels = image.load()
    for y in range(hauteur):
        for x in range(largeur):
            ecart = grain.randint(-1, 1)
            r, v, b = pixels[x, y]
            pixels[x, y] = (max(0, min(255, r + ecart)),
                            max(0, min(255, v + ecart)),
                            max(0, min(255, b + ecart)))
    return image


def _halo(image, centre, rayon: int, teinte: str, force: float = 0.28):
    """Une lueur diffuse derriere la marque, pour que le coin ne soit pas plat."""
    from PIL import Image, ImageDraw, ImageFilter

    couche = Image.new("L", image.size, 0)
    dessin = ImageDraw.Draw(couche)
    x, y = centre
    dessin.ellipse((x - rayon, y - rayon, x + rayon, y + rayon),
                   fill=round(255 * force))
    couche = couche.filter(ImageFilter.GaussianBlur(rayon * 0.55))
    teinte_pleine = Image.new("RGB", image.size, _rvb(teinte))
    image.paste(teinte_pleine, (0, 0), couche)
    return image


def construire() -> list[Path]:
    from PIL import Image

    from papote import couleurs, logo

    DESTINATION.mkdir(parents=True, exist_ok=True)
    ecrits = []

    # -- l'icone du programme. Un seul fichier, plusieurs tailles : Windows
    #    prend celle qui convient a l'endroit ou il l'affiche.
    tailles = (16, 24, 32, 48, 64, 128, 256)
    icone = logo.dessiner(256)
    chemin = DESTINATION / "papote.ico"
    icone.save(chemin, sizes=[(t, t) for t in tailles])
    ecrits.append(chemin)

    # -- la banniere des pages interieures. Le titre de WixUI occupe la
    #    gauche : la marque se met a droite, discrete.
    banniere = _degrade_vertical(BANNIERE, couleurs.SURFACE, couleurs.FOND)
    marque = logo.dessiner(30)
    banniere.paste(marque, (BANNIERE[0] - 46, 14), marque)
    _ecrire(banniere, "Papote", (BANNIERE[0] - 46 - 62, 21),
            _police("grasse", 14), couleurs.TEXTE_DOUX)
    chemin = DESTINATION / "banniere.bmp"
    banniere.save(chemin)
    ecrits.append(chemin)

    # -- la page d'accueil. Tout le dessin tient dans la colonne de gauche.
    grand = _degrade_vertical(FOND, couleurs.FOND, couleurs.SURFACE)
    _halo(grand, (COLONNE // 2, 118), 96, couleurs.ACCENT)

    bulle = logo.dessiner(76)
    grand.paste(bulle, (COLONNE // 2 - 38, 80), bulle)
    _centrer(grand, "Papote", COLONNE, 172, _police("grasse", 21),
             couleurs.TEXTE)
    _centrer(grand, "le correcteur", COLONNE, 200, _police("normale", 11),
             couleurs.TEXTE_DOUX)
    _centrer(grand, "qui vous laisse parler", COLONNE, 215,
             _police("normale", 11), couleurs.TEXTE_DOUX)

    # Un filet vertical separe la colonne du texte de Windows : sans lui, le
    # paragraphe semble flotter au milieu de nulle part.
    _filet(grand, COLONNE, 46, FOND[1] - 46, couleurs.BORDURE)

    chemin = DESTINATION / "fond.bmp"
    grand.save(chemin)
    ecrits.append(chemin)

    return ecrits


def _ecrire(image, texte: str, position, police, couleur: str) -> None:
    from PIL import ImageDraw

    ImageDraw.Draw(image).text(position, texte, font=police,
                               fill=_rvb(couleur))


def _centrer(image, texte: str, largeur: int, y: int, police,
             couleur: str) -> None:
    from PIL import ImageDraw

    dessin = ImageDraw.Draw(image)
    gauche, _haut, droite, _bas = dessin.textbbox((0, 0), texte, font=police)
    dessin.text(((largeur - (droite - gauche)) // 2 - gauche, y), texte,
                font=police, fill=_rvb(couleur))


def _filet(image, x: int, haut: int, bas: int, couleur: str) -> None:
    from PIL import ImageDraw

    ImageDraw.Draw(image).line((x, haut, x, bas), fill=_rvb(couleur), width=1)


def main() -> int:
    for chemin in construire():
        print(f"  {chemin.relative_to(RACINE)} "
              f"({chemin.stat().st_size // 1024} Ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
