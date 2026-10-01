# -*- coding: utf-8 -*-
"""Le modele statistique : trancher les homophones par l'usage.

Les regles savent ce qu'elles savent : « ils on » appelle « ont », parce que
quelqu'un l'a ecrit. Mais « a » ou « à », « ou » ou « où », « son » ou
« sont », « manger » ou « mangé » se decident le plus souvent par ce qui
entoure le mot, de mille facons qu'aucune liste ne couvre.

Ce module compte, dans un grand corpus de francais correct, les contextes de
ces mots-la et d'eux seuls :

    « il a mangé »    ->   (il, a)  (a, mangé)  (il, a, mangé) ...
    « va à la plage » ->   (va, à)  (à, la)    (va, à, la) ...

Pour corriger, il remplace le mot par chacun de ses homophones et additionne
le logarithme des comptes de tous les morceaux de contexte qui le contiennent
(la methode « SUMLM » de Bergsma, Lin et Goebel, 2009). Le candidat qui
l'emporte nettement remplace le mot ecrit ; s'il ne l'emporte que de peu, on
ne touche a rien.

Les verbes du premier groupe ont un traitement a part. « manger », « mangé »,
« mangez » se prononcent pareil, et il y a des milliers de verbes : on ne
compte pas leurs contextes un par un, mais ceux de leur **forme** — infinitif,
participe, deuxieme personne. « pour » annonce un infinitif quel que soit le
verbe, « a » un participe. C'est ce qui permet a un modele de quelques
megaoctets de couvrir des verbes qu'il n'a jamais vus.

Le fichier (donnees/modele_fr.bin.gz) ne contient que des empreintes de
contextes et des comptes : aucune phrase du corpus n'y survit. Il est
fabrique par « outils/entrainer_modele.py ».

Format, en petit-boutiste :

    b"PAPOTE-NG1"                 signature
    uint32  n                     nombre d'entrees
    uint32  cles[n]               empreintes triees (crc32)
    uint16  comptes[n]            comptes, plafonnes a 65 535
"""

from __future__ import annotations

import gzip
import math
import re
import struct
import zlib
from array import array
from bisect import bisect_left
from pathlib import Path

SIGNATURE = b"PAPOTE-NG1"

# Les ensembles de mots qui se prononcent (presque) pareil et s'ecrivent
# differemment. Un mot peut n'appartenir qu'a un ensemble.
HOMOPHONES = [
    {"a", "à"},
    {"ou", "où"},
    {"son", "sont"},
    {"ces", "ses", "c'est", "s'est", "sais", "sait"},
    {"ce", "se"},
    {"la", "là", "l'a"},
    {"et", "est"},
    {"on", "ont"},
    {"leur", "leurs"},
    {"ça", "sa"},
    {"peu", "peut", "peux"},
    {"mes", "mais", "met", "mets"},
    {"ni", "n'y"},
    {"dans", "d'en"},
    {"tout", "tous"},
    {"si", "s'y"},
    {"sans", "s'en"},
    {"près", "prêt"},
    {"du", "dû"},
    {"sur", "sûr"},
    {"ma", "m'a"},
    {"ta", "t'a", "t'as"},
    {"mon", "m'ont"},
    {"ton", "t'ont"},
    {"quel", "quelle", "quels", "quelles", "qu'elle", "qu'elles"},
    {"voir", "voire"},
    {"cours", "court", "cour"},
    {"davantage", "d'avantage"},
]
ENSEMBLE_DE = {mot: frozenset(e) for e in HOMOPHONES for mot in e}

# Les formes des verbes du premier groupe qui se prononcent [e]. La deuxieme
# personne (« mangez ») est comptee mais jamais proposee : « allez dans le
# pays ou consultez notre page » est un imperatif que deux mots de contexte
# ne distinguent pas d'un infinitif.
INF, PP, P2 = "§INF", "§PP", "§2P"
CLASSES_VERBALES = (INF, PP)

# La ponctuation fait partie du contexte : « tu vas où ? » ne se lit pas
# comme « tu vas ou tu restes ».
_FIN = re.compile(r"[.!?…]")
_PAUSE = re.compile(r"[,;:]")
_NOMBRE = re.compile(r"^\d+([.,]\d+)?$")

DEBUT, FIN = "<s>", "</s>"

# Le poids de chaque sorte de contexte dans le score.
POIDS = {"G2": 1.0, "G1": 1.0, "D1": 1.0, "D2": 1.0, "M": 1.2}


def normaliser(mot: str) -> str:
    mot = mot.lower().replace("’", "'")
    return "<n>" if _NOMBRE.match(mot) else mot


def sequence(textes: list[str], separateurs: list[str]) -> tuple[list[str], list[int]]:
    """Les mots et la ponctuation, et ou se trouve chaque mot dans la suite.

    `separateurs[k]` est le texte entre le mot k et le suivant.
    """
    suite = [DEBUT]
    place = []
    for k, mot in enumerate(textes):
        place.append(len(suite))
        suite.append(normaliser(mot))
        entre = separateurs[k] if k < len(separateurs) else ""
        if _FIN.search(entre):
            suite.append(".")
        elif _PAUSE.search(entre):
            suite.append(",")
    suite.append(FIN)
    return suite, place


def contextes(suite: list[str], p: int, cible: str) -> list[tuple[str, str]]:
    """Les morceaux de contexte de la position p, la cible a la place du mot."""
    g2 = suite[p - 2] if p >= 2 else DEBUT
    g1 = suite[p - 1]
    d1 = suite[p + 1]
    d2 = suite[p + 2] if p + 2 < len(suite) else FIN
    return [
        ("G1", f"{g1}\x1f{cible}"),
        ("D1", f"{cible}\x1f{d1}"),
        ("G2", f"{g2}\x1f{g1}\x1f{cible}"),
        ("M", f"{g1}\x1f{cible}\x1f{d1}"),
        ("D2", f"{cible}\x1f{d1}\x1f{d2}"),
    ]


def empreinte(sorte: str, cle: str) -> int:
    return zlib.crc32(f"{sorte}\x1e{cle}".encode("utf-8"))


class Modele:
    """Les comptes, et la facon de s'en servir."""

    def __init__(self, cles: array, comptes: array):
        self._cles = cles
        self._comptes = comptes

    # -- chargement ---------------------------------------------------------

    @classmethod
    def charger(cls, chemin: Path) -> "Modele | None":
        try:
            with gzip.open(chemin, "rb") as f:
                donnees = f.read()
        except OSError:
            return None
        if not donnees.startswith(SIGNATURE):
            return None
        (n,) = struct.unpack_from("<I", donnees, len(SIGNATURE))
        debut = len(SIGNATURE) + 4
        cles = array("I")
        cles.frombytes(donnees[debut:debut + 4 * n])
        comptes = array("H")
        comptes.frombytes(donnees[debut + 4 * n:debut + 6 * n])
        return cls(cles, comptes)

    @staticmethod
    def ecrire(chemin: Path, table: dict[int, int]) -> None:
        cles = sorted(table)
        with gzip.open(chemin, "wb", compresslevel=9) as f:
            f.write(SIGNATURE)
            f.write(struct.pack("<I", len(cles)))
            f.write(array("I", cles).tobytes())
            f.write(array("H", (min(table[c], 65535) for c in cles)).tobytes())

    def __len__(self) -> int:
        return len(self._cles)

    # -- consultation -------------------------------------------------------

    def compte(self, sorte: str, cle: str) -> int:
        h = empreinte(sorte, cle)
        i = bisect_left(self._cles, h)
        if i < len(self._cles) and self._cles[i] == h:
            return self._comptes[i]
        return 0

    def score(self, suite: list[str], p: int, cible: str) -> tuple[float, int]:
        """(score, preuves) : la somme ponderee des log-comptes, et le total brut."""
        total = 0.0
        preuves = 0
        for sorte, cle in contextes(suite, p, cible):
            n = self.compte(sorte, cle)
            preuves += n
            total += POIDS[sorte] * math.log1p(n)
        return total, preuves

    def trancher(self, suite: list[str], p: int, ecrit: str,
                 candidats, marge: float, preuves_min: int,
                 garde: int = 2, rapport: float = 10.0,
                 garde_bigrammes: int | None = 30):
        """Le candidat qui l'emporte nettement sur ce qui est ecrit, ou None.

        Deux conditions, en plus de l'ecart de score :

        - le candidat doit s'appuyer sur assez de contextes vus ;
        - si ce qui est ecrit a deja ete vu dans ce contexte precis (le mot
          et ses voisins immediats, au moins `garde` fois), on ne le
          remplace que si le candidat y est `rapport` fois plus courant.
          « l'on riait de voir s'en retourner » existe : on n'y touche pas.
        """
        score_ecrit, _ = self.score(suite, p, ecrit)
        meilleur, score_meilleur, preuves_meilleur = None, score_ecrit, 0
        for candidat in candidats:
            if candidat == ecrit:
                continue
            s, preuves = self.score(suite, p, candidat)
            if s > score_meilleur:
                meilleur, score_meilleur, preuves_meilleur = candidat, s, preuves
        if meilleur is None:
            return None
        if score_meilleur - score_ecrit < marge or preuves_meilleur < preuves_min:
            return None
        if garde:
            vus_ecrit = dict((sorte, self.compte(sorte, cle))
                             for sorte, cle in contextes(suite, p, ecrit))
            vus_meilleur = dict((sorte, self.compte(sorte, cle))
                                for sorte, cle in contextes(suite, p, meilleur))
            # Les bigrammes protegent aussi, mais il leur faut plus de
            # temoins : « voire même » n'a qu'un voisin pour lui.
            seuils = [("M", garde), ("G2", garde), ("D2", garde)]
            if garde_bigrammes:
                seuils += [("G1", garde_bigrammes), ("D1", garde_bigrammes)]
            for sorte, seuil in seuils:
                if vus_ecrit[sorte] >= seuil and \
                        vus_meilleur[sorte] < rapport * vus_ecrit[sorte]:
                    return None
        return meilleur


# -- les verbes du premier groupe ----------------------------------------------

def classe_verbale(morphologie, mot: str) -> tuple[str, str] | None:
    """(classe, lemme) d'une forme en [e] d'un verbe du premier groupe."""
    if not mot or not mot.endswith(("er", "é", "és", "ée", "ées", "ez")):
        return None
    traits = morphologie.traits(mot)
    if not traits:
        return None
    lemmes = [l for l in morphologie.lemmes(mot) if l.endswith("er")]
    if len(lemmes) != 1:
        return None
    nominal = bool(traits & {"ms", "fs", "mp", "fp", "xs", "xp"})
    if mot.endswith("er"):
        # « manger », « dîner » sont aussi des noms (« le manger »), mais
        # leur emploi de nom a le meme voisinage que l'infinitif.
        if "inf" in traits:
            return INF, lemmes[0]
        return None
    if traits & {"pms", "pmp", "pfs", "pfp"} and not nominal:
        # « le marché », « une entrée », « l'été » : un participe qui est
        # aussi un nom courant. On n'y touche pas.
        return PP, lemmes[0]
    return None


def forme_de_classe(morphologie, lemme: str, classe: str, _ecrit: str = "") -> str | None:
    """La forme du lemme dans cette classe : « manger », « mangé », « mangez »."""
    groupes = morphologie.paradigme(lemme)
    if len(groupes) < 2:
        return None
    if classe == INF:
        return lemme
    if classe == PP:
        # Le masculin singulier : les regles d'accord l'ajusteront ensuite.
        for f, t in groupes[0].items():
            if "pms" in t:
                return f
        return None
    if classe == P2:
        for f, t in groupes[1].items():
            if "2p" in t:
                return f
    return None
