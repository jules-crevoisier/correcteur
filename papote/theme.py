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


def note(parent, texte: str, fond: str = SURFACE,
         wraplength: int | None = None, **options) -> tk.Label:
    """Un texte secondaire, qui se replie a la largeur qu'on lui laisse.

    Une longueur de repli fixe donne une colonne de texte qui deborde des
    qu'on retrecit la fenetre, ou qui laisse la moitie de la place vide des
    qu'on l'agrandit. Suivre la largeur reelle coute une liaison.
    """
    etiquette = tk.Label(parent, text=texte, bg=fond, fg=TEXTE_DOUX, anchor="w",
                         justify="left", font=police(9), **options)
    if wraplength is not None:
        etiquette.configure(wraplength=wraplength)
        return etiquette

    dernier = {"largeur": 0}

    def replier(evenement):
        utile = max(180, evenement.width - 4)
        # Redimensionner a chaque pixel relancerait l'evenement sans fin.
        if abs(utile - dernier["largeur"]) > 8:
            dernier["largeur"] = utile
            etiquette.configure(wraplength=utile)

    etiquette.bind("<Configure>", replier)
    return etiquette


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


class BarreDefilement:
    """Une barre de defilement fine, dessinee.

    Celle de tkinter a l'apparence que Windows lui donne : grise, large, et
    parfaitement deplacee au milieu d'un fond sombre. Celle-ci n'est qu'un
    rectangle arrondi qui suit la vue, s'attrape a la souris, et disparait
    quand il n'y a rien a faire defiler.
    """

    LARGEUR = 10
    EPAISSEUR = 6

    def __init__(self, parent, commande, fond: str = FOND):
        self.commande = commande          # yview de la toile
        self.debut, self.fin = 0.0, 1.0
        self.saisie = None

        self.canevas = tk.Canvas(parent, width=self.LARGEUR, bg=fond,
                                 highlightthickness=0)
        self.curseur = rectangle_arrondi(self.canevas, 2, 0, self.EPAISSEUR + 2,
                                         10, 3, fill=BORDURE, outline="")

        self.canevas.bind("<Configure>", lambda _e: self._dessiner())
        self.canevas.bind("<Button-1>", self._attraper)
        self.canevas.bind("<B1-Motion>", self._trainer)
        self.canevas.bind("<ButtonRelease-1>", self._lacher)
        self.canevas.bind("<Enter>",
                          lambda _e: self.canevas.itemconfigure(self.curseur,
                                                                fill=TEXTE_ETEINT))
        self.canevas.bind("<Leave>",
                          lambda _e: self.canevas.itemconfigure(self.curseur,
                                                                fill=BORDURE))

    # -- suivi de la vue ----------------------------------------------------

    def set(self, debut, fin) -> None:
        """Appelee par la toile a chaque deplacement."""
        self.debut, self.fin = float(debut), float(fin)
        self._dessiner()

    def utile(self) -> bool:
        """Y a-t-il seulement quelque chose a faire defiler ?"""
        return (self.fin - self.debut) < 0.999

    def _hauteur(self) -> int:
        try:
            return max(1, self.canevas.winfo_height())
        except tk.TclError:
            return 1

    def _dessiner(self) -> None:
        hauteur = self._hauteur()
        haut = int(self.debut * hauteur)
        bas = max(haut + 24, int(self.fin * hauteur))
        self.canevas.coords(self.curseur, 2, haut, self.EPAISSEUR + 2, bas)
        self.canevas.itemconfigure(self.curseur,
                                   state="normal" if self.utile() else "hidden")

    # -- souris -------------------------------------------------------------

    def _position(self, evenement) -> float:
        return max(0.0, min(1.0, evenement.y / self._hauteur()))

    def _attraper(self, evenement) -> None:
        self.saisie = self._position(evenement) - self.debut
        self._trainer(evenement)

    def _trainer(self, evenement) -> None:
        if self.saisie is None:
            return
        self.commande("moveto", max(0.0, self._position(evenement) - self.saisie))

    def _lacher(self, _evenement) -> None:
        self.saisie = None

    def pack(self, **options):
        self.canevas.pack(**options)
        return self


class Defilement:
    """Une zone qui defile — ce que tkinter ne sait pas faire tout seul.

    Une fenetre plus petite que son contenu doit rester utilisable : sans
    cela, la moitie des reglages est inaccessible sur un petit ecran, ou des
    que Windows agrandit les polices. Le contenu prend toujours la largeur
    disponible, ce qui laisse les textes se replier proprement.
    """

    def __init__(self, parent, fond: str = FOND):
        self.exterieur = tk.Frame(parent, bg=fond)

        self.toile = tk.Canvas(self.exterieur, bg=fond, highlightthickness=0)
        self.barre = BarreDefilement(self.exterieur, self._defiler, fond)
        self.toile.configure(yscrollcommand=self.barre.set)

        self.barre.pack(side="right", fill="y")
        self.toile.pack(side="left", fill="both", expand=True)

        self.interieur = tk.Frame(self.toile, bg=fond)
        self.fenetre = self.toile.create_window((0, 0), window=self.interieur,
                                                anchor="nw")

        self.interieur.bind("<Configure>", self._contenu_a_change)
        self.toile.bind("<Configure>", self._zone_a_change)
        # La molette n'agit que sur la zone survolee : deux zones qui defilent
        # en meme temps sont plus desagreables qu'aucune.
        self.toile.bind("<Enter>", self._ecouter_molette)
        self.toile.bind("<Leave>", self._oublier_molette)

    def _defiler(self, *arguments) -> None:
        self.toile.yview(*arguments)

    def _contenu_a_change(self, _evenement) -> None:
        self.toile.configure(scrollregion=self.toile.bbox("all"))

    def _zone_a_change(self, evenement) -> None:
        # Le contenu epouse la largeur : c'est ce qui rend les textes
        # repliables et la fenetre redimensionnable.
        self.toile.itemconfigure(self.fenetre, width=evenement.width)

    def _ecouter_molette(self, _evenement) -> None:
        self.toile.bind_all("<MouseWheel>", self._molette)
        self.toile.bind_all("<Button-4>", self._molette)
        self.toile.bind_all("<Button-5>", self._molette)

    def _oublier_molette(self, _evenement) -> None:
        for evenement in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.toile.unbind_all(evenement)

    def _molette(self, evenement) -> None:
        if not self.barre.utile():
            return
        # Windows envoie un « delta » de 120 par cran ; X11, deux boutons.
        if getattr(evenement, "num", None) == 4:
            crans = -1
        elif getattr(evenement, "num", None) == 5:
            crans = 1
        else:
            crans = -int(getattr(evenement, "delta", 0) / 120) or 0
        if crans:
            self.toile.yview_scroll(crans, "units")

    def pack(self, **options):
        self.exterieur.pack(**options)
        return self


class Colonnes:
    """Deux panneaux cote a cote, empiles des que la fenetre se retrecit.

    C'est tout ce que veut dire « responsive » ici : en dessous d'un certain
    nombre de pixels, deux colonnes de trois centimetres ne servent plus a
    personne.
    """

    SEUIL = 720

    def __init__(self, parent, fond: str = FOND, seuil: int | None = None):
        self.cadre = tk.Frame(parent, bg=fond)
        self.panneaux: list[tk.Frame] = []
        self.seuil = seuil if seuil is not None else self.SEUIL
        self.cote_a_cote: bool | None = None
        self.cadre.bind("<Configure>", self._sur_mesure)

    def ajouter(self) -> tk.Frame:
        panneau = tk.Frame(self.cadre, bg=self.cadre.cget("bg"))
        self.panneaux.append(panneau)
        return panneau

    def disposer(self, cote_a_cote: bool) -> None:
        if cote_a_cote == self.cote_a_cote:
            return
        self.cote_a_cote = cote_a_cote
        for indice, panneau in enumerate(self.panneaux):
            panneau.pack_forget()
            if cote_a_cote:
                panneau.pack(side="left", fill="both", expand=True,
                             padx=(0, MOYEN) if indice == 0 else (MOYEN, 0))
            else:
                panneau.pack(side="top", fill="both", expand=True,
                             pady=(0, MOYEN) if indice == 0 else (MOYEN, 0))

    def _sur_mesure(self, evenement) -> None:
        self.disposer(evenement.width >= self.seuil)

    def pack(self, **options):
        self.cadre.pack(**options)
        self.disposer(True)
        return self


class Segments:
    """Un choix entre deux ou trois options, d'un seul tenant.

    Remplace les boutons radio de tkinter, qui portent l'apparence de Windows
    et jurent au milieu de widgets dessines.
    """

    HAUTEUR = 32

    def __init__(self, parent, options: list[tuple[str, str]], valeur: str,
                 commande=None, fond: str = SURFACE):
        self.options = options
        self.valeur = valeur
        self.commande = commande
        self.boutons: dict[str, Bouton] = {}

        self.cadre = tk.Frame(parent, bg=fond)
        for cle, libelle in options:
            bouton = Bouton(self.cadre, libelle,
                            lambda c=cle: self.choisir(c), fond=fond)
            bouton.pack(side="left", padx=(0, PETIT))
            self.boutons[cle] = bouton
        self._peindre()

    def _peindre(self) -> None:
        for cle, bouton in self.boutons.items():
            choisi = cle == self.valeur
            bouton.repos = ACCENT if choisi else SURFACE_HAUTE
            bouton.survol = ACCENT_VIF if choisi else BORDURE
            bouton.couleur_texte = "white" if choisi else TEXTE_DOUX
            bouton.canevas.itemconfigure(bouton.forme, fill=bouton.repos)
            bouton.canevas.itemconfigure(bouton.etiquette,
                                         fill=bouton.couleur_texte)

    def choisir(self, cle: str) -> None:
        self.valeur = cle
        self._peindre()
        if self.commande is not None:
            self.commande(cle)

    def get(self) -> str:
        return self.valeur

    def set(self, valeur: str) -> None:
        self.valeur = valeur
        self._peindre()

    def pack(self, **options):
        self.cadre.pack(**options)
        return self
