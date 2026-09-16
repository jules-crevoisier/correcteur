# -*- coding: utf-8 -*-
"""Relecture : voir ce qui va changer, et choisir.

La correction automatique est faite pour le quotidien. Pour un message qui
compte — une candidature, un message a un client — on veut regarder avant de
laisser faire.

Ce module compare le texte d'origine au texte corrige et en tire une liste de
changements, chacun acceptable ou refusable separement. Il ne demande rien au
correcteur : il regarde seulement les deux textes. C'est ce qui le rend
independant du nombre de passes, de l'ordre des regles et du reste.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

# On compare mot a mot, ponctuation et espaces compris : un changement doit
# pouvoir se lire, et « ils on » -> « ils ont » n'est pas une affaire de
# lettres.
_DECOUPE = re.compile(r"\w+|\W", re.UNICODE)


@dataclass
class Changement:
    """Un endroit ou le texte corrige differe de l'original."""

    avant: str
    apres: str
    accepte: bool = True

    def __str__(self) -> str:
        avant = self.avant.strip() or "∅"
        apres = self.apres.strip() or "∅"
        return f"{avant} → {apres}"


def _jetons(texte: str) -> list[str]:
    return _DECOUPE.findall(texte)


def changements(original: str, corrige: str) -> list[Changement]:
    """Ce qui separe les deux textes, morceau par morceau."""
    gauche, droite = _jetons(original), _jetons(corrige)
    trouves = []
    for operation, g1, g2, d1, d2 in difflib.SequenceMatcher(
        None, gauche, droite, autojunk=False
    ).get_opcodes():
        if operation == "equal":
            continue
        trouves.append(Changement("".join(gauche[g1:g2]), "".join(droite[d1:d2])))
    return trouves


def composer(original: str, corrige: str,
             choix: list[Changement]) -> str:
    """Reconstruit le texte en ne gardant que les changements acceptes."""
    gauche, droite = _jetons(original), _jetons(corrige)
    morceaux, reste = [], list(choix)

    for operation, g1, g2, d1, d2 in difflib.SequenceMatcher(
        None, gauche, droite, autojunk=False
    ).get_opcodes():
        if operation == "equal":
            morceaux.append("".join(gauche[g1:g2]))
            continue
        changement = reste.pop(0) if reste else None
        accepte = changement.accepte if changement is not None else True
        morceaux.append("".join(droite[d1:d2] if accepte else gauche[g1:g2]))

    return "".join(morceaux)
