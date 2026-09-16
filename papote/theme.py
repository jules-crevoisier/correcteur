# -*- coding: utf-8 -*-
"""Les widgets dessines a la main.

tkinter donne des widgets gris des annees quatre-vingt-dix. Tout ce qui suit
sert a le faire oublier : bouton aux angles arrondis, interrupteur a bascule,
entree de navigation — aucun n'existe chez tkinter, tous sont dessines sur un
canevas, parce que c'est la seule facon d'avoir des coins ronds.

La palette et les espacements vivent dans `couleurs.py`, qui ne depend de
rien : l'icone de la barre des taches s'en sert sans charger tkinter.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from . import icones

from .couleurs import (  # noqa: F401 — reexportes pour les widgets
    ACCENT, ACCENT_SOURD, ACCENT_VIF, ALERTE, BORDURE, BORDURE_VIVE, FAMILLE,
    FOND, GRAND, MOYEN, PETIT, SUCCES, SURFACE, SURFACE_HAUTE, TEXTE,
    TEXTE_DOUX, TEXTE_ETEINT, TRES_GRAND, police,
)


def _largeur_texte(texte: str, taille: int, gras: bool) -> int:
    """Largeur reelle du texte, pour dimensionner ce qu'on dessine autour."""
    try:
        mesure = tkfont.Font(family=FAMILLE, size=taille,
                             weight="bold" if gras else "normal")
        return mesure.measure(texte)
    except tk.TclError:
        # Pas de fenetre : une approximation vaut mieux qu'une exception.
        return len(texte) * (taille - 2)


# ---------------------------------------------------------------------------
# Dessin
# ---------------------------------------------------------------------------

def rectangle_arrondi(canevas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                      rayon: int, **options):
    """Un rectangle aux angles arrondis, faute d'en avoir un chez tkinter."""
    rayon = min(rayon, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + rayon, y1, x2 - rayon, y1, x2, y1, x2, y1 + rayon,
        x2, y2 - rayon, x2, y2, x2 - rayon, y2, x1 + rayon, y2,
        x1, y2, x1, y2 - rayon, x1, y1 + rayon, x1, y1,
    ]
    return canevas.create_polygon(points, smooth=True, **options)


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

class Bouton:
    """Un bouton aux angles arrondis, qui s'eclaire au survol."""

    HAUTEUR = 34
    HAUTEUR_PETIT = 26
    MARGE = 16

    def __init__(self, parent, texte: str, commande=None, principal: bool = False,
                 petit: bool = False, icone: str | None = None,
                 fond: str = FOND):
        self.commande = commande
        self.actif = True
        self.principal = principal
        self.fond = fond

        taille_police = 9 if petit else 10
        hauteur = self.HAUTEUR_PETIT if petit else self.HAUTEUR
        marge = 10 if petit else self.MARGE

        self.repos = ACCENT if principal else SURFACE_HAUTE
        self.survol = ACCENT_VIF if principal else BORDURE
        self.couleur_texte = "white" if principal else TEXTE

        self.image = None
        decalage = 0
        if icone is not None:
            self.image = icones.image_tk(
                icone, icones.palette(self.couleur_texte, self.repos), self.repos, 1
            )
            decalage = icones.TAILLE + 6

        largeur = _largeur_texte(texte, taille_police, principal) + 2 * marge + decalage

        self.canevas = tk.Canvas(parent, width=largeur, height=hauteur, bg=fond,
                                 highlightthickness=0, cursor="hand2")
        self.forme = rectangle_arrondi(self.canevas, 0, 0, largeur - 1, hauteur - 1,
                                       8, fill=self.repos, outline="")
        if self.image is not None:
            self.canevas.create_image(marge, hauteur // 2, image=self.image,
                                      anchor="w")
        self.etiquette = self.canevas.create_text(
            marge + decalage, hauteur // 2, text=texte, anchor="w",
            fill=self.couleur_texte, font=police(taille_police, principal),
        )

        self.canevas.bind("<Enter>", self._entrer)
        self.canevas.bind("<Leave>", self._sortir)
        self.canevas.bind("<Button-1>", self._cliquer)

    def _entrer(self, _=None):
        if self.actif:
            self.canevas.itemconfigure(self.forme, fill=self.survol)

    def _sortir(self, _=None):
        self.canevas.itemconfigure(self.forme, fill=self.repos if self.actif
                                   else SURFACE)

    def _cliquer(self, _=None):
        if self.actif and self.commande is not None:
            self.commande()

    def configurer(self, texte: str | None = None, actif: bool | None = None):
        if texte is not None:
            self.canevas.itemconfigure(self.etiquette, text=texte)
        if actif is not None:
            self.actif = actif
            self.canevas.itemconfigure(self.forme,
                                       fill=self.repos if actif else SURFACE)
            self.canevas.itemconfigure(
                self.etiquette, fill=self.couleur_texte if actif else TEXTE_ETEINT)
            self.canevas.configure(cursor="hand2" if actif else "")

    def pack(self, **options):
        self.canevas.pack(**options)
        return self

    def grid(self, **options):
        self.canevas.grid(**options)
        return self


class Interrupteur:
    """Un interrupteur a bascule, comme sur un telephone."""

    LARGEUR, HAUTEUR = 38, 22

    def __init__(self, parent, valeur: bool = False, commande=None,
                 fond: str = SURFACE):
        self.variable = tk.BooleanVar(value=valeur)
        self.commande = commande

        self.canevas = tk.Canvas(parent, width=self.LARGEUR, height=self.HAUTEUR,
                                 bg=fond, highlightthickness=0, cursor="hand2")
        self.piste = rectangle_arrondi(self.canevas, 1, 1, self.LARGEUR - 2,
                                       self.HAUTEUR - 2, 10, fill=SURFACE_HAUTE,
                                       outline="")
        self.bouton = self.canevas.create_oval(0, 0, 0, 0, fill=TEXTE_DOUX,
                                               outline="")
        self.canevas.bind("<Button-1>", self._basculer)
        self._dessiner()

    def _dessiner(self):
        allume = bool(self.variable.get())
        self.canevas.itemconfigure(self.piste,
                                   fill=ACCENT if allume else SURFACE_HAUTE)
        rayon = self.HAUTEUR - 8
        x = self.LARGEUR - rayon - 4 if allume else 4
        self.canevas.coords(self.bouton, x, 4, x + rayon, 4 + rayon)
        self.canevas.itemconfigure(self.bouton,
                                   fill="white" if allume else TEXTE_DOUX)

    def _basculer(self, _=None):
        self.variable.set(not self.variable.get())
        self._dessiner()
        if self.commande is not None:
            self.commande()

    def get(self) -> bool:
        return bool(self.variable.get())

    def set(self, valeur: bool) -> None:
        self.variable.set(bool(valeur))
        self._dessiner()

    def pack(self, **options):
        self.canevas.pack(**options)
        return self


class EntreeNavigation:
    """Une ligne de la colonne de gauche : icone, libelle, et etat."""

    HAUTEUR = 38

    def __init__(self, parent, nom: str, icone: str, commande):
        self.nom = nom
        self.commande = commande
        self.choisie = False

        self.cadre = tk.Frame(parent, bg=FOND, height=self.HAUTEUR)
        self.cadre.pack_propagate(False)

        self.image = icones.image_tk(icone, icones.palette(TEXTE_DOUX, FOND),
                                     FOND, 1)
        self.icone = tk.Label(self.cadre, image=self.image, bg=FOND, bd=0)
        self.icone.pack(side="left", padx=(12, 10))

        self.etiquette = tk.Label(self.cadre, text=nom, bg=FOND, fg=TEXTE_DOUX,
                                  font=police(10), anchor="w")
        self.etiquette.pack(side="left", fill="x", expand=True)

        for widget in (self.cadre, self.icone, self.etiquette):
            widget.bind("<Button-1>", lambda _e: self.commande(self.nom))
            widget.bind("<Enter>", self._entrer)
            widget.bind("<Leave>", self._sortir)
            widget.configure(cursor="hand2")

    def _peindre(self, fond: str, couleur_texte: str) -> None:
        self.cadre.configure(bg=fond)
        self.icone.configure(bg=fond)
        self.etiquette.configure(bg=fond, fg=couleur_texte)

    def _entrer(self, _=None):
        if not self.choisie:
            self._peindre(SURFACE, TEXTE)

    def _sortir(self, _=None):
        if not self.choisie:
            self._peindre(FOND, TEXTE_DOUX)

    def choisir(self, choisie: bool) -> None:
        self.choisie = choisie
        if choisie:
            self._peindre(ACCENT_SOURD, TEXTE)
            self.etiquette.configure(font=police(10, gras=True))
        else:
            self._peindre(FOND, TEXTE_DOUX)
            self.etiquette.configure(font=police(10))

    def pack(self, **options):
        self.cadre.pack(**options)
        return self


# ---------------------------------------------------------------------------
# Petits assemblages
# ---------------------------------------------------------------------------

def carte(parent, **options) -> tk.Frame:
    """Un panneau pose sur le fond, ou l'on range ce qui va ensemble."""
    return tk.Frame(parent, bg=SURFACE, highlightthickness=1,
                    highlightbackground=BORDURE, **options)


def titre(parent, texte: str, fond: str = SURFACE) -> tk.Label:
    return tk.Label(parent, text=texte, bg=fond, fg=TEXTE, anchor="w",
                    font=police(11, gras=True))


def note(parent, texte: str, fond: str = SURFACE, **options) -> tk.Label:
    return tk.Label(parent, text=texte, bg=fond, fg=TEXTE_DOUX, anchor="w",
                    justify="left", font=police(9), **options)


def entree(parent, largeur: int = 20, fond: str = SURFACE_HAUTE) -> tk.Entry:
    return tk.Entry(parent, bg=fond, fg=TEXTE, relief="flat", width=largeur,
                    insertbackground=ACCENT, font=police(10),
                    highlightthickness=1, highlightbackground=BORDURE,
                    highlightcolor=ACCENT)


def liste(parent, hauteur: int = 8, fond: str = SURFACE_HAUTE) -> tk.Listbox:
    return tk.Listbox(parent, bg=fond, fg=TEXTE, relief="flat", borderwidth=0,
                      height=hauteur, font=police(10), selectbackground=ACCENT,
                      selectforeground="white", highlightthickness=1,
                      highlightbackground=BORDURE, activestyle="none")


def texte(parent, hauteur: int | None = None, fond: str = SURFACE_HAUTE) -> tk.Text:
    options = {"height": hauteur} if hauteur else {}
    return tk.Text(parent, wrap="word", bg=fond, fg=TEXTE, relief="flat",
                   insertbackground=ACCENT, padx=14, pady=12, font=police(11),
                   undo=True, highlightthickness=1, highlightbackground=BORDURE,
                   highlightcolor=BORDURE, **options)
