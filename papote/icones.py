# -*- coding: utf-8 -*-
"""Les icones de Papote, dessinees en pixel art.

Chaque icone est une grille de caracteres — un caractere, un pixel — et une
palette qui dit quelle couleur porte chaque caractere. Ecrire une icone
revient donc a la dessiner, et la relire revient a la voir :

        ....########....
        ..############..
        .##############.
        .#.oo..oo..oo.#.

Le rendu se fait a l'agrandissement entier, sans lissage : un pixel devient
un carre de quatre, de huit ou de seize, et le trait reste net. C'est tout
l'interet du pixel art pour une icone de barre des taches, ou chaque pixel
compte.

Rien ici ne depend de Pillow : `tkinter.PhotoImage` sait poser des pixels un
par un. Seule l'icone de la zone de notification passe par Pillow, que
`pystray` exige de toute facon.
"""

from __future__ import annotations

TAILLE = 16

# Caracteres transparents. Tout le reste doit figurer dans la palette.
VIDE = " ."


def _grille(dessin: str) -> list[str]:
    """Transforme un dessin en grille carree, en completant les lignes courtes."""
    lignes = [ligne for ligne in dessin.strip("\n").split("\n")]
    return [ligne.ljust(TAILLE, ".")[:TAILLE] for ligne in lignes]


# ---------------------------------------------------------------------------
# Les dessins
#
# « # » le trait principal, « o » le creux (couleur du fond), « + » la
# lumiere, « a » la couleur d'accent.
# ---------------------------------------------------------------------------

DESSINS = {
    # La marque : une bulle de conversation. Papote, tout simplement.
    "papote": _grille("""
....########....
..############..
.####++++++####.
.##############.
.##############.
.#.oo..oo..oo.#.
.#.oo..oo..oo.#.
.##############.
.##############.
..############..
...####.........
..####..........
.###............
.#..............
"""),

    # Un crayon : corriger.
    "crayon": _grille("""
................
..........###...
.........##+##..
........##+##...
.......##+##....
......##+##.....
.....##+##......
....##+##.......
...##+##........
..##+##.........
..#+##..........
..####..........
..###...........
"""),

    # Un livre ouvert : le dictionnaire.
    "livre": _grille("""
................
...##......##...
..####....####..
.###o#....#o###.
.##ooo#..#ooo##.
.##ooo#..#ooo##.
.##ooo#..#ooo##.
.##ooo#..#ooo##.
.##ooo####ooo##.
.##oooooooooo##.
.##############.
..############..
"""),

    # Trois barres : vos fautes.
    "barres": _grille("""
................
.............##.
.............##.
.........##..##.
.........##..##.
.....##..##..##.
.....##..##..##.
.....##..##..##.
.##..##..##..##.
.##..##..##..##.
.##..##..##..##.
.##############.
"""),

    # Une fenetre : les applications.
    "fenetre": _grille("""
................
.##############.
.##############.
.#o#..........#.
.#............#.
.#....####....#.
.#....####....#.
.#............#.
.#............#.
.##############.
"""),

    # Trois curseurs : les reglages.
    "reglages": _grille("""
................
....##..........
.##############.
....##..........
................
..........##....
.##############.
..........##....
................
.......##.......
.##############.
.......##.......
"""),

    # Une fleche qui descend dans un bac : la mise a jour.
    "telecharger": _grille("""
................
.......##.......
.......##.......
.......##.......
.......##.......
..##...##...##..
...##..##..##...
....##.##.##....
.....######.....
......###.......
................
.##..........##.
.##############.
.##############.
"""),

    # Une fleche qui revient : annuler.
    "annuler": _grille("""
................
....######......
...##....##.....
..##......##....
..##............
.####...........
..##............
...##...........
"""),

    # Une coche : c'est fait.
    "coche": _grille("""
................
.............##.
............##..
...........##...
..##......##....
...##....##.....
....##..##......
.....####.......
......##........
"""),
}


def palette(trait: str, fond: str, lumiere: str | None = None,
            accent: str | None = None) -> dict[str, str]:
    """Associe une couleur a chaque caractere d'un dessin."""
    return {
        "#": trait,
        "o": fond,
        "+": lumiere or trait,
        "a": accent or trait,
    }


def pixels(nom: str) -> list[str]:
    """La grille du dessin demande."""
    try:
        return DESSINS[nom]
    except KeyError:
        raise KeyError(f"icone inconnue : {nom}") from None


def _lignes_de_couleurs(nom: str, couleurs: dict[str, str],
                        transparent: str) -> list[list[str]]:
    """La grille, traduite en couleurs, prete a etre posee pixel par pixel."""
    return [
        [transparent if caractere in VIDE
         else couleurs.get(caractere, couleurs["#"])
         for caractere in ligne]
        for ligne in pixels(nom)
    ]


def image_tk(nom: str, couleurs: dict[str, str], fond: str, zoom: int = 2):
    """Une icone prete pour tkinter, agrandie sans lissage.

    tkinter ne gere pas la transparence sur un PhotoImage construit a la main :
    les pixels vides prennent donc la couleur du fond sur lequel l'icone sera
    posee. C'est sans importance — on sait toujours ou on la pose.
    """
    import tkinter as tk

    grille = _lignes_de_couleurs(nom, couleurs, fond)
    image = tk.PhotoImage(width=TAILLE, height=len(grille))
    for y, ligne in enumerate(grille):
        # « put » accepte une ligne entiere d'un coup : seize fois moins
        # d'appels, et le demarrage de la fenetre s'en ressent.
        image.put("{" + " ".join(ligne) + "}", to=(0, y))
    return image.zoom(zoom) if zoom > 1 else image


def image_pil(nom: str, couleurs: dict[str, str], taille: int = 64):
    """La meme icone pour la zone de notification, fond transparent."""
    from PIL import Image

    grille = pixels(nom)
    image = Image.new("RGBA", (TAILLE, len(grille)), (0, 0, 0, 0))
    pixel = image.load()
    for y, ligne in enumerate(grille):
        for x, caractere in enumerate(ligne):
            if caractere in VIDE:
                continue
            pixel[x, y] = _en_rvba(couleurs.get(caractere, couleurs["#"]))

    cote = max(TAILLE, len(grille))
    carree = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    carree.paste(image, (0, (cote - len(grille)) // 2))
    # NEAREST : c'est ce qui garde les pixels carres.
    return carree.resize((taille, taille), Image.NEAREST)


def _en_rvba(couleur: str) -> tuple[int, int, int, int]:
    """« #2b7ade » -> (43, 122, 222, 255)."""
    valeur = couleur.lstrip("#")
    if len(valeur) == 3:
        valeur = "".join(c * 2 for c in valeur)
    return (int(valeur[0:2], 16), int(valeur[2:4], 16),
            int(valeur[4:6], 16), 255)
