# -*- coding: utf-8 -*-
"""De la parole au texte lisible.

La reconnaissance vocale rend un ruban de mots : pas de majuscules, pas de
ponctuation, pas d'accents fiables, et le registre parle tel quel.

    bonjour tout le monde donc on se retrouve pour le point hebdo je pense
    qu on peut commencer par le budget

C'est illisible, et pourtant tout y est. Ce qui manque n'est pas dans le son :
c'est de la mise en forme, et deux signaux suffisent a la retrouver.

**Les silences.** Le moteur de reconnaissance date chaque mot. Un blanc d'une
seconde entre deux mots, c'est un point ; un blanc court, c'est une virgule.
Personne ne parle en ponctuant, mais tout le monde respire aux memes endroits.

**Le correcteur.** Papote sait deja rendre les accents, accorder les verbes et
trancher les homophones — et surtout, il sait le faire **sans toucher au
registre**. Un compte rendu ou « j'ai pas eu le temps » devient « je n'ai pas
eu le temps » ne ressemble plus a ce qui a ete dit. C'est la raison d'etre de
ce module ici plutot qu'ailleurs : le meme moteur qui respecte votre facon
d'ecrire respecte votre facon de parler.

Reste les locuteurs. Le moteur rend, pour chaque phrase, une **empreinte
vocale** : cent vingt-huit nombres qui decrivent une voix. Deux phrases de la
meme personne ont des empreintes proches, et cela suffit a les regrouper sans
jamais savoir de qui il s'agit. Personne n'est identifie : on sait seulement
que celui qui parle n'est pas celui d'avant.

Rien ne sort de la machine. Ni le son, ni le texte, ni les empreintes.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field

# -- ponctuation ------------------------------------------------------------

# Un blanc plus long que cela entre deux mots ferme une phrase. En dessous de
# la demi-seconde, c'est une respiration : au plus une virgule.
SILENCE_DE_PHRASE = 0.85
SILENCE_DE_VIRGULE = 0.38

# Une phrase plus longue que cela sans le moindre silence se coupe quand
# meme : personne ne dit quarante mots d'un souffle, et si le moteur n'a pas
# entendu de blanc, c'est lui qui se trompe.
MOTS_AVANT_COUPURE = 40

# Mots qui ouvrent une question. Le point d'interrogation ne s'entend pas,
# mais il s'annonce.
OUVERTURES_INTERROGATIVES = {
    "est-ce", "pourquoi", "comment", "combien", "quand", "où", "qui",
    "quel", "quelle", "quels", "quelles", "qu'est-ce", "lequel",
    "laquelle", "quoi",
}

# Ceux-la ouvrent une subordonnee, pas une question : « je sais pas
# pourquoi » n'est pas une question, « pourquoi tu dis ca » en est une.
AVANT_UNE_SUBORDONNEE = {
    "sais", "sait", "savez", "savons", "dis", "dit", "dites", "demande",
    "demandes", "demandez", "comprends", "comprend", "vois", "voit",
    "explique", "expliques", "expliquez", "raconte", "montre", "oublie",
}

# Mots qui commencent une nouvelle phrase quand ils suivent un silence : ils
# relancent, ils ne prolongent pas.
RELANCES = {
    "donc", "alors", "bon", "bref", "sinon", "ensuite", "après", "voilà",
    "ok", "d'accord", "oui", "non", "effectivement", "exactement",
}


@dataclass(frozen=True)
class Mot:
    """Un mot et sa place dans le temps, telle que le moteur l'a entendue."""

    texte: str
    debut: float
    fin: float


@dataclass(frozen=True)
class Segment:
    """Ce que le moteur rend d'un seul coup : des mots et une voix.

    `empreinte` est le vecteur qui decrit la voix. Il est vide quand le
    modele de locuteurs n'est pas charge — la transcription marche alors
    tout aussi bien, mais tout le monde parle d'une seule voix.
    """

    mots: tuple[Mot, ...]
    empreinte: tuple[float, ...] = ()

    @property
    def debut(self) -> float:
        return self.mots[0].debut if self.mots else 0.0

    @property
    def fin(self) -> float:
        return self.mots[-1].fin if self.mots else 0.0

    @property
    def texte(self) -> str:
        return " ".join(mot.texte for mot in self.mots)


@dataclass
class Tour:
    """Une prise de parole : qui, quand, et quoi — mis en forme."""

    locuteur: str
    debut: float
    fin: float
    texte: str

    @property
    def duree(self) -> float:
        return max(0.0, self.fin - self.debut)


# ---------------------------------------------------------------------------
# Les locuteurs
# ---------------------------------------------------------------------------

# Au-dessus de cette ressemblance entre deux empreintes, c'est la meme voix.
# Le seuil est volontairement bas : se tromper en separant deux tours d'une
# meme personne abime moins un compte rendu que de fondre deux personnes en
# une seule. Dans le doute, on ouvre une voix de plus.
RESSEMBLANCE_MINIMALE = 0.70

# En dessous, l'empreinte est calculee sur trop peu de son pour valoir
# quelque chose : le segment rejoint le locuteur precedent.
DUREE_MINIMALE_EMPREINTE = 1.2


def ressemblance(a, b) -> float:
    """Le cosinus entre deux empreintes, ramene entre 0 et 1.

    Pas de numpy : cent vingt-huit multiplications ne valent pas dix-sept
    megaoctets de dependance dans l'executable.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    produit = sum(x * y for x, y in zip(a, b))
    norme_a = math.sqrt(sum(x * x for x in a))
    norme_b = math.sqrt(sum(y * y for y in b))
    if not norme_a or not norme_b:
        return 0.0
    return (produit / (norme_a * norme_b) + 1) / 2


class Locuteurs:
    """Regroupe les voix au fil de l'eau, sans savoir a qui elles sont.

    Chaque voix rencontree devient un centre ; une nouvelle empreinte
    rejoint le centre le plus proche, ou en ouvre un nouveau. Le centre se
    deplace ensuite vers ce qu'il vient d'absorber, ce qui le rend meilleur
    a mesure que la personne parle.

    Aucune identite n'est stockee : une empreinte ne permet pas de
    reconnaitre quelqu'un ailleurs, et rien n'est ecrit sur le disque.
    """

    def __init__(self, seuil: float = RESSEMBLANCE_MINIMALE):
        self.seuil = seuil
        self.centres: list[list[float]] = []
        self._vus: list[int] = []
        self._dernier: int = 0

    def attribuer(self, segment: Segment) -> int:
        """L'indice du locuteur de ce segment, a partir de 0."""
        empreinte = list(segment.empreinte)
        trop_court = (segment.fin - segment.debut) < DUREE_MINIMALE_EMPREINTE
        if not empreinte or (trop_court and self.centres):
            # Sans empreinte utilisable, on prolonge celui qui parlait :
            # couper une phrase en deux voix sur un « oui » de trois
            # dixiemes de seconde ne rend service a personne.
            return self._dernier

        meilleurs = [(ressemblance(centre, empreinte), i)
                     for i, centre in enumerate(self.centres)]
        if meilleurs:
            score, indice = max(meilleurs)
            if score >= self.seuil:
                self._absorber(indice, empreinte)
                self._dernier = indice
                return indice

        self.centres.append(empreinte)
        self._vus.append(1)
        self._dernier = len(self.centres) - 1
        return self._dernier

    def _absorber(self, indice: int, empreinte: list[float]) -> None:
        vus = self._vus[indice]
        centre = self.centres[indice]
        self.centres[indice] = [(c * vus + e) / (vus + 1)
                                for c, e in zip(centre, empreinte)]
        self._vus[indice] = vus + 1

    def __len__(self) -> int:
        return len(self.centres)


# ---------------------------------------------------------------------------
# Les noms
# ---------------------------------------------------------------------------

# « moi c'est Marion », « je m'appelle Pierre » : quelqu'un qui se presente
# donne son nom, et c'est la seule facon honnete d'en connaitre un. Le nom
# n'est jamais devine ailleurs.
_PRESENTATIONS = (
    re.compile(r"\bje m'appelle\s+(\w[\w'’-]*)", re.IGNORECASE),
    re.compile(r"\bmoi c'est\s+(\w[\w'’-]*)", re.IGNORECASE),
    re.compile(r"\bc'est\s+(\w[\w'’-]*)\s+(?:à l'appareil|qui parle)",
               re.IGNORECASE),
    re.compile(r"^\s*(\w[\w'’-]*)\s+(?:à l'appareil|au micro)\b",
               re.IGNORECASE),
)

# Ce qui suit « moi c'est » sans etre un prenom.
_PAS_UN_PRENOM = {
    "pas", "plus", "moi", "toi", "lui", "elle", "ça", "ca", "bon", "bien",
    "vrai", "faux", "clair", "sûr", "sur", "mieux", "pire", "juste",
    "comme", "que", "qui", "quoi", "tout", "rien", "le", "la", "les",
    "un", "une", "des", "mon", "ma", "mes", "ce", "cette", "ces",
}


def nom_annonce(texte: str) -> str | None:
    """Le prenom que quelqu'un vient de donner, s'il en a donne un."""
    for motif in _PRESENTATIONS:
        trouve = motif.search(texte)
        if not trouve:
            continue
        nom = trouve.group(1)
        if nom.lower() in _PAS_UN_PRENOM or len(nom) < 2:
            continue
        return nom[:1].upper() + nom[1:]
    return None


# ---------------------------------------------------------------------------
# La ponctuation
# ---------------------------------------------------------------------------

def _sans_accents(mot: str) -> str:
    decompose = unicodedata.normalize("NFD", mot.lower())
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def _interroge(phrase: list[Mot]) -> bool:
    """Cette phrase est-elle une question ?

    Elle l'est quand elle s'ouvre sur un mot interrogatif — sauf si ce mot
    ouvre en realite une subordonnee : « je sais pas pourquoi il est
    parti » n'est pas une question.
    """
    if not phrase:
        return False
    premiers = [_sans_accents(m.texte) for m in phrase[:3]]
    if premiers[0] in {"est-ce", "qu'est-ce"}:
        return True
    for rang, mot in enumerate(premiers):
        if mot not in {_sans_accents(x) for x in OUVERTURES_INTERROGATIVES}:
            continue
        if rang == 0:
            return True
        precedent = _sans_accents(phrase[rang - 1].texte)
        if precedent not in {_sans_accents(x) for x in AVANT_UNE_SUBORDONNEE}:
            return True
    return False


def ponctuer(mots: list[Mot] | tuple[Mot, ...]) -> str:
    """Rend le ruban de mots sous forme de phrases ponctuees.

    Les silences font tout le travail : un blanc long ferme la phrase, un
    blanc court pose une virgule. On n'invente aucune ponctuation que le
    rythme ne justifie — un compte rendu trop ponctue se lit plus mal qu'un
    compte rendu qui ne l'est pas assez.
    """
    mots = list(mots)
    if not mots:
        return ""

    phrases: list[list[Mot]] = [[]]
    virgules: set[int] = set()

    for rang, mot in enumerate(mots):
        courante = phrases[-1]
        if courante:
            blanc = mot.debut - courante[-1].fin
            relance = _sans_accents(mot.texte) in {
                _sans_accents(x) for x in RELANCES}
            if blanc >= SILENCE_DE_PHRASE or (
                    blanc >= SILENCE_DE_VIRGULE and relance) or \
                    len(courante) >= MOTS_AVANT_COUPURE:
                phrases.append([mot])
                continue
            if blanc >= SILENCE_DE_VIRGULE:
                virgules.add(rang - 1)
        courante.append(mot)

    rendu = []
    rang = 0
    for phrase in phrases:
        if not phrase:
            continue
        morceaux = []
        for mot in phrase:
            morceaux.append(mot.texte + ("," if rang in virgules else ""))
            rang += 1
        texte = " ".join(morceaux).rstrip(",")
        texte = texte[:1].upper() + texte[1:]
        rendu.append(texte + ("&nbsp;?" if _interroge(phrase) else "."))

    return " ".join(rendu).replace("&nbsp;?", " ?")


# ---------------------------------------------------------------------------
# L'assemblage
# ---------------------------------------------------------------------------

@dataclass
class Transcription:
    """Les tours de parole d'un enregistrement, mis en forme.

    Le correcteur est facultatif : sans lui, le texte reste tel que le
    moteur l'a entendu. Avec lui, il est relu comme le serait un message —
    accents, accords, homophones — et dans le meme respect du registre.
    """

    correcteur: object | None = None
    locuteurs: Locuteurs = field(default_factory=Locuteurs)
    tours: list[Tour] = field(default_factory=list)
    noms: dict[int, str] = field(default_factory=dict)

    def ajouter(self, segment: Segment) -> Tour | None:
        """Range un segment dans le tour de parole qui lui revient."""
        if not segment.mots:
            return None

        indice = self.locuteurs.attribuer(segment)
        texte = self._mettre_en_forme(segment)
        if not texte:
            return None

        nom = nom_annonce(texte)
        if nom and indice not in self.noms:
            self.noms[indice] = nom

        # Deux segments de suite du meme locuteur ne font qu'un tour : le
        # decoupage du moteur n'a pas de sens pour un lecteur.
        if self.tours and self.tours[-1].locuteur == self._nom(indice):
            precedent = self.tours[-1]
            precedent.texte = f"{precedent.texte} {texte}".strip()
            precedent.fin = segment.fin
            return precedent

        tour = Tour(self._nom(indice), segment.debut, segment.fin, texte)
        self.tours.append(tour)
        return tour

    def _mettre_en_forme(self, segment: Segment) -> str:
        texte = ponctuer(segment.mots)
        if self.correcteur is None or not texte:
            return texte
        try:
            return self.correcteur.corriger(texte)[0]
        except Exception:
            # Un compte rendu brut vaut mieux que pas de compte rendu.
            return texte

    def _nom(self, indice: int) -> str:
        return self.noms.get(indice, f"Personne {indice + 1}")

    def renommer(self, ancien: str, nouveau: str) -> None:
        """Donne un nom a une voix, apres coup.

        Les tours deja rendus changent avec elle : un compte rendu ou la
        moitie des repliques sont signees « Personne 2 » et l'autre moitie
        « Claire » ne serait pas relisible.
        """
        nouveau = (nouveau or "").strip()
        if not nouveau or ancien == nouveau:
            return
        for indice in range(len(self.locuteurs)):
            if self._nom(indice) == ancien:
                self.noms[indice] = nouveau
        for tour in self.tours:
            if tour.locuteur == ancien:
                tour.locuteur = nouveau

    @property
    def participants(self) -> list[str]:
        """Les voix entendues, dans l'ordre ou elles ont pris la parole."""
        vus: list[str] = []
        for tour in self.tours:
            if tour.locuteur not in vus:
                vus.append(tour.locuteur)
        return vus

    @property
    def duree(self) -> float:
        return self.tours[-1].fin if self.tours else 0.0

    def texte(self) -> str:
        """La transcription entiere, un tour par paragraphe."""
        return "\n\n".join(f"{tour.locuteur} : {tour.texte}"
                           for tour in self.tours)
