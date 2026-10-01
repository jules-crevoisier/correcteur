# -*- coding: utf-8 -*-
"""La bulle de propositions, posee toujours au meme endroit.

Elle montre ce que Papote propose pour le mot en cours : les suites
probables quand on ecrit, les remplacements possibles quand le mot est
inconnu. La touche de validation prend la premiere.

    ●  bonj  →  ╭ bonjour  [Tab] ╮   bonjours · bonjourner

La premiere proposition est une pastille de la couleur de Papote, avec la
touche qui la prend dessinee comme une touche ; les autres suivent, plus
discretes. Sous Windows 11, la fenetre a les coins arrondis et l'ombre des
menus du systeme ; elle suit le theme clair ou sombre choisi dans Windows,
et apparait en fondu plutot que d'un coup.

**Pourquoi un coin fixe, et non au-dessus du mot.** Suivre le curseur
suppose de savoir ou il est a l'ecran. Windows le dit pour les applications
natives — `GetGUIThreadInfo` rend la position du caret — mais pas pour ce
qui est construit sur Chromium : Discord, Slack, les navigateurs, les
editeurs de code. Or c'est la qu'on ecrit. Une bulle qui saute au bon
endroit une fois sur trois est pire qu'une bulle qui ne bouge jamais : on
apprend a regarder un coin, on n'apprend pas a chercher.

**Pourquoi tkinter, alors que la fenetre est en HTML.** Cette bulle
apparait et disparait a chaque mot. Demarrer un moteur de rendu pour cela
couterait des centaines de millisecondes et de la memoire en permanence ;
tkinter ouvre une fenetre sans bordure en quelques millisecondes. Les
formes arrondies sont dessinees par Pillow, lissees, et posees sur un
canevas ; le texte reste celui de Windows, net a toutes les tailles.

**Fil a part.** tkinter exige que tout se passe sur le fil qui a cree sa
racine, et l'icone de la zone de notification occupe deja le fil principal.
La bulle vit donc dans son propre fil, et on lui parle par une file
d'attente qu'elle vide elle-meme. Aucune methode publique d'ici ne touche a
tkinter directement.

**Jamais le focus.** La bulle ne doit pas prendre la main a l'application
ou l'on ecrit : sous Windows, elle porte le style « ne s'active pas ».

Enfin, tout echoue en silence. Une bulle qui ne s'affiche pas est un
agrement en moins ; une exception qui remonte emporterait le clavier.
"""

from __future__ import annotations

import base64
import io
import os
import queue
import threading
import time
from dataclasses import dataclass

from . import couleurs

# Distance aux bords de l'ecran, en pixels. La barre des taches fait une
# quarantaine de pixels : on se pose au-dessus.
MARGE_DROITE = 24
MARGE_BAS = 64

# Au-dela, la bulle devient un panneau. Trois propositions et un mot, pas
# davantage.
PROPOSITIONS_MAXIMUM = 3

# Temps d'affichage maximal sans rien recevoir de neuf. Une bulle oubliee a
# l'ecran est une bulle qui ment.
DUREE_MAXIMALE = 6.0

# L'opacite finale, et les paliers du fondu (un toutes les 16 ms).
OPACITE = 0.98
FONDU = (0.35, 0.65, 0.88, OPACITE)


# ---------------------------------------------------------------------------
# Le theme
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Palette:
    fond: str
    bordure: str
    texte: str
    doux: str
    eteint: str
    pastille: str          # la premiere proposition
    sur_pastille: str      # son texte
    touche: str            # le fond de la touche dessinee sur la pastille
    point: str             # le point de Papote, a gauche


SOMBRE = Palette(
    fond=couleurs.SURFACE, bordure=couleurs.BORDURE, texte=couleurs.TEXTE,
    doux=couleurs.TEXTE_DOUX, eteint=couleurs.TEXTE_ETEINT,
    # Un bleu plus profond que l'accent : le blanc s'y lit (contraste AA).
    pastille="#3d6ef5", sur_pastille="#ffffff", touche="#6a91f8",
    point=couleurs.ACCENT_VIF,
)
CLAIR = Palette(
    fond=couleurs.PAGE, bordure=couleurs.BORDURE_CLAIRE, texte=couleurs.ENCRE,
    doux=couleurs.ENCRE_DOUCE, eteint="#8a92a6",
    pastille="#2f62e9", sur_pastille="#ffffff", touche="#5d86ee",
    point=couleurs.ACCENT,
)


def theme_windows() -> str:
    """« clair » ou « sombre », comme les applications de Windows."""
    if os.name != "nt":
        return "sombre"
    try:
        import winreg

        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as cle:
            valeur, _type = winreg.QueryValueEx(cle, "AppsUseLightTheme")
        return "clair" if valeur else "sombre"
    except OSError:
        return "sombre"


def palette(theme: str | None = None) -> Palette:
    return CLAIR if (theme or theme_windows()) == "clair" else SOMBRE


# ---------------------------------------------------------------------------
# La mise en page, sans tkinter
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Mesures:
    """Les dimensions de base, en pixels a 96 points par pouce."""
    marge: int = 12            # bords de la bulle
    point: int = 7             # diametre du point de Papote
    ecart: int = 10            # entre deux elements
    pastille_h: int = 28       # hauteur de la pastille
    pastille_marge: int = 10   # de part et d'autre du mot, dans la pastille
    touche_h: int = 18
    touche_marge: int = 6
    rayon: int = 8
    hauteur: int = 44


@dataclass(frozen=True)
class Element:
    genre: str                 # « point », « mot », « fleche », « pastille »,
    x: int                     # « choix », « touche », « touche_texte »,
    largeur: int               # « autre », « separateur »
    texte: str = ""


def disposer(mot: str, propositions: list[str], touche: str, mesurer,
             m: Mesures = Mesures()) -> tuple[list[Element], int]:
    """Place chaque element de gauche a droite ; rend aussi la largeur totale.

    `mesurer(texte, style)` rend la largeur d'un texte dans l'un des styles
    « mot », « choix », « touche », « autre ». C'est la seule chose qu'on
    demande a tkinter, ce qui permet de tester la mise en page sans ecran.
    """
    premiere, *autres = propositions
    elements: list[Element] = []
    x = m.marge
    elements.append(Element("point", x, m.point))
    x += m.point + m.ecart

    if mot:
        largeur = mesurer(mot, "mot")
        elements.append(Element("mot", x, largeur, mot))
        x += largeur + m.ecart - 2
        largeur = mesurer("→", "mot")
        elements.append(Element("fleche", x, largeur, "→"))
        x += largeur + m.ecart - 2

    choix = mesurer(premiere, "choix")
    texte_touche = mesurer(touche, "touche")
    largeur_touche = texte_touche + 2 * m.touche_marge
    largeur_pastille = (m.pastille_marge + choix + 8 + largeur_touche
                        + (m.pastille_h - m.touche_h) // 2)
    elements.append(Element("pastille", x, largeur_pastille))
    elements.append(Element("choix", x + m.pastille_marge, choix, premiere))
    debut_touche = x + m.pastille_marge + choix + 8
    elements.append(Element("touche", debut_touche, largeur_touche))
    elements.append(Element("touche_texte", debut_touche + m.touche_marge,
                            texte_touche, touche))
    x += largeur_pastille

    for k, autre in enumerate(autres):
        x += m.ecart + (2 if k == 0 else 0)
        if k:
            largeur = mesurer("·", "autre")
            elements.append(Element("separateur", x, largeur, "·"))
            x += largeur + m.ecart
        largeur = mesurer(autre, "autre")
        elements.append(Element("autre", x, largeur, autre))
        x += largeur
    return elements, x + m.marge + 2


# ---------------------------------------------------------------------------
# Les formes lissees
# ---------------------------------------------------------------------------

_FORMES: dict = {}


def _forme(largeur: int, hauteur: int, rayon: int, couleur: str,
           fond: str, bordure: str | None = None):
    """Un rectangle arrondi lisse, en PNG, pret pour `tk.PhotoImage(data=)`.

    Dessine quatre fois plus grand, puis reduit : c'est ce qui lisse les
    courbes. Le fond est opaque — la couleur de la bulle —, ce qui evite
    toute frange autour des angles.
    """
    cle = (largeur, hauteur, rayon, couleur, fond, bordure)
    if cle in _FORMES:
        return _FORMES[cle]
    from PIL import Image, ImageDraw

    f = 4
    image = Image.new("RGB", (largeur * f, hauteur * f), fond)
    dessin = ImageDraw.Draw(image)
    boite = (0, 0, largeur * f - 1, hauteur * f - 1)
    if bordure:
        dessin.rounded_rectangle(boite, radius=rayon * f, fill=bordure)
        boite = (f, f, largeur * f - 1 - f, hauteur * f - 1 - f)
        dessin.rounded_rectangle(boite, radius=(rayon - 1) * f, fill=couleur)
    else:
        dessin.rounded_rectangle(boite, radius=rayon * f, fill=couleur)
    image = image.resize((largeur, hauteur), Image.LANCZOS)
    tampon = io.BytesIO()
    image.save(tampon, format="PNG")
    donnees = base64.b64encode(tampon.getvalue())
    if len(_FORMES) > 64:
        _FORMES.clear()
    _FORMES[cle] = donnees
    return donnees


# ---------------------------------------------------------------------------
# Windows : coins ronds, ombre, et jamais le focus
# ---------------------------------------------------------------------------

def _habiller_pour_windows(racine) -> bool:
    """Rend vrai si Windows arrondit lui-meme les coins (Windows 11)."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        racine.update_idletasks()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        fenetre = user32.GetParent(racine.winfo_id()) or racine.winfo_id()

        # Ne jamais s'activer, ne jamais voler la frappe.
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        style = user32.GetWindowLongW(fenetre, GWL_EXSTYLE)
        user32.SetWindowLongW(fenetre, GWL_EXSTYLE,
                              style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)

        # Coins arrondis et ombre des menus de Windows 11. Ailleurs, l'appel
        # echoue sans bruit et la bulle garde sa bordure d'un pixel.
        dwm = ctypes.WinDLL("dwmapi")
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        preference = ctypes.c_int(DWMWCP_ROUND)
        resultat = dwm.DwmSetWindowAttribute(
            wintypes.HWND(fenetre), DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference), ctypes.sizeof(preference))
        return resultat == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# La bulle
# ---------------------------------------------------------------------------

class Bulle:
    """Une petite fenetre sans bordure, toujours au-dessus des autres.

    Trois methodes, toutes appelables depuis n'importe quel fil :

        montrer(mot, propositions, touche)
        cacher()
        fermer()
    """

    def __init__(self, position: str = "bas-droite", theme: str | None = None):
        self.position = position
        self._theme = theme
        self._file: queue.Queue = queue.Queue()
        self._fil: threading.Thread | None = None
        self._racine = None
        self._vivante = False
        self._echouee = False
        self._images: list = []

    # -- ce que le reste de Papote appelle -----------------------------------

    def montrer(self, mot: str, propositions: list[str],
                touche: str = "Tab") -> None:
        if not propositions or self._echouee:
            return
        self._demarrer()
        self._file.put(("montrer", (mot, propositions[:PROPOSITIONS_MAXIMUM],
                                    touche)))

    def cacher(self) -> None:
        if self._fil is None:
            return
        self._file.put(("cacher", None))

    def fermer(self) -> None:
        if self._fil is None:
            return
        self._file.put(("fermer", None))
        self._fil = None

    @property
    def visible(self) -> bool:
        return self._vivante

    # -- le fil qui tient la fenetre -----------------------------------------

    def _demarrer(self) -> None:
        if self._fil is not None and self._fil.is_alive():
            return
        self._fil = threading.Thread(target=self._vivre, daemon=True)
        self._fil.start()

    def _vivre(self) -> None:
        try:
            self._construire()
            self._racine.mainloop()
        except Exception:
            # Pas d'ecran, pas de tkinter, un pilote graphique fache : la
            # prediction se passe de bulle, le reste continue.
            self._echouee = True
        finally:
            self._racine = None
            self._vivante = False

    def _construire(self) -> None:
        import tkinter as tk
        from tkinter import font as tkfont

        self._palette = palette(self._theme)
        p = self._palette
        racine = tk.Tk()
        racine.withdraw()
        racine.overrideredirect(True)       # ni bordure ni barre de titre
        racine.attributes("-topmost", True)
        try:
            racine.attributes("-toolwindow", True)   # pas dans Alt+Tab
        except Exception:
            pass
        racine.configure(bg=p.fond)

        # Les pixels suivent la mise a l'echelle de Windows (125 %, 150 %…).
        self._echelle = max(1.0, racine.winfo_fpixels("1i") / 96.0)
        e = self._echelle
        self._m = Mesures(**{k: round(v * e) for k, v in Mesures().__dict__.items()})

        famille = couleurs.FAMILLE
        self._polices = {
            "mot": tkfont.Font(root=racine, family=famille, size=10),
            "choix": tkfont.Font(root=racine, family=famille, size=11, weight="bold"),
            "touche": tkfont.Font(root=racine, family=famille, size=8, weight="bold"),
            "autre": tkfont.Font(root=racine, family=famille, size=10),
        }
        self._canevas = tk.Canvas(racine, bg=p.fond, highlightthickness=0, bd=0)
        self._canevas.pack(fill="both", expand=True)
        self._racine = racine
        self._coins_systeme = _habiller_pour_windows(racine)
        racine.after(40, self._vider_la_file)

    def _vider_la_file(self) -> None:
        """Consomme les ordres recus des autres fils.

        tkinter n'accepte d'ordres que du fil qui l'a cree ; c'est donc ici,
        et seulement ici, qu'on touche a la fenetre.
        """
        recu = False
        try:
            while True:
                try:
                    ordre, charge = self._file.get_nowait()
                except queue.Empty:
                    break
                recu = True
                if ordre == "montrer":
                    self._afficher(*charge)
                elif ordre == "cacher":
                    self._effacer()
                elif ordre == "fermer":
                    self._racine.quit()
                    return
        except Exception:
            self._echouee = True
        finally:
            if self._racine is not None:
                # Vingt-cinq reveils par seconde pendant qu'on tape, pour que
                # la bulle suive les doigts ; six quand rien ne se passe, pour
                # ne pas tenir le processeur eveille toute la journee.
                maintenant = time.monotonic()
                if recu:
                    self._dernier_ordre = maintenant
                actif = maintenant - getattr(self, "_dernier_ordre", 0.0) < 2.0
                self._racine.after(40 if actif else 160, self._vider_la_file)

    def _dessiner(self, mot: str, propositions: list[str], touche: str) -> tuple[int, int]:
        import tkinter as tk

        p, m, c = self._palette, self._m, self._canevas
        elements, largeur = disposer(
            mot, propositions, touche,
            lambda texte, style: self._polices[style].measure(texte), m)
        hauteur = m.hauteur
        milieu = hauteur // 2
        c.delete("all")
        self._images = []
        c.configure(width=largeur, height=hauteur)

        if not self._coins_systeme:
            # Sans les coins de Windows 11, la bulle dessine les siens : le
            # fond est alors celui du bureau, qu'on ne connait pas — une
            # bordure franche fait mieux qu'une frange.
            c.create_rectangle(0, 0, largeur - 1, hauteur - 1,
                               outline=p.bordure, fill=p.fond)

        for el in elements:
            if el.genre == "point":
                r = m.point
                c.create_oval(el.x, milieu - r // 2, el.x + r, milieu - r // 2 + r,
                              fill=p.point, outline="")
            elif el.genre == "mot":
                c.create_text(el.x, milieu, text=el.texte, anchor="w",
                              fill=p.doux, font=self._polices["mot"])
            elif el.genre in ("fleche", "separateur"):
                c.create_text(el.x, milieu, text=el.texte, anchor="w",
                              fill=p.eteint, font=self._polices["mot"])
            elif el.genre == "pastille":
                image = tk.PhotoImage(master=self._racine, data=_forme(
                    el.largeur, m.pastille_h, m.rayon, p.pastille, p.fond))
                self._images.append(image)
                c.create_image(el.x, milieu, image=image, anchor="w")
            elif el.genre == "choix":
                c.create_text(el.x, milieu, text=el.texte, anchor="w",
                              fill=p.sur_pastille, font=self._polices["choix"])
            elif el.genre == "touche":
                image = tk.PhotoImage(master=self._racine, data=_forme(
                    el.largeur, m.touche_h, max(3, m.rayon // 2), p.touche,
                    p.pastille))
                self._images.append(image)
                c.create_image(el.x, milieu, image=image, anchor="w")
            elif el.genre == "touche_texte":
                c.create_text(el.x, milieu, text=el.texte, anchor="w",
                              fill=p.sur_pastille, font=self._polices["touche"])
            elif el.genre == "autre":
                c.create_text(el.x, milieu, text=el.texte, anchor="w",
                              fill=p.texte, font=self._polices["autre"])
        return largeur, hauteur

    def _afficher(self, mot: str, propositions: list[str],
                  touche: str) -> None:
        largeur, hauteur = self._dessiner(mot, propositions, touche)
        x, y = self._coin(largeur, hauteur)
        self._racine.geometry(f"{largeur}x{hauteur}+{x}+{y}")
        if not self._vivante:
            # Elle apparait en fondu ; ensuite, elle change sur place.
            self._fondre(0)
            self._racine.deiconify()
        self._racine.lift()
        self._vivante = True

    def _fondre(self, palier: int) -> None:
        try:
            self._racine.attributes("-alpha", FONDU[palier])
        except Exception:
            return
        if palier + 1 < len(FONDU):
            self._racine.after(16, self._fondre, palier + 1)

    def _effacer(self) -> None:
        if self._racine is not None:
            self._racine.withdraw()
        self._vivante = False

    def _coin(self, largeur: int, hauteur: int) -> tuple[int, int]:
        """Ou poser la bulle, selon le coin choisi."""
        ecran_l = self._racine.winfo_screenwidth()
        ecran_h = self._racine.winfo_screenheight()
        e = getattr(self, "_echelle", 1.0)
        droite, bas = round(MARGE_DROITE * e), round(MARGE_BAS * e)
        coins = {
            "bas-droite": (ecran_l - largeur - droite, ecran_h - hauteur - bas),
            "bas-gauche": (droite, ecran_h - hauteur - bas),
            "haut-droite": (ecran_l - largeur - droite, droite),
            "haut-gauche": (droite, droite),
        }
        return coins.get(self.position, coins["bas-droite"])


class BulleMuette:
    """Une bulle qui ne fait rien, pour quand la prediction est eteinte.

    Distribuer un objet inerte plutot que `None` evite au reste du code de
    verifier a chaque appel s'il a une bulle.
    """

    visible = False

    def montrer(self, *_args, **_options) -> None:
        pass

    def cacher(self) -> None:
        pass

    def fermer(self) -> None:
        pass
