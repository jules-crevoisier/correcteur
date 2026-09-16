# -*- coding: utf-8 -*-
"""Un tkinter de substitution, assez fidele pour eprouver la fenetre.

L'environnement de developpement n'a ni tkinter ni ecran. Ce module en imite
la partie que Papote utilise — et seulement celle-la : tout appel a une
methode qui n'existe pas ici leve, comme il le ferait sur un vrai widget mal
employe. C'est ce qui rend le test utile : il attrape les fautes de frappe,
les attributs oublies et les signatures fausses, qui sont exactement les
erreurs qu'on ne voit pas sans ecran.
"""

from __future__ import annotations

import sys
import types


class Widget:
    """Le socle commun : des options, des enfants, des liaisons."""

    def __init__(self, parent=None, **options):
        self.parent = parent
        self.options = dict(options)
        self.enfants: list[Widget] = []
        self.liaisons: dict[str, object] = {}
        self.visible = False
        if isinstance(parent, Widget):
            parent.enfants.append(self)

    # -- placement
    def pack(self, **_options): self.visible = True
    def grid(self, **_options): self.visible = True
    def pack_forget(self): self.visible = False
    def pack_propagate(self, _valeur): pass
    def grid_propagate(self, _valeur): pass

    # -- arbre
    def winfo_children(self): return list(self.enfants)

    def destroy(self):
        if isinstance(self.parent, Widget) and self in self.parent.enfants:
            self.parent.enfants.remove(self)
        self.enfants.clear()

    # -- options et evenements
    def configure(self, **options): self.options.update(options)
    config = configure

    def cget(self, cle): return self.options.get(cle)
    def bind(self, evenement, fonction, *_a): self.liaisons[evenement] = fonction
    def unbind(self, evenement, *_a): self.liaisons.pop(evenement, None)
    def focus_set(self): pass
    def grab_set(self): pass
    def grab_release(self): pass

    def declencher(self, evenement, donnees=None):
        """Simule un evenement : c'est ainsi que les tests cliquent."""
        fonction = self.liaisons.get(evenement)
        if fonction is not None:
            return fonction(donnees)
        return None


class Frame(Widget): pass
class Label(Widget): pass
class Radiobutton(Widget): pass
class Checkbutton(Widget): pass
class Scrollbar(Widget): pass


class Entry(Widget):
    def __init__(self, parent=None, **options):
        super().__init__(parent, **options)
        self.contenu = ""

    def get(self): return self.contenu
    def insert(self, _indice, texte): self.contenu += texte

    def delete(self, _debut, _fin=None): self.contenu = ""


class Listbox(Widget):
    def __init__(self, parent=None, **options):
        super().__init__(parent, **options)
        self.lignes: list[str] = []
        self.selection: tuple[int, ...] = ()

    def insert(self, _position, texte): self.lignes.append(texte)

    def delete(self, debut, fin=None):
        if debut == 0 and fin == "end":
            self.lignes.clear()

    def get(self, indice): return self.lignes[indice]
    def curselection(self): return self.selection
    def choisir(self, indice): self.selection = (indice,)


class Text(Widget):
    def __init__(self, parent=None, **options):
        super().__init__(parent, **options)
        self.contenu = ""

    def insert(self, _position, texte): self.contenu += texte

    def delete(self, _debut, _fin=None): self.contenu = ""

    def get(self, _debut, _fin=None): return self.contenu


class Canvas(Widget):
    def __init__(self, parent=None, **options):
        super().__init__(parent, **options)
        self.objets: dict[int, dict] = {}
        self._compteur = 0

    def _ajouter(self, genre, **options):
        self._compteur += 1
        self.objets[self._compteur] = {"genre": genre, **options}
        return self._compteur

    def create_polygon(self, *_points, **options):
        return self._ajouter("polygone", **options)

    def create_text(self, *_position, **options):
        return self._ajouter("texte", **options)

    def create_image(self, *_position, **options):
        return self._ajouter("image", **options)

    def create_oval(self, *_position, **options):
        return self._ajouter("ovale", **options)

    def create_window(self, *_position, **options):
        return self._ajouter("fenetre", **options)

    def itemconfigure(self, identifiant, **options):
        self.objets[identifiant].update(options)
    itemconfig = itemconfigure

    def coords(self, _identifiant, *_valeurs): pass
    def bbox(self, *_a): return (0, 0, 10, 10)
    def yview(self, *_a): pass


class PhotoImage:
    def __init__(self, width=0, height=0, **_options):
        self.largeur, self.hauteur = width, height
        self.lignes: list[str] = []

    def put(self, donnees, to=None): self.lignes.append(donnees)

    def zoom(self, facteur):
        agrandie = PhotoImage(self.largeur * facteur, self.hauteur * facteur)
        agrandie.lignes = list(self.lignes)
        return agrandie


class Variable:
    def __init__(self, value=None, **_options): self.valeur = value
    def get(self): return self.valeur
    def set(self, valeur): self.valeur = valeur


class BooleanVar(Variable):
    def __init__(self, value=False, **options): super().__init__(bool(value), **options)
    def get(self): return bool(self.valeur)


class StringVar(Variable):
    def __init__(self, value="", **options): super().__init__(value, **options)


class Tk(Widget):
    def __init__(self, **options):
        super().__init__(None, **options)
        self.titre = ""
        self.presse_papiers = ""
        self.differes: list = []

    def title(self, texte): self.titre = texte
    def geometry(self, _valeur): pass
    def minsize(self, *_valeurs): pass
    def mainloop(self): pass
    def clipboard_clear(self): self.presse_papiers = ""
    def clipboard_append(self, texte): self.presse_papiers += texte

    def after(self, _delai, fonction=None, *arguments):
        """Les taches differees s'executent tout de suite : les tests attendent."""
        if fonction is not None:
            self.differes.append((fonction, arguments))
            fonction(*arguments)


class TclError(Exception):
    pass


class _Police:
    def __init__(self, **_options): pass
    def measure(self, texte): return len(texte) * 7


def installer():
    """Met le faux tkinter a la place du vrai, avant tout import de la fenetre."""
    module = types.ModuleType("tkinter")
    for nom, valeur in globals().items():
        if nom[0].isupper() or nom == "TclError":
            setattr(module, nom, valeur)
    module.TclError = TclError

    police = types.ModuleType("tkinter.font")
    police.Font = _Police

    sys.modules["tkinter"] = module
    sys.modules["tkinter.font"] = police
    module.font = police
    return module
