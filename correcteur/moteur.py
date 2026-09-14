# -*- coding: utf-8 -*-
"""Moteur de correction : LanguageTool + garde-fous maison.

LanguageTool fait le travail linguistique lourd (accords, conjugaison,
homonymes, orthographe). Ce module decide ensuite lesquelles de ses
suggestions meritent d'etre appliquees.

Deux principes :

1. On corrige les fautes, jamais le registre. « j'ai pas » est du francais
   parle correct ; c'est le module `regles` qui neutralise cette couche.
2. Mieux vaut sous-corriger que degrader. Une suggestion douteuse est
   ecartee : un message un peu fautif reste lisible, un message corrompu
   par une mauvaise correction ne l'est plus.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from . import regles

# Trois lettres identiques d'affilee : « ouiiii », « mdrrrr », « nooon ».
# C'est de l'emphase volontaire, jamais une faute de frappe.
_EMPHASE = re.compile(r"(.)\1{2,}", re.IGNORECASE)

_MOTIFS_PROTEGES = re.compile(
    "|".join(regles.MOTIFS_PROTEGES), re.IGNORECASE | re.DOTALL
)

# Longueur maximale d'un suffixe ajoute par une correction d'accord
# (« somme » -> « sommes », « chelou » -> « chelous », « venu » -> « venues »).
_SUFFIXE_MAX = 3


@dataclass(frozen=True)
class Correction:
    """Une modification appliquee au texte."""

    debut: int
    fin: int
    avant: str
    apres: str
    regle: str
    message: str

    def __str__(self) -> str:
        return f"{self.avant} → {self.apres}"


def _sans_accents(texte: str) -> str:
    texte = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def _normaliser_mot(mot: str) -> str:
    """Pour comparer un mot au lexique protege."""
    return _sans_accents(mot.strip(".,;:!?…\"'«»()[]{}-–—*_~"))


def _formes_comparables(texte: str) -> set[str]:
    """Formes normalisees d'un fragment, pour juger si un changement est cosmetique.

    Les accents et les apostrophes disparaissent ; le trait d'union est teste
    a la fois comme une soudure et comme une espace. Les espaces, eux, sont
    conserves : c'est precisement le decoupage en mots qu'on veut surveiller.
    """
    base = _sans_accents(texte).replace("'", "").replace("’", "")
    return {
        re.sub(r"\s+", " ", base.replace("-", "")).strip(),
        re.sub(r"\s+", " ", base.replace("-", " ")).strip(),
    }


def _zones_protegees(texte: str) -> list[tuple[int, int]]:
    """Intervalles du texte auxquels aucune correction ne doit toucher."""
    return [(m.start(), m.end()) for m in _MOTIFS_PROTEGES.finditer(texte)]


def _chevauche(debut: int, fin: int, zones: Iterable[tuple[int, int]]) -> bool:
    return any(debut < z_fin and fin > z_debut for z_debut, z_fin in zones)


def _changement_cosmetique(fragment: str, remplacement: str) -> bool:
    """Vrai si le remplacement ne fait qu'accentuer, apostropher ou accorder.

    Ce test est le garde-fou central. LanguageTool degrade surtout les
    fragments de plusieurs mots, qu'il re-decoupe : « ta fini » -> « te finir »,
    « les enfant » -> « l'enfant », « ceter » -> « ce ter ». Ces re-decoupages
    changent le squelette du fragment ; les vraies corrections ne le changent
    pas (« ma dit » -> « m'a dit », « Est ce » -> « Est-ce ») ou se contentent
    d'ajouter une terminaison (« nous somme » -> « nous sommes »).
    """
    formes_frag = _formes_comparables(fragment)
    formes_rempl = _formes_comparables(remplacement)

    # Purement typographique : accents, apostrophes, traits d'union.
    if formes_frag & formes_rempl:
        return True

    # Ajout d'une terminaison d'accord, a la fin du dernier mot.
    for f in formes_frag:
        for r in formes_rempl:
            if r.startswith(f) and 0 < len(r) - len(f) <= _SUFFIXE_MAX:
                return True
    return False


class Correcteur:
    """Corrige du francais en respectant le registre de l'auteur."""

    def __init__(self, outil, regles_optionnelles: dict[str, bool] | None = None):
        """
        `outil` expose `.check(texte)` a la maniere de language_tool_python.
        L'injecter plutot que le construire ici rend le moteur testable sans
        demarrer un serveur Java.
        """
        self.outil = outil
        actives = dict(regles.REGLES_OPTIONNELLES)
        actives.update(regles_optionnelles or {})
        # Une regle optionnelle laissee a False rejoint la liste noire.
        self.regles_ignorees = set(regles.REGLES_IGNOREES) | {
            nom for nom, active in actives.items() if not active
        }
        self._cache_lexique: dict[str, bool] = {}

    # -- validation lexicale ------------------------------------------------

    def _mot_existe(self, mot: str) -> bool:
        """Le mot figure-t-il au dictionnaire ?

        LanguageTool propose parfois des formes qui n'existent pas
        (« mangé » -> « mangait », « garé » -> « garees »). On lui soumet le
        mot isole pour trancher. Le resultat est mis en cache : la meme
        poignee de mots revient sans cesse.
        """
        cle = mot.lower()
        if cle in self._cache_lexique:
            return self._cache_lexique[cle]

        # Un mot sans lettre (ponctuation, chiffres) n'a rien a valider.
        if not any(c.isalpha() for c in mot):
            self._cache_lexique[cle] = True
            return True

        try:
            fautes = [
                m for m in self.outil.check(mot)
                if (getattr(m, "category", "") or "") == "TYPOS"
            ]
            existe = not fautes
        except Exception:
            # En cas de souci serveur, on accorde le benefice du doute.
            existe = True

        self._cache_lexique[cle] = existe
        return existe

    def _remplacement_valide(self, fragment: str, remplacement: str) -> bool:
        """Le remplacement est-il assez sur pour etre applique sans demander ?"""
        if _changement_cosmetique(fragment, remplacement):
            return True

        # Au-dela du cosmetique, on n'accepte qu'un mot unique remplace par un
        # mot unique. Tout changement du nombre de mots est un re-decoupage.
        if len(fragment.split()) != 1 or len(remplacement.split()) != 1:
            return False

        return self._mot_existe(remplacement)

    # -- filtrage -----------------------------------------------------------

    def _retenir(self, match, texte: str, zones: list[tuple[int, int]]) -> bool:
        """Decide si une suggestion de LanguageTool merite d'etre appliquee."""
        regle = getattr(match, "rule_id", "") or ""
        categorie = getattr(match, "category", "") or ""

        remplacements = getattr(match, "replacements", None) or []
        if not remplacements:
            return False

        # -- couche 1 : le registre n'est pas une faute
        if regle in self.regles_ignorees:
            return False
        if categorie in regles.CATEGORIES_IGNOREES:
            return False

        debut = match.offset
        fin = debut + match.error_length
        if _chevauche(debut, fin, zones):
            return False

        fragment = texte[debut:fin]
        remplacement = remplacements[0]

        # -- couche 2 : ce que l'auteur a ecrit exprès
        if _EMPHASE.search(fragment):
            return False
        if _normaliser_mot(fragment) in regles.LEXIQUE_PROTEGE:
            return False

        # -- couche 3 : ne pas degrader
        if not remplacement.strip():
            return False
        if not self._remplacement_valide(fragment, remplacement):
            return False

        return True

    # -- application --------------------------------------------------------

    def _passe(self, texte: str) -> tuple[str, list[Correction]]:
        """Une passe de correction. Renvoie le texte corrige et le journal."""
        zones = _zones_protegees(texte)
        retenus = [m for m in self.outil.check(texte) if self._retenir(m, texte, zones)]

        # De la fin vers le debut : les offsets des corrections restantes
        # ne bougent pas au fur et a mesure qu'on modifie le texte.
        retenus.sort(key=lambda m: m.offset, reverse=True)

        corrections: list[Correction] = []
        derniere_position = len(texte) + 1
        for m in retenus:
            debut, fin = m.offset, m.offset + m.error_length
            # Deux regles peuvent viser la meme zone ; la premiere gagne.
            if fin > derniere_position:
                continue
            remplacement = m.replacements[0]
            corrections.append(
                Correction(
                    debut=debut,
                    fin=fin,
                    avant=texte[debut:fin],
                    apres=remplacement,
                    regle=getattr(m, "rule_id", ""),
                    message=getattr(m, "message", ""),
                )
            )
            texte = texte[:debut] + remplacement + texte[fin:]
            derniere_position = debut

        corrections.reverse()
        return texte, corrections

    def corriger(self, texte: str, passes: int = 2) -> tuple[str, list[Correction]]:
        """Corrige `texte` et renvoie (texte_corrige, corrections_appliquees).

        Deux passes par defaut : corriger « ils on mange » en « ils ont mange »
        debloque l'analyse du verbe, que la premiere passe ne pouvait pas voir.
        """
        if not texte or not texte.strip():
            return texte, []

        # Les espaces de bord comptent au collage : on les met de cote et on
        # les restitue tels quels.
        marge_gauche = texte[: len(texte) - len(texte.lstrip())]
        marge_droite = texte[len(texte.rstrip()):]
        corps = texte.strip()

        toutes: list[Correction] = []
        for _ in range(max(1, passes)):
            corps, corrections = self._passe(corps)
            if not corrections:
                break
            toutes.extend(corrections)

        return marge_gauche + corps + marge_droite, toutes


def construire(langue: str = "fr", regles_optionnelles: dict[str, bool] | None = None):
    """Demarre LanguageTool en local et renvoie un Correcteur pret a l'emploi."""
    import language_tool_python

    outil = language_tool_python.LanguageTool(langue)
    return Correcteur(outil, regles_optionnelles)
