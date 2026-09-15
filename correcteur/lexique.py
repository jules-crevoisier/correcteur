# -*- coding: utf-8 -*-
"""Le dictionnaire francais et la fabrique de suggestions.

Le lexique est une liste de formes flechies (450 000 mots), produite une fois
pour toutes par `outils/construire_lexique.py` a partir du dictionnaire
Hunspell de Dicollecte. Il arrive deja groupe par *squelette* — la graphie du
mot privee de ses accents — et trie, ce qui permet de le consulter par
dichotomie sans construire le moindre index au demarrage :

    gateaux\tgâteaux
    pres\tprès prés prêts
    bonjour

Ce groupement fait tout le travail. Un mot inconnu se corrige en deux temps :

1. meme squelette — l'utilisateur a simplement omis ses accents ;
2. squelette a une frappe d'ecart — il a aussi fait une faute de frappe.

Dans les deux cas on ne *devine* rien : on fabrique des candidats et on ne
garde que ceux qui existent. La liste de frequences departage les ex aequo.
"""

from __future__ import annotations

import bisect
import gzip
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .chemins import dossier_donnees

# Lettres utilisees pour fabriquer les variantes a une frappe d'ecart. Les
# accents n'y figurent pas : ils sont deja couverts par l'index des squelettes.
ALPHABET = "abcdefghijklmnopqrstuvwxyz-'"

CLASSE_ACCENT = 0
CLASSE_EDITION = 1

# En dessous de cette longueur, une lettre d'ecart ne veut plus rien dire :
# « tt » deviendrait « et », « ct » deviendrait « cet ».
LONGUEUR_MINIMALE_EDITION = 4

# Un mot absent de la liste de frequences recoit ce rang : il existe, mais il
# est trop rare pour qu'on remplace quoi que ce soit par lui sans preuve.
RANG_INCONNU = 10 ** 9


def _table_sans_accents() -> dict[int, str]:
    """Table de conversion lettre accentuee -> lettre nue.

    `str.translate` est dix fois plus rapide que `unicodedata.normalize`, et
    on l'applique a 450 000 mots au chargement.
    """
    table: dict[int, str] = {}
    for code in range(0x00C0, 0x0250):
        caractere = chr(code)
        decompose = unicodedata.normalize("NFD", caractere)
        nu = "".join(c for c in decompose if unicodedata.category(c) != "Mn")
        if nu and nu != caractere:
            table[code] = nu
    table[ord("œ")] = "oe"
    table[ord("Œ")] = "OE"
    table[ord("æ")] = "ae"
    table[ord("Æ")] = "AE"
    table[ord("’")] = "'"
    return table


_TABLE_NUE = _table_sans_accents()


def sans_accents(texte: str) -> str:
    """« Gâteaux » -> « Gateaux ». Le squelette d'un mot."""
    return texte.translate(_TABLE_NUE)


def squelette(texte: str) -> str:
    """La forme sous laquelle un mot est indexe : sans accents ni majuscules."""
    return sans_accents(texte).lower()


class LexiqueIntrouvable(RuntimeError):
    """Les fichiers de donnees n'ont pas ete trouves."""


@dataclass(frozen=True)
class Candidat:
    mot: str
    classe: int
    rang: int

    @property
    def cle(self) -> tuple[int, int, int]:
        return (self.classe, self.rang, len(self.mot))


def _meme_casse(modele: str, mot: str) -> str:
    """Rend `mot` avec la casse de `modele` : « Gateaux » -> « Gâteaux »."""
    if len(modele) > 1 and modele.isupper():
        return mot.upper()
    if modele[:1].isupper():
        return mot[:1].upper() + mot[1:]
    return mot


class Lexique:
    """Les mots du francais, et ce qu'on peut proposer a la place d'un intrus."""

    def __init__(self, dossier: Path | None = None,
                 lignes: list[str] | None = None,
                 frequences: list[str] | None = None):
        """`lignes` et `frequences` permettent aux tests d'injecter un mini-lexique."""
        self._dossier = dossier
        self._lignes = sorted(lignes) if lignes is not None else None
        self._rangs = (
            {m: i for i, m in enumerate(frequences)} if frequences is not None else None
        )
        self._cache: dict[str, list[Candidat]] = {}

    @classmethod
    def depuis_formes(cls, formes: list[str], frequences: list[str] | None = None):
        """Construit un lexique a partir de graphies brutes. Pratique en test."""
        groupes: dict[str, list[str]] = {}
        for forme in formes:
            groupes.setdefault(squelette(forme), []).append(forme)
        lignes = [
            nu if sorted(set(graphies)) == [nu] else nu + "\t" + " ".join(sorted(set(graphies)))
            for nu, graphies in groupes.items()
        ]
        return cls(lignes=lignes, frequences=frequences if frequences is not None else formes)

    # -- chargement ---------------------------------------------------------

    def _lire(self, nom: str) -> list[str]:
        dossier = self._dossier or dossier_donnees()
        chemin = dossier / nom
        if not chemin.is_file():
            raise LexiqueIntrouvable(
                f"Le fichier {chemin} est introuvable.\n"
                "Le dossier « donnees » doit accompagner l'application."
            )
        with gzip.open(chemin, "rt", encoding="utf-8") as f:
            return f.read().split("\n")

    @property
    def lignes(self) -> list[str]:
        if self._lignes is None:
            self._lignes = self._lire("lexique_fr.txt.gz")
        return self._lignes

    @property
    def rangs(self) -> dict[str, int]:
        if self._rangs is None:
            self._rangs = {
                m: i for i, m in enumerate(self._lire("frequences_fr.txt.gz"))
            }
        return self._rangs

    def charger(self) -> None:
        """Force la lecture des fichiers, pour la faire au moment choisi."""
        self.lignes  # noqa: B018
        self.rangs  # noqa: B018

    # -- consultation -------------------------------------------------------

    def _ligne(self, nu: str) -> str | None:
        """La ligne du lexique decrivant ce squelette, par dichotomie."""
        lignes = self.lignes
        position = bisect.bisect_left(lignes, nu)
        if position >= len(lignes):
            return None
        ligne = lignes[position]
        # Le squelette occupe seul sa ligne, ou precede une tabulation.
        if ligne == nu or ligne.startswith(nu + "\t"):
            return ligne
        return None

    def formes(self, mot: str) -> tuple[str, ...]:
        """Toutes les graphies connues qui partagent le squelette de `mot`."""
        nu = squelette(mot)
        ligne = self._ligne(nu)
        if ligne is None:
            return ()
        if "\t" not in ligne:
            return (nu,)
        return tuple(ligne.split("\t", 1)[1].split(" "))

    def existe(self, nu: str) -> bool:
        """Ce squelette figure-t-il au lexique ?"""
        return self._ligne(nu) is not None

    def connait(self, mot: str) -> bool:
        """Le mot existe-t-il tel qu'il est ecrit, a la casse pres ?"""
        if not mot:
            return False
        formes = self.formes(mot)
        if not formes:
            return False
        if mot in formes or mot.lower() in formes:
            return True
        # « DEMAIN » ou « Demain » en debut de phrase valent « demain » ;
        # l'inverse n'est pas vrai : « paris » ne vaut pas « Paris ».
        return mot[:1].isupper() and mot.lower().capitalize() in formes

    def rang(self, mot: str) -> int:
        """Position du mot parmi les plus employes (petit = courant)."""
        rangs = self.rangs
        minuscule = mot.lower()
        if minuscule in rangs:
            return rangs[minuscule]
        return rangs.get(mot, RANG_INCONNU)

    # -- fabrication de candidats -------------------------------------------

    def _squelettes_voisins(self, nu: str) -> set[str]:
        """Squelettes du lexique a une frappe d'ecart de `nu`."""
        decoupes = [(nu[:i], nu[i:]) for i in range(len(nu) + 1)]
        formes = set()

        for gauche, droite in decoupes:
            if droite:
                formes.add(gauche + droite[1:])                            # oubli
                if len(droite) > 1:
                    formes.add(gauche + droite[1] + droite[0] + droite[2:])  # inversion
                for lettre in ALPHABET:
                    formes.add(gauche + lettre + droite[1:])               # echange
            for lettre in ALPHABET:
                formes.add(gauche + lettre + droite)                       # ajout

        formes.discard(nu)
        return {forme for forme in formes if self.existe(forme)}

    def candidats(self, mot: str) -> list[Candidat]:
        """Remplacements plausibles, du plus au moins probable."""
        minuscule = mot.lower()
        if minuscule in self._cache:
            return self._cache[minuscule]

        nu = squelette(minuscule)
        trouves: dict[str, int] = {}

        # 1. Meme squelette : il ne manquait que les accents.
        for forme in self.formes(minuscule):
            if forme.lower() != minuscule:
                trouves[forme] = CLASSE_ACCENT

        # 2. Squelette voisin. Deux fois plus bavard, donc deux fois plus
        #    risque : on ne s'en sert que si le premier n'a rien donne.
        if not trouves and len(nu) >= LONGUEUR_MINIMALE_EDITION:
            for voisin in self._squelettes_voisins(nu):
                for forme in self.formes(voisin):
                    trouves.setdefault(forme, CLASSE_EDITION)

        candidats = sorted(
            (Candidat(forme, classe, self.rang(forme))
             for forme, classe in trouves.items()),
            key=lambda c: c.cle,
        )
        self._cache[minuscule] = candidats
        return candidats

    # -- decision -----------------------------------------------------------

    def suggestion(self, mot: str, classe_max: int = CLASSE_EDITION) -> str | None:
        """Le remplacement a appliquer sans rien demander, s'il est evident.

        `classe_max` limite la recherche aux candidats les plus surs : passer
        CLASSE_ACCENT ne laisse que la restitution des accents.

        « Evident » veut dire : un candidat courant, et nettement plus courant
        que son suivant. Devant deux candidats aussi plausibles l'un que
        l'autre (« prés » et « près »), on prefere ne rien faire : garder une
        faute vaut mieux qu'en inventer une.
        """
        candidats = [c for c in self.candidats(mot) if c.classe <= classe_max]
        if not candidats:
            return None

        meilleur = candidats[0]
        if meilleur.rang == RANG_INCONNU:
            # Le mot existe, mais il ne figure pas parmi les 48 000 formes
            # les plus employees : trop rare pour qu'on parie dessus.
            return None

        # Une correction par edition invente une lettre : il lui faut une
        # marge plus large qu'a une simple restitution d'accents.
        ecart_exige = 8 if meilleur.classe == CLASSE_EDITION else 3

        concurrents = [c for c in candidats[1:] if c.classe == meilleur.classe]
        if concurrents and concurrents[0].rang <= meilleur.rang * ecart_exige:
            return None

        return _meme_casse(mot, meilleur.mot)
