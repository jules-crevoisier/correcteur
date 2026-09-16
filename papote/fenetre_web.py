# -*- coding: utf-8 -*-
"""La fenetre de Papote : une page web rendue par le moteur d'Edge.

tkinter etait un mur. Il ne sait ni adoucir un coin, ni poser une ombre, ni
animer quoi que ce soit ; tout ce qui avait l'air soigne dans l'ancienne
fenetre etait dessine trait par trait sur un Canvas, et se voyait quand
meme. Le moteur d'Edge, lui, est installe sur toutes les machines depuis
Windows 10, il ne se telecharge pas, et il rend une page comme un
navigateur.

Ce module est volontairement mince. Tout ce que la fenetre sait faire est
dans `passerelle.py`, qui ne connait rien a l'affichage et se teste sans
ecran ; tout ce qu'elle montre est dans `web/`. Ici, on ouvre la fenetre et
on branche l'un a l'autre.

Le repli compte autant que le reste : sur une machine ou le moteur manque,
Papote ouvre l'ancienne fenetre plutot que de ne rien ouvrir du tout. Une
fenetre qui refuse de s'afficher ne laisse aucun moyen de dire pourquoi.
"""

from __future__ import annotations

import sys

from . import journal as journal_mod
from .chemins import dossier_web

TITRE = "Papote"
LARGEUR, HAUTEUR = 980, 700
LARGEUR_MINIMALE, HAUTEUR_MINIMALE = 560, 460


def disponible() -> bool:
    """Le moteur de rendu est-il la ?

    On ne cherche que l'import : savoir si le moteur d'Edge repondra vraiment
    demande de l'ouvrir, et une fenetre qui clignote pour rien est pire qu'un
    repli.
    """
    try:
        import webview  # noqa: F401
    except Exception:                                # noqa: BLE001
        return False
    return True


def ouvrir(app) -> bool:
    """Ouvre la fenetre et rend la main quand elle se ferme.

    Renvoie False si la fenetre n'a pas pu s'ouvrir, pour que l'appelant
    tente l'ancienne.
    """
    try:
        import webview
    except Exception as e:                           # noqa: BLE001
        journal_mod.erreur("Moteur de rendu indisponible", e)
        return False

    from .passerelle import Passerelle

    passerelle = Passerelle(app)
    page = dossier_web() / "index.html"
    if not page.is_file():
        journal_mod.erreur(f"Page introuvable : {page}")
        return False

    try:
        fenetre = webview.create_window(
            TITRE,
            str(page),
            js_api=passerelle,
            width=LARGEUR,
            height=HAUTEUR,
            min_size=(LARGEUR_MINIMALE, HAUTEUR_MINIMALE),
            # Le fond est pose avant que la page n'arrive : sans lui, la
            # fenetre s'ouvre sur un rectangle blanc, et le passage au theme
            # sombre se voit comme un eclair.
            background_color="#0e1014",
            text_select=True,
        )
        webview.start(gui=_moteur(), private_mode=False,
                      storage_path=str(_dossier_moteur()))
        del fenetre
    except Exception as e:                           # noqa: BLE001
        journal_mod.erreur("La fenetre n'a pas pu s'ouvrir", e)
        return False
    return True


def _moteur() -> str | None:
    """Le moteur de rendu a employer.

    Sur Windows on impose celui d'Edge : laisse a lui-meme, pywebview peut
    retomber sur l'ancien moteur d'Internet Explorer, qui ne comprend rien de
    ce qu'emploie la page.
    """
    return "edgechromium" if sys.platform == "win32" else None


def _dossier_moteur():
    """Ou le moteur range ses fichiers de travail.

    A cote des reglages, et non dans le dossier du programme : celui-ci est
    parfois en lecture seule, et une mise a jour le remplace.
    """
    from .config import dossier_config

    dossier = dossier_config() / "moteur"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier
