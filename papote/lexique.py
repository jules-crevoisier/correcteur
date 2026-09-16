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

Ce groupement fait tout le travail. Un mot inconnu se corrige en trois temps :

1. meme squelette — l'utilisateur a simplement omis ses accents ;
2. squelette a une frappe d'ecart — il a aussi fait une faute de frappe ;
3. squelette a deux frappes d'ecart — il en a fait deux, ou une inversion
   doublee d'un oubli, comme « ourné » pour « journée ».

Dans les trois cas on ne *devine* rien : on fabrique des candidats et on ne
garde que ceux qui existent. La liste de frequences departage les ex aequo,
une classe plus lointaine ne l'emportant que si elle les ecrase.

Quand plus rien ne departage — « ourné » vaut « journée » autant que
« durée » — `suggestion` se tait et `propositions` rend la courte liste :
c'est alors a l'utilisateur de choisir, et la fenetre la lui montre.
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
CLASSE_EDITION_DOUBLE = 2

# En dessous de cette longueur, une lettre d'ecart ne veut plus rien dire :
# « tt » deviendrait « et », « ct » deviendrait « cet ».
LONGUEUR_MINIMALE_EDITION = 4

# Deux lettres d'ecart, il en faut bien davantage : sur « tmp », la distance
# deux propose « temps », « type », « tome » et cinquante autres. A partir de
# cinq lettres elle redevient utile — c'est elle qui tire « journée » de
# « ourné », que la distance un laisse a « tourné ».
LONGUEUR_MINIMALE_EDITION_DOUBLE = 5

# Au-dela, le mot est trop rare pour qu'on le propose apres une faute de
# frappe : la coincidence est plus probable que l'intention. « jesper » ne
# doit pas devenir « jasper », 22 000e mot du francais, sous pretexte qu'il
# n'est qu'a une lettre. Les accents, eux, n'ont pas de plafond : rendre son
# accent a un mot ne change pas de mot.
RANG_MAXIMAL = (None, 20_000, 20_000)

# « Franchement courant » : les trois mille premiers mots du francais couvrent
# l'essentiel d'un message du quotidien. On s'en sert la ou une correction
# demande une garantie supplementaire.
RANG_COURANT = 3_000

# Un accent ne se tape pas par hasard. Celui qui ecrit « pasé » a voulu un
# « é » : lui proposer « pas », qui est pourtant cent fois plus courant, c'est
# lui retirer un mot.
ACCENTUEES = set("àâäéèêëîïôöùûüÿçœæÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇŒÆ")

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


def accentue(mot: str) -> bool:
    """Le mot porte-t-il au moins un accent, une cedille ou une ligature ?"""
    return any(caractere in ACCENTUEES for caractere in mot)


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

    # Au-dela de ce nombre de candidats, la fusion triee bat la dichotomie.
    SEUIL_FUSION = 5_000

    def __init__(self, dossier: Path | None = None,
                 lignes: list[str] | None = None,
                 frequences: list[str] | None = None):
        """`lignes` et `frequences` permettent aux tests d'injecter un mini-lexique."""
        self._dossier = dossier
        self._lignes = sorted(lignes) if lignes is not None else None
        self._rangs = (
            {m: i for i, m in enumerate(frequences)} if frequences is not None else None
        )
        self._cache: dict[tuple[str, int], list[Candidat]] = {}

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

    @staticmethod
    def _variantes(nu: str) -> set[str]:
        """Toutes les chaines a une frappe de `nu` — existantes ou non."""
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
        return formes

    def _retenir_existants(self, candidats: set[str]) -> set[str]:
        """Ne garde que les squelettes qui figurent au lexique.

        Sur quelques centaines de candidats, la dichotomie va plus vite. Sur
        les cent mille que produit la distance deux, elle coute une demi-
        seconde : mieux vaut trier les candidats et parcourir le lexique une
        seule fois, cote a cote, comme on fusionne deux listes triees.
        """
        if len(candidats) <= self.SEUIL_FUSION:
            return {candidat for candidat in candidats if self.existe(candidat)}

        trouves = set()
        lignes = self.lignes
        position = 0
        for candidat in sorted(candidats):
            position = bisect.bisect_left(lignes, candidat, position)
            if position >= len(lignes):
                break
            ligne = lignes[position]
            if ligne == candidat or ligne.startswith(candidat + "\t"):
                trouves.add(candidat)
        return trouves

    def _squelettes_voisins(self, nu: str) -> set[str]:
        """Squelettes du lexique a une frappe d'ecart de `nu`."""
        return self._retenir_existants(self._variantes(nu))

    def _squelettes_lointains(self, nu: str) -> set[str]:
        """Squelettes du lexique a deux frappes d'ecart de `nu`."""
        lointains = set()
        for voisin in self._variantes(nu):
            lointains |= self._variantes(voisin)
        lointains.discard(nu)
        return self._retenir_existants(lointains)

    def candidats(self, mot: str,
                  classe_max: int = CLASSE_EDITION_DOUBLE) -> list[Candidat]:
        """Remplacements plausibles, du plus au moins probable.

        `classe_max` borne la *recherche*, pas seulement son resultat : la
        distance deux coute cent fois la distance un, on ne la paie donc que
        lorsqu'on est pret a s'en servir.
        """
        minuscule = mot.lower()
        cle_cache = (minuscule, classe_max)
        if cle_cache in self._cache:
            return self._cache[cle_cache]

        nu = squelette(minuscule)
        trouves: dict[str, int] = {}

        # 1. Meme squelette : il ne manquait que les accents.
        for forme in self.formes(minuscule):
            if forme.lower() != minuscule:
                trouves[forme] = CLASSE_ACCENT

        # Un mot accentue ne se corrige qu'en un autre mot accentue :
        # « pasé » peut devenir « passé », jamais « pas ».
        garder_accent = accentue(minuscule)

        def recueillir(squelettes, classe):
            for voisin in squelettes:
                for forme in self.formes(voisin):
                    if garder_accent and not accentue(forme):
                        continue
                    trouves.setdefault(forme, classe)

        # Les accents suffisent a expliquer le mot : inutile d'aller plus loin,
        # « prés » ne se corrige pas en « pris ».
        accents_seuls = bool(trouves)

        # 2. Squelette voisin : une frappe d'ecart.
        if (not accents_seuls and classe_max >= CLASSE_EDITION
                and len(nu) >= LONGUEUR_MINIMALE_EDITION):
            recueillir(self._squelettes_voisins(nu), CLASSE_EDITION)

        # 3. Deux frappes d'ecart. On la lance meme quand la distance un a
        #    repondu : sur « ourné » elle propose « tourné » et « orné », deux
        #    mots rares qui se valent, alors que « journée » attend a deux
        #    frappes. C'est `suggestion` qui tranchera entre les deux classes.
        if (not accents_seuls and classe_max >= CLASSE_EDITION_DOUBLE
                and len(nu) >= LONGUEUR_MINIMALE_EDITION_DOUBLE):
            recueillir(self._squelettes_lointains(nu), CLASSE_EDITION_DOUBLE)

        # « reunion » a deux graphies : « réunion » et « Réunion ». L'ile
        # tenait le mot en otage — deux candidats qui se valent, donc aucune
        # correction. Quand une forme minuscule existe, sa jumelle capitalisee
        # cesse d'etre une concurrente. « paris » garde « Paris », lui : la
        # jumelle minuscule n'existe pas.
        if not minuscule[:1].isupper():
            en_bas = {f.lower() for f in trouves if not f[:1].isupper()}
            trouves = {
                f: c for f, c in trouves.items()
                if not (f[:1].isupper() and f.lower() in en_bas)
            }

        candidats = sorted(
            (Candidat(forme, classe, self.rang(forme))
             for forme, classe in trouves.items()),
            key=lambda c: c.cle,
        )
        self._cache[cle_cache] = candidats
        return candidats

    # -- decision -----------------------------------------------------------

    def suggestion(self, mot: str,
                   classe_max: int = CLASSE_EDITION_DOUBLE) -> str | None:
        """Le remplacement a appliquer sans rien demander, s'il est evident.

        `classe_max` limite la recherche aux candidats les plus surs : passer
        CLASSE_ACCENT ne laisse que la restitution des accents.

        « Evident » veut dire : un candidat courant, et nettement plus courant
        que son suivant. Devant deux candidats aussi plausibles l'un que
        l'autre (« prés » et « près »), on prefere ne rien faire : garder une
        faute vaut mieux qu'en inventer une.

        Les classes sont examinees de la plus sure a la moins sure. Une classe
        ne l'emporte sur les precedentes que si son candidat les ecrase : sur
        « ourné », « journée » (384e mot du francais) bat « tourné » (3217e)
        malgre la frappe supplementaire qu'il demande.
        """
        candidats = self.candidats(mot, classe_max)
        candidats = [c for c in candidats if c.classe <= classe_max]

        # Le meilleur candidat des classes deja examinees, quand aucune n'a
        # su trancher. La suivante devra faire mieux que lui.
        recale: Candidat | None = None

        for classe in sorted({c.classe for c in candidats}):
            groupe = [c for c in candidats if c.classe == classe]
            meilleur = groupe[0]

            if meilleur.rang == RANG_INCONNU:
                # Le mot existe, mais il ne figure pas parmi les 48 000 formes
                # les plus employees : trop rare pour qu'on parie dessus. Les
                # classes suivantes sont encore moins sures.
                break

            # Une faute de frappe dans un mot rare : la coincidence est plus
            # probable que l'intention.
            plafond = RANG_MAXIMAL[classe]
            if plafond is not None and meilleur.rang > plafond:
                break

            # Une correction par edition invente une lettre : il lui faut une
            # marge plus large qu'a une simple restitution d'accents. Cinq fois
            # plus courant que son suivant, c'est deja un ecart qu'on ne trouve
            # pas entre deux mots egalement plausibles.
            ecart_exige = 5 if classe >= CLASSE_EDITION else 3

            if len(groupe) > 1 and groupe[1].rang <= meilleur.rang * ecart_exige:
                # Deux mots se valent dans cette classe : on passe la main,
                # mais le meilleur reste la barre a franchir.
                if recale is None or meilleur.rang < recale.rang:
                    recale = meilleur
                continue

            if recale is not None and recale.rang < meilleur.rang * ecart_exige:
                # La classe plus sure gardait un candidat comparable : on ne
                # lui prefere pas une correction plus lointaine.
                break

            return _meme_casse(mot, meilleur.mot)

        return None

    # Dans une liste de propositions, c'est l'humain qui tranche : on peut donc
    # melanger les classes, a condition de rappeler qu'une frappe de plus rend
    # le candidat moins probable. Sans cette penalite « ourné » proposerait
    # « tourné » (3217e mot du francais) avant « journée » (384e).
    PENALITE_PROPOSITION = (1, 4, 12)

    def propositions(self, mot: str, maximum: int = 4) -> list[str]:
        """Ce qu'on peut proposer a la place d'un mot, a defaut d'en etre sur.

        `suggestion` se tait des que deux candidats se valent — c'est ce qui
        lui evite d'inventer des fautes. Mais se taire n'aide personne devant
        « ourné » : ici on rend la courte liste, et l'utilisateur choisit.
        """
        classes = sorted(
            (c for c in self.candidats(mot) if c.rang != RANG_INCONNU),
            key=lambda c: c.rang * self.PENALITE_PROPOSITION[c.classe],
        )
        minuscule = mot.lower()
        retenus: list[str] = []
        vus: set[str] = set()
        for candidat in classes:
            cle = candidat.mot.lower()
            if cle == minuscule or cle in vus:
                continue
            vus.add(cle)
            retenus.append(_meme_casse(mot, candidat.mot))
            if len(retenus) == maximum:
                break
        return retenus
