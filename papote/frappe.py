# -*- coding: utf-8 -*-
"""Correction au fil de la frappe.

Le raccourci oblige a s'interrompre : selectionner, appuyer, verifier. Ce
module supprime cette etape — le texte se corrige tout seul pendant qu'on
ecrit, comme sur un telephone.

Le principe est simple : on retient la phrase en cours de frappe, et chaque
fois qu'un mot se termine — une espace, une virgule, un point — on soumet la
phrase au correcteur. S'il propose autre chose, on efface ce qu'il faut et on
reecrit. « sa » ne devient « ça » qu'une fois « va » tape : c'est la phrase
qui tranche, pas le mot.

Tout est dans le fait de savoir exactement ce qui est a l'ecran. Le module
s'y tient par une regle unique : **au moindre doute, on oublie la phrase**.
Une touche inconnue, un accent mort, un deplacement du curseur, un silence
un peu long, et le tampon repart de zero. Une correction manquee ne se voit
pas ; une correction appliquee au mauvais endroit detruit le texte.

`Frappe` ne connait ni le clavier ni le systeme : elle recoit des caracteres
et rend des remplacements, ce qui la rend entierement testable.
`EcouteClavier` fait le reste.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

# Un mot se termine sur l'un de ces caracteres. Ni l'apostrophe ni le trait
# d'union n'y figurent : « j'ai » et « est-ce » sont des mots entiers.
SEPARATEURS = " \t\n.,;:!?…\"()[]{}«»/\\|"

# Apres l'un de ceux-la, la phrase est finie : on repart a zero.
FINS_DE_PHRASE = ".!?…\n"

# Touches qui deplacent le curseur : ce qui est a l'ecran nous echappe.
TOUCHES_DE_DEPLACEMENT = {
    "left", "right", "up", "down", "home", "end", "page up", "page down",
    "delete", "esc", "escape", "insert",
}

# Accents morts : « ^ » puis « e » affiche « ê ». Le clavier nous annonce
# deux touches la ou l'ecran montre un caractere ; on ne sait plus compter.
ACCENTS_MORTS = {"^", "¨", "`", "~", "dead"}

TOUCHES_SPECIALES = {
    "space": " ",
    "enter": "\n",
    "return": "\n",
    "tab": "\t",
}


@dataclass(frozen=True)
class Remplacement:
    """Ce qu'il faut taper a la place de ce qui vient d'etre ecrit."""

    effacer: int      # nombre de retours arriere
    ecrire: str       # texte a taper ensuite
    avant: str        # ce qui disparait, pour pouvoir le remettre

    @property
    def inverse(self) -> "Remplacement":
        """Le remplacement qui annule celui-ci."""
        return Remplacement(len(self.ecrire), self.avant, self.ecrire)

    def __str__(self) -> str:
        return f"{self.avant.strip()} → {self.ecrire.strip()}"


class Frappe:
    """Le texte en cours de frappe, et les corrections qu'il appelle.

    On lui donne les caracteres tapes ; elle rend un `Remplacement` quand une
    correction s'impose, et `None` le reste du temps.
    """

    def __init__(self, correcteur, longueur_max: int = 400,
                 effacement_max: int = 40):
        self.correcteur = correcteur
        self.longueur_max = longueur_max
        # Au-dela, la correction porte trop loin en arriere : la rafale de
        # retours arriere serait visible, et une desynchronisation couteuse.
        self.effacement_max = effacement_max
        self.texte = ""

    # -- ce qui arrive du clavier -------------------------------------------

    def oublier(self) -> None:
        """Repart de zero : on ne sait plus ce qu'il y a a l'ecran."""
        self.texte = ""

    def retour_arriere(self) -> None:
        if self.texte:
            self.texte = self.texte[:-1]
        else:
            # L'utilisateur efface du texte qu'on n'a pas vu passer.
            self.oublier()

    def caractere(self, caractere: str) -> Remplacement | None:
        """Enregistre un caractere tape. Renvoie la correction s'il en faut une."""
        if not caractere:
            return None

        if not self.texte and caractere in SEPARATEURS:
            # Une phrase ne commence pas par une espace : ne pas la retenir
            # evite de croire qu'on suit un texte qu'on ne suit pas.
            return None

        self.texte += caractere
        self._raccourcir()

        if caractere not in SEPARATEURS:
            return None

        remplacement = self._examiner(caractere)

        if caractere in FINS_DE_PHRASE:
            # La phrase est close : la suivante n'a pas besoin de son contexte,
            # et un tampon qui ne grandit pas est un tampon qui ne derive pas.
            self.oublier()

        return remplacement

    # -- decision -----------------------------------------------------------

    def _raccourcir(self) -> None:
        """Ne garde que la fin du texte, coupee proprement entre deux mots."""
        if len(self.texte) <= self.longueur_max:
            return
        reste = self.texte[-self.longueur_max:]
        for i, caractere in enumerate(reste):
            if caractere in SEPARATEURS:
                self.texte = reste[i + 1:]
                return
        self.texte = reste

    def _examiner(self, separateur: str) -> Remplacement | None:
        corps = self.texte[:-1]
        if not corps.strip():
            return None

        # Pas de majuscule ni de point final : la phrase n'est pas finie.
        corrige, corrections = self.correcteur.corriger(corps, mise_en_forme=False)
        if corrige == corps or not corrections:
            return None

        commun = _prefixe_commun(corps, corrige)

        # On ne sait taper que par la fin : tout ce qui suit le premier
        # caractere different doit etre reecrit, separateur compris.
        efface = corps[commun:] + separateur
        ecrit = corrige[commun:] + separateur

        if len(efface) > self.effacement_max:
            return None
        if "\n" in efface:
            # Remonter au-dessus d'une ligne demande de savoir ou elle
            # commence, ce que les retours arriere ne garantissent pas.
            return None

        self.texte = corrige + separateur
        return Remplacement(len(efface), ecrit, efface)


def _prefixe_commun(gauche: str, droite: str) -> int:
    limite = min(len(gauche), len(droite))
    for i in range(limite):
        if gauche[i] != droite[i]:
            return i
    return limite


class EcouteClavier:
    """Branche `Frappe` sur le vrai clavier.

    Deux precautions gouvernent cette classe :

    - **Ne jamais s'ecouter soi-meme.** Taper un remplacement produit des
      evenements clavier ; les prendre pour de la frappe humaine ferait boucler
      l'ensemble. Un verrou les ecarte, et toute touche pressee pendant qu'on
      ecrit fait oublier la phrase : on ne sait plus dans quel ordre tout cela
      s'est pose a l'ecran.
    - **Ne rien retenir.** Le tampon vit en memoire, quelques centaines de
      caracteres au plus, et rien n'en sort : ni fichier, ni reseau. Il
      s'efface des que le doute s'installe.
    """

    def __init__(self, frappe: Frappe, delai_oubli: float = 5.0,
                 sur_correction: Callable[[Remplacement], None] | None = None,
                 profondeur_annulation: int = 20):
        self.frappe = frappe
        self.delai_oubli = delai_oubli
        self.sur_correction = sur_correction
        self.annulables: list[Remplacement] = []
        self.profondeur_annulation = profondeur_annulation

        self.actif = False
        self._en_ecriture = False
        self._touche_pendant_ecriture = False
        self._derniere_touche = 0.0
        self._branchement = None

    # -- cycle de vie -------------------------------------------------------

    def activer(self) -> None:
        import keyboard

        if self._branchement is not None:
            return
        self.frappe.oublier()
        self._branchement = keyboard.hook(self._sur_evenement)
        self.actif = True

    def desactiver(self) -> None:
        import keyboard

        self.actif = False
        self.frappe.oublier()
        if self._branchement is None:
            return
        try:
            keyboard.unhook(self._branchement)
        except (KeyError, ValueError):
            pass
        self._branchement = None

    # -- reception des touches ----------------------------------------------

    def _sur_evenement(self, evenement) -> None:
        if not self.actif:
            return

        if self._en_ecriture:
            # C'est nous qui tapons — ou l'utilisateur, par-dessus nous.
            self._touche_pendant_ecriture = True
            return

        if getattr(evenement, "event_type", None) != "down":
            return

        maintenant = time.monotonic()
        if maintenant - self._derniere_touche > self.delai_oubli:
            # Un silence : le curseur a pu aller ailleurs entre-temps.
            self.frappe.oublier()
        self._derniere_touche = maintenant

        caractere = self._traduire(evenement)
        if caractere is None:
            return

        try:
            remplacement = self.frappe.caractere(caractere)
        except Exception:
            # Une correction ratee ne doit jamais emporter le clavier.
            self.frappe.oublier()
            return

        if remplacement is not None:
            self._appliquer(remplacement)

    def _traduire(self, evenement) -> str | None:
        """Le caractere reellement tape, ou None s'il n'y a rien a retenir."""
        import keyboard

        nom = getattr(evenement, "name", None)
        if not nom:
            self.frappe.oublier()
            return None

        # Un raccourci est en cours : ce qui suit n'est pas de la frappe.
        # (AltGr se presente comme ctrl+alt : on prefere l'ecarter aussi.)
        if any(keyboard.is_pressed(touche) for touche in ("ctrl", "alt", "windows")):
            self.frappe.oublier()
            return None

        if nom == "backspace":
            self.frappe.retour_arriere()
            return None

        if nom in TOUCHES_DE_DEPLACEMENT:
            self.frappe.oublier()
            return None

        if nom in TOUCHES_SPECIALES:
            return TOUCHES_SPECIALES[nom]

        if nom in ACCENTS_MORTS:
            self.frappe.oublier()
            return None

        if len(nom) != 1:
            # Majuscule, fonction, verrouillage... : rien a ajouter au tampon.
            return None

        if keyboard.is_pressed("shift"):
            return nom.upper()
        return nom

    # -- ecriture -----------------------------------------------------------

    def _appliquer(self, remplacement: Remplacement) -> None:
        self.annulables.append(remplacement)
        del self.annulables[:-self.profondeur_annulation]
        if self.sur_correction is not None:
            self.sur_correction(remplacement)
        # Taper depuis le fil du crochet clavier le bloquerait : on passe la
        # main a un fil dedie.
        threading.Thread(target=self._taper, args=(remplacement,),
                         daemon=True).start()

    def _taper(self, remplacement: Remplacement) -> None:
        import keyboard

        self._touche_pendant_ecriture = False
        self._en_ecriture = True
        try:
            for _ in range(remplacement.effacer):
                keyboard.send("backspace")
            keyboard.write(remplacement.ecrire, delay=0)
        except Exception:
            self.frappe.oublier()
        finally:
            self._en_ecriture = False
            if self._touche_pendant_ecriture:
                # L'utilisateur a tape pendant qu'on ecrivait : impossible de
                # savoir ce que donne le melange.
                self.frappe.oublier()

    # -- annulation ---------------------------------------------------------

    def annuler(self) -> Remplacement | None:
        """Remet ce qui etait ecrit avant la derniere correction automatique."""
        if not self.annulables:
            return None
        remplacement = self.annulables.pop()
        self._taper(remplacement.inverse)
        # Le mot rétabli ne doit pas etre recorrige dans la foulee : on repart
        # de la phrase suivante.
        self.frappe.oublier()
        return remplacement
