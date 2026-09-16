# -*- coding: utf-8 -*-
"""Deviner le mot en cours de frappe, comme sur un clavier de telephone.

Le correcteur repare ce qui est ecrit ; celui-ci propose ce qui va l'etre.
Trois lettres suffisent souvent : « anni » n'a qu'une suite plausible,
« bonj » aussi.

Le principe tient en deux lignes. La liste de frequences est triee une fois
par ordre alphabetique ; un prefixe s'y retrouve alors par dichotomie, et
tous les mots qui commencent par lui sont contigus. On les classe par
frequence, on rend les trois premiers.

Ce que ce module ne fait **pas**, volontairement :

- il ne propose rien en dessous de trois lettres. Sur deux, les candidats se
  comptent par centaines et le premier n'est pas plus probable qu'un autre ;
- il ne propose pas le mot deja ecrit. Completer « bonjour » par
  « bonjour » n'aide personne ;
- il ne propose rien si le prefixe est deja un mot courant, sauf si la suite
  est franchement plus frequente. Quelqu'un qui a tape « par » voulait
  probablement « par », pas « parce ».

La prediction se trompe sans gravite — on peut toujours continuer a taper.
C'est ce qui la distingue de la correction, qui, elle, ne doit jamais se
tromper.
"""

from __future__ import annotations

import bisect
import unicodedata

# En dessous, le prefixe ne designe rien : « be » ouvre sur « bien »,
# « beaucoup », « besoin », « bec », et cent autres.
LONGUEUR_MINIMALE = 3

# Nombre de propositions rendues. Au-dela de trois, on ne lit plus, on
# cherche — et chercher coute plus cher que taper.
PROPOSITIONS = 3

# Si le prefixe est lui-meme un mot courant, la proposition doit etre bien
# plus frequente pour valoir la peine d'etre montree.
AVANTAGE_EXIGE = 3

# Au-dela de ce rang, le mot est trop rare pour etre propose a quelqu'un qui
# n'a tape que trois lettres.
RANG_MAXIMAL = 12_000


def _sans_accents(mot: str) -> str:
    """Pour que « evene » trouve « événement ».

    Personne ne tape les accents quand il est presse, et la prediction doit
    justement servir a ceux qui le sont.
    """
    decompose = unicodedata.normalize("NFD", mot)
    return "".join(c for c in decompose
                   if unicodedata.category(c) != "Mn").lower()


class Predicteur:
    """Les mots qui commencent comme celui qu'on est en train d'ecrire."""

    def __init__(self, lexique):
        self.lexique = lexique
        self._index: list[tuple[str, str]] | None = None

    @property
    def index(self) -> list[tuple[str, str]]:
        """Les mots courants, sans accents, tries — et leur vraie graphie.

        Construit a la premiere demande : quelqu'un qui n'emploie jamais la
        prediction ne paie pas ces quelques dixiemes de seconde.
        """
        if self._index is None:
            self._index = sorted(
                (_sans_accents(mot), mot)
                for mot, rang in self.lexique.rangs.items()
                if rang <= RANG_MAXIMAL and len(mot) > LONGUEUR_MINIMALE
                and mot[:1].islower() and _est_un_mot(mot)
            )
        return self._index

    def completer(self, prefixe: str, maximum: int = PROPOSITIONS) -> list[str]:
        """Les suites les plus probables de ce debut de mot."""
        if not prefixe or len(prefixe) < LONGUEUR_MINIMALE:
            return []

        nu = _sans_accents(prefixe)
        if not _est_un_mot(nu):
            return []

        index = self.index
        depart = bisect.bisect_left(index, (nu, ""))

        candidats = []
        for squelette, mot in index[depart:]:
            if not squelette.startswith(nu):
                break
            if squelette == nu and mot.lower() == prefixe.lower():
                # Le mot deja ecrit : rien a completer.
                continue
            candidats.append((self.lexique.rang(mot), mot))
            if len(candidats) > 200:
                # Un prefixe qui ouvre sur deux cents mots ne designe rien.
                break

        candidats.sort()
        retenus = [mot for _rang, mot in candidats[:maximum]]
        if not retenus:
            return []

        # Le prefixe est deja un mot courant : ne proposer la suite que si
        # elle est franchement plus employee que lui.
        rang_prefixe = self.lexique.rang(prefixe.lower())
        if rang_prefixe <= RANG_MAXIMAL:
            meilleur = self.lexique.rang(retenus[0])
            if meilleur * AVANTAGE_EXIGE > rang_prefixe:
                return []

        return [_meme_casse(prefixe, mot) for mot in retenus]

    def suite(self, prefixe: str) -> str | None:
        """Ce qu'il resterait a taper pour accepter la premiere proposition.

        C'est ce que la touche de validation ecrira : le mot moins ce qui est
        deja a l'ecran. Rien si la proposition ne prolonge pas exactement ce
        qui est ecrit — un accent ajoute en cours de mot obligerait a effacer,
        ce que la prediction ne fait jamais.
        """
        propositions = self.completer(prefixe, maximum=1)
        if not propositions:
            return None
        mot = propositions[0]
        if not mot.startswith(prefixe):
            return None
        return mot[len(prefixe):] or None


def _est_un_mot(mot: str) -> bool:
    """Lettres, apostrophes et traits d'union.

    Les exclure ferait manquer « aujourd'hui » et « rendez-vous », qui sont
    justement les plus penibles a taper en entier.
    """
    return all(c.isalpha() or c in "'-\u2019" for c in mot)


def _meme_casse(modele: str, mot: str) -> str:
    """« Anni » propose « Anniversaire », pas « anniversaire »."""
    if modele[:1].isupper():
        return mot[:1].upper() + mot[1:]
    return mot
