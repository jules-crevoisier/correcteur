# -*- coding: utf-8 -*-
"""La marque de Papote : une bulle qui parle, dessinee proprement.

Les icones de `icones.py` sont des grilles de pixels. A seize pixels de cote
c'est le bon choix — chaque point tombe juste, rien ne bave. Agrandies a cent
vingt-huit, elles deviennent des paves : c'est ce qui donnait a l'installateur
son air de logiciel de 1998.

Ce module dessine la meme bulle en formes pleines, et la rend lisse par
suréchantillonnage : on trace quatre fois trop grand, puis on reduit. Les
bords obliques y gagnent leur degrade, et la bulle reste nette a n'importe
quelle taille.

Deux sorties, pour deux mondes :

    dessiner()   une image Pillow, pour l'icone Windows et l'installateur ;
    svg()        le meme trace en SVG, pour la fenetre en HTML.

Les proportions sont exprimees en fractions du cote : le dessin ne connait
pas sa taille finale, ce qui lui permet d'etre juste a toutes.
"""

from __future__ import annotations

from . import couleurs

# Suréchantillonnage. Au-dela de quatre, l'oeil ne voit plus la difference et
# la memoire, elle, la voit passer.
FINESSE = 4

# La bulle, en fractions du cote. Elle n'occupe pas tout le carre : une icone
# qui touche ses bords parait plus grosse que ses voisines dans une barre des
# taches, et mal cadree partout ailleurs.
GAUCHE, DROITE = 0.085, 0.915
HAUT, BAS = 0.155, 0.665
RAYON = 0.240

# La queue de la bulle, en bas a gauche : trois points qui suffisent a la
# faire lire comme une parole plutot que comme un bouton.
QUEUE = ((0.255, 0.640), (0.215, 0.880), (0.470, 0.640))

# Les trois points de suspension, alignes dans la bulle.
POINTS_Y = 0.410
POINTS_X = (0.315, 0.500, 0.685)
POINT_RAYON = 0.058


def _melange(depart: str, arrivee: str, part: float) -> tuple[int, int, int]:
    """Une couleur entre deux autres. `part` va de 0 (depart) a 1 (arrivee)."""
    a = _rvb(depart)
    b = _rvb(arrivee)
    return tuple(round(x + (y - x) * part) for x, y in zip(a, b))


def _rvb(valeur: str) -> tuple[int, int, int]:
    valeur = valeur.lstrip("#")[:6]
    return tuple(int(valeur[i:i + 2], 16) for i in (0, 2, 4))


def dessiner(taille: int = 256, fond: str | None = None,
             teinte: str = couleurs.ACCENT,
             lumiere: str = couleurs.ACCENT_VIF):
    """La bulle, en image Pillow carree de `taille` pixels.

    `fond` colore le carre ; laisse a None, l'image est transparente, ce qui
    est ce qu'il faut pour une icone.
    """
    from PIL import Image, ImageDraw

    cote = taille * FINESSE
    image = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(image)

    def px(fraction: float) -> float:
        return fraction * cote

    # -- la bulle et sa queue, en blanc plein : ce calque servira de pochoir
    #    au degrade. Peindre le degrade a travers une forme donne un resultat
    #    plus propre que de peindre la forme ligne par ligne.
    pochoir = Image.new("L", (cote, cote), 0)
    trace = ImageDraw.Draw(pochoir)
    trace.rounded_rectangle(
        (px(GAUCHE), px(HAUT), px(DROITE), px(BAS)),
        radius=px(RAYON), fill=255,
    )
    trace.polygon([(px(x), px(y)) for x, y in QUEUE], fill=255)

    # -- le degrade, du haut vers le bas
    degrade = Image.new("RGB", (1, cote))
    peinture = ImageDraw.Draw(degrade)
    for y in range(cote):
        peinture.point((0, y), fill=_melange(lumiere, teinte, y / cote))
    degrade = degrade.resize((cote, cote))

    image.paste(degrade, (0, 0), pochoir)

    # -- les trois points, creuses dans la bulle
    creux = fond or couleurs.FOND
    for x in POINTS_X:
        dessin.ellipse(
            (px(x - POINT_RAYON), px(POINTS_Y - POINT_RAYON),
             px(x + POINT_RAYON), px(POINTS_Y + POINT_RAYON)),
            fill=_rvb(creux) + (255,),
        )

    image = image.resize((taille, taille), Image.LANCZOS)

    if fond is None:
        return image
    carre = Image.new("RGB", (taille, taille), _rvb(fond))
    carre.paste(image, (0, 0), image)
    return carre


def svg(taille: int = 64, teinte: str = couleurs.ACCENT,
        lumiere: str = couleurs.ACCENT_VIF,
        creux: str = couleurs.FOND, identifiant: str = "papote") -> str:
    """Le meme trace, en SVG, pour la fenetre en HTML.

    Le SVG est ecrit sur une grille de cent, ce qui rend les fractions
    ci-dessus lisibles telles quelles dans le fichier produit.
    """
    def n(fraction: float) -> str:
        return f"{fraction * 100:.4g}"

    queue = " ".join(f"{n(x)},{n(y)}" for x, y in QUEUE)
    points = "".join(
        f'<circle cx="{n(x)}" cy="{n(POINTS_Y)}" r="{n(POINT_RAYON)}" '
        f'fill="{creux}"/>'
        for x in POINTS_X
    )
    return (
        f'<svg width="{taille}" height="{taille}" viewBox="0 0 100 100" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Papote">'
        f'<defs><linearGradient id="{identifiant}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{lumiere}"/>'
        f'<stop offset="1" stop-color="{teinte}"/>'
        f'</linearGradient></defs>'
        f'<g fill="url(#{identifiant})">'
        f'<rect x="{n(GAUCHE)}" y="{n(HAUT)}" '
        f'width="{n(DROITE - GAUCHE)}" height="{n(BAS - HAUT)}" '
        f'rx="{n(RAYON)}"/>'
        f'<polygon points="{queue}"/>'
        f'</g>{points}</svg>'
    )
