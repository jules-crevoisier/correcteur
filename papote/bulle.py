# -*- coding: utf-8 -*-
"""La bulle de propositions, posee toujours au meme endroit.

Elle montre ce que Papote propose pour le mot en cours : les suites
probables quand on ecrit, les remplacements possibles quand le mot est
inconnu. La touche de validation prend la premiere.

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
tkinter ouvre une fenetre sans bordure en quelques millisecondes. Ce qu'il
ne sait pas faire — ombres, animations, typographie fine — n'a pas cours
ici : trois mots dans un rectangle.

**Fil a part.** tkinter exige que tout se passe sur le fil qui a cree sa
racine, et l'icone de la zone de notification occupe deja le fil principal.
La bulle vit donc dans son propre fil, et on lui parle par une file
d'attente qu'elle vide elle-meme. Aucune methode publique d'ici ne touche a
tkinter directement.

Enfin, tout echoue en silence. Une bulle qui ne s'affiche pas est un
agrement en moins ; une exception qui remonte emporterait le clavier.
"""

from __future__ import annotations

import queue
import threading

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


class Bulle:
    """Une petite fenetre sans bordure, toujours au-dessus des autres.

    Trois methodes, toutes appelables depuis n'importe quel fil :

        montrer(mot, propositions, touche)
        cacher()
        fermer()
    """

    def __init__(self, position: str = "bas-droite"):
        self.position = position
        self._file: queue.Queue = queue.Queue()
        self._fil: threading.Thread | None = None
        self._racine = None
        self._vivante = False
        self._echouee = False

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

        racine = tk.Tk()
        racine.withdraw()
        racine.overrideredirect(True)       # ni bordure ni barre de titre
        racine.attributes("-topmost", True)
        # La bulle ne doit jamais prendre le focus : le texte continue de
        # s'ecrire dans l'application ou l'on tape.
        try:
            racine.attributes("-alpha", 0.97)
            racine.attributes("-toolwindow", True)   # pas dans Alt+Tab
        except Exception:
            pass
        racine.configure(bg=couleurs.BORDURE)

        cadre = tk.Frame(racine, bg=couleurs.SURFACE, padx=14, pady=10)
        cadre.pack(padx=1, pady=1)

        self._mot = tk.Label(cadre, text="", bg=couleurs.SURFACE,
                             fg=couleurs.TEXTE_DOUX,
                             font=(couleurs.FAMILLE, 9))
        self._mot.pack(anchor="w")

        self._choix = tk.Label(cadre, text="", bg=couleurs.SURFACE,
                               fg=couleurs.TEXTE,
                               font=(couleurs.FAMILLE, 12, "bold"))
        self._choix.pack(anchor="w", pady=(2, 0))

        self._touche = tk.Label(cadre, text="", bg=couleurs.SURFACE,
                                fg=couleurs.TEXTE_ETEINT,
                                font=(couleurs.FAMILLE, 8))
        self._touche.pack(anchor="w", pady=(4, 0))

        self._racine = racine
        racine.after(40, self._vider_la_file)

    def _vider_la_file(self) -> None:
        """Consomme les ordres recus des autres fils.

        tkinter n'accepte d'ordres que du fil qui l'a cree ; c'est donc ici,
        et seulement ici, qu'on touche a la fenetre.
        """
        try:
            while True:
                try:
                    ordre, charge = self._file.get_nowait()
                except queue.Empty:
                    break
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
                self._racine.after(40, self._vider_la_file)

    def _afficher(self, mot: str, propositions: list[str],
                  touche: str) -> None:
        premiere, *autres = propositions
        self._mot.configure(text=f"{mot}…")
        self._choix.configure(text=premiere)
        reste = f"   ·   {'  '.join(autres)}" if autres else ""
        self._touche.configure(text=f"{touche} pour accepter{reste}")

        self._racine.update_idletasks()
        largeur = self._racine.winfo_reqwidth()
        hauteur = self._racine.winfo_reqheight()
        x, y = self._coin(largeur, hauteur)
        self._racine.geometry(f"{largeur}x{hauteur}+{x}+{y}")
        self._racine.deiconify()
        self._racine.lift()
        self._vivante = True

    def _effacer(self) -> None:
        if self._racine is not None:
            self._racine.withdraw()
        self._vivante = False

    def _coin(self, largeur: int, hauteur: int) -> tuple[int, int]:
        """Ou poser la bulle, selon le coin choisi."""
        ecran_l = self._racine.winfo_screenwidth()
        ecran_h = self._racine.winfo_screenheight()
        coins = {
            "bas-droite": (ecran_l - largeur - MARGE_DROITE,
                           ecran_h - hauteur - MARGE_BAS),
            "bas-gauche": (MARGE_DROITE, ecran_h - hauteur - MARGE_BAS),
            "haut-droite": (ecran_l - largeur - MARGE_DROITE, MARGE_DROITE),
            "haut-gauche": (MARGE_DROITE, MARGE_DROITE),
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
