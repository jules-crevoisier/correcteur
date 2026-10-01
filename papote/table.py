# -*- coding: utf-8 -*-
"""Une table de lignes triees, rangee d'un seul bloc.

Le lexique et la morphologie se consultent par dichotomie dans des fichiers
de plusieurs centaines de milliers de lignes. Les garder en `list[str]`
coutait un objet Python par ligne — quatre-vingts octets de structure pour
une vingtaine de lettres utiles : soixante megaoctets pour ce qui en pese
vingt.

Ici, tout le texte tient dans un seul `bytes`, et un tableau d'entiers dit
ou commence chaque ligne. La ligne n'est decodee qu'au moment ou on la lit,
soit une vingtaine de fois par recherche. L'ordre des octets UTF-8 est celui
des caracteres : la dichotomie donne les memes reponses qu'avant.
"""

from __future__ import annotations

import bisect
from array import array
from collections.abc import Sequence
from itertools import accumulate


class TableTriee(Sequence):
    """Se lit comme une `list[str]`, n'en a pas le poids."""

    __slots__ = ("_donnees", "_debuts", "_empreintes")

    def __init__(self, donnees: bytes):
        self._donnees = donnees
        self._empreintes: array | None = None
        # Le debut de chaque ligne, plus un debut fictif apres la derniere :
        # la ligne i s'etend de debuts[i] a debuts[i + 1] - 1.
        longueurs = map(len, donnees.split(b"\n"))
        self._debuts = array("I", accumulate(longueurs, lambda total, n: total + n + 1,
                                             initial=0))

    def __len__(self) -> int:
        return len(self._debuts) - 1

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[k] for k in range(*i.indices(len(self)))]
        if i < 0:
            i += len(self)
        if not 0 <= i < len(self):
            raise IndexError(i)
        return self._donnees[self._debuts[i]:self._debuts[i + 1] - 1].decode("utf-8")

    def contient_cle(self, cle: str) -> bool:
        """Une ligne commence-t-elle par cette cle (suivie d'une tabulation ou de rien) ?

        La recherche des fautes de frappe teste jusqu'a cent mille candidats
        par mot. Une dichotomie dans la table, lue ligne a ligne depuis Python,
        y passerait des secondes. On garde donc a part l'empreinte de chaque
        cle, triee dans un tableau d'entiers : quatre megaoctets, et une
        recherche qui reste en C.
        """
        empreintes = self.empreintes()
        h = hash(cle.encode("utf-8"))
        i = bisect.bisect_left(empreintes, h)
        return i < len(empreintes) and empreintes[i] == h

    def empreintes(self) -> array:
        if self._empreintes is None:
            self._empreintes = array("q", sorted(
                hash(ligne.split(b"\t", 1)[0])
                for ligne in self._donnees.split(b"\n")))
        return self._empreintes

    def octets(self, i: int) -> bytes:
        return self._donnees[self._debuts[i]:self._debuts[i + 1] - 1]


class _VueOctets(Sequence):
    """La meme table, lue en octets : la dichotomie n'a rien a decoder."""

    __slots__ = ("_table",)

    def __init__(self, table: TableTriee):
        self._table = table

    def __len__(self) -> int:
        return len(self._table)

    def __getitem__(self, i):
        return self._table.octets(i)


def position(lignes, cle: str, debut: int = 0) -> int:
    """`bisect_left` sur une liste comme sur une `TableTriee`.

    Sur la table, la cle est encodee une fois et comparee aux octets : une
    recherche ne decode plus que la ligne trouvee.
    """
    if isinstance(lignes, TableTriee):
        return bisect.bisect_left(_VueOctets(lignes), cle.encode("utf-8"), debut)
    return bisect.bisect_left(lignes, cle, debut)
