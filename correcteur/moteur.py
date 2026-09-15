# -*- coding: utf-8 -*-
"""Moteur de correction : orthographe, grammaire et garde-fous.

Le texte traverse trois couches, dans cet ordre :

0. **Vos remplacements.** Ce que vous avez appris au correcteur passe avant
   tout le reste : « ptetre » -> « peut-être », « cdlt » -> « cordialement ».
1. **Les zones intouchables.** Liens, blocs de code, mentions, emojis, argot,
   emphase volontaire : tout cela sort du circuit avant meme d'etre examine.
2. **La grammaire** (`grammaire.py`), qui regarde les mots voisins et tranche
   les homonymes : « sa va » -> « ça va », « ils on » -> « ils ont ».
3. **L'orthographe** (`lexique.py`), qui ne s'occupe que des mots absents du
   dictionnaire : « gateaux » -> « gâteaux ».

Deux principes gouvernent l'ensemble :

- On corrige les fautes, jamais le registre. « j'ai pas » est du francais
  parle correct, et aucune regle d'ici n'y touche.
- Mieux vaut sous-corriger que degrader. Une correction douteuse est ecartee :
  un message un peu fautif reste lisible, un message corrompu ne l'est plus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import grammaire, regles
from .lexique import CLASSE_ACCENT, Lexique, sans_accents

# Trois lettres identiques d'affilee : « ouiiii », « mdrrrr », « nooon ».
# C'est de l'emphase volontaire, jamais une faute de frappe.
_EMPHASE = re.compile(r"(.)\1{2,}", re.IGNORECASE)

_MOTIFS_PROTEGES = re.compile(
    "|".join(regles.MOTIFS_PROTEGES), re.IGNORECASE | re.DOTALL
)

_DEBUT_DE_PHRASE = re.compile(r"(?:^|[.!?…]\s+|\n\s*)$")

_PONCTUATION_FINALE = ".!?…:;,"


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


def _normaliser_mot(mot: str) -> str:
    """Pour comparer un mot au lexique protege."""
    return sans_accents(mot.strip(".,;:!?…\"'«»()[]{}-–—*_~")).lower()


def _zones_protegees(texte: str) -> list[tuple[int, int]]:
    """Intervalles du texte auxquels aucune correction ne doit toucher."""
    return [(m.start(), m.end()) for m in _MOTIFS_PROTEGES.finditer(texte)]


def _chevauche(debut: int, fin: int, zones: list[tuple[int, int]]) -> bool:
    return any(debut < z_fin and fin > z_debut for z_debut, z_fin in zones)


class Correcteur:
    """Corrige du francais en respectant le registre de l'auteur."""

    def __init__(self, lexique: Lexique | None = None,
                 regles_optionnelles: dict[str, bool] | None = None,
                 mots_perso: list[str] | None = None,
                 remplacements_perso: dict[str, str] | None = None):
        self.lexique = lexique if lexique is not None else Lexique()

        actives = dict(regles.REGLES_OPTIONNELLES)
        actives.update(regles_optionnelles or {})
        self.regles_ignorees = {nom for nom, active in actives.items() if not active}

        self.mots_proteges = set(regles.LEXIQUE_PROTEGE) | set(regles.LEXIQUE_ANGLAIS)
        for mot in mots_perso or []:
            self.mots_proteges.add(_normaliser_mot(mot))

        # Les cles sont comparees en minuscules et sans apostrophe typographique,
        # pour que « Ptetre » et « ptetre » trouvent la meme entree.
        self.remplacements = {
            cle.lower().replace("\u2019", "'"): valeur
            for cle, valeur in (remplacements_perso or {}).items()
            if cle.strip() and valeur.strip()
        }

    def prechauffer(self) -> None:
        """Lit les fichiers de donnees maintenant plutot qu'a la 1re correction."""
        self.lexique.charger()

    # -- protection ---------------------------------------------------------

    def _protege(self, mot: str) -> bool:
        """Ce mot doit-il rester tel quel, quoi qu'il arrive ?"""
        if _EMPHASE.search(mot):
            return True
        if _normaliser_mot(mot) in self.mots_proteges:
            return True
        # Sigles et emphase en capitales : « SNCF », « NON ».
        return len(mot) > 1 and mot.isupper()

    # -- orthographe --------------------------------------------------------

    def _connu(self, mot: str) -> bool:
        if self.lexique.connait(mot):
            return True
        # « j'ai », « qu'il » : l'elision se verifie a part.
        elision, noyau = grammaire.separer_clitique(mot)
        if elision:
            return not noyau or self.lexique.connait(noyau)
        return False

    def _apostrophe_manquante(self, mot: str) -> str | None:
        """« jai » -> « j'ai », « cest » -> « c'est », « daccord » -> « d'accord ».

        L'apostrophe est la touche la plus souvent sautee en tapant vite. Le
        mot colle n'existe jamais dans le dictionnaire, ce qui rend la
        correction sure : il suffit que la coupure donne deux morceaux
        connus.
        """
        for elision in grammaire.CLITIQUES:
            tete = elision.rstrip("'")
            if not mot.lower().startswith(tete) or len(mot) <= len(tete):
                continue
            reste = mot[len(tete):]
            # « ca » ne doit pas devenir « c'a » : il faut un vrai mot derriere.
            if len(reste) < 2:
                continue
            if self.lexique.connait(reste):
                return mot[: len(tete)] + "'" + reste
            # « cetait » -> « c'était » : le morceau de droite a le droit
            # d'avoir perdu ses accents, mais pas d'etre une faute de frappe,
            # sans quoi « subject » deviendrait « s'abject ».
            accentue = self.lexique.suggestion(reste, classe_max=CLASSE_ACCENT)
            if accentue is not None:
                return mot[: len(tete)] + "'" + accentue
        return None

    def _orthographe(self, mot: str) -> str | None:
        """Le mot correctement orthographie, s'il ne fait aucun doute."""
        if len(mot) < 2:
            # Une lettre isolee est une abreviation (« c pas grave »), pas un
            # mot a corriger.
            return None

        elision, noyau = grammaire.separer_clitique(mot)

        # Un mot capitalise au milieu d'une phrase est un nom propre : on veut
        # bien lui rendre ses accents, pas le remplacer par un autre mot.
        prudent = mot[:1].isupper()

        # Ordre de confiance : les accents oublies d'abord, l'apostrophe
        # oubliee ensuite, la faute de frappe en dernier. « cest » deviendrait
        # « est » si on laissait la distance d'edition passer la premiere.
        accents = self.lexique.suggestion(noyau, classe_max=CLASSE_ACCENT)
        if accents is not None:
            return elision + accents

        if not elision:
            apostrophe = self._apostrophe_manquante(mot)
            if apostrophe is not None:
                return apostrophe

        if prudent:
            return None

        frappe = self.lexique.suggestion(noyau)
        return elision + frappe if frappe is not None else None

    # -- une passe ----------------------------------------------------------

    def _passe(self, texte: str) -> tuple[str, list[Correction]]:
        jetons = grammaire.decouper(texte)
        zones = _zones_protegees(texte)
        propositions: list[Correction] = []
        traites: set[int] = set()

        def utilisable(indices: range, debut: int, fin: int) -> bool:
            if _chevauche(debut, fin, zones):
                return False
            return not any(self._protege(jetons[i].texte) for i in indices)

        # -- vos remplacements : ils passent avant tout, y compris avant les
        #    protections, puisque c'est vous qui les avez demandes.
        if self.remplacements:
            for i, jeton in enumerate(jetons):
                if _chevauche(jeton.debut, jeton.fin, zones):
                    continue
                remplacement = self.remplacements.get(
                    jeton.texte.lower().replace("\u2019", "'")
                )
                if remplacement is None or remplacement == jeton.texte:
                    continue
                propositions.append(
                    Correction(jeton.debut, jeton.fin, jeton.texte,
                               grammaire.appliquer_casse(jeton.texte, remplacement),
                               "REMPLACEMENT_PERSO",
                               "remplacement enregistre dans votre dictionnaire")
                )
                traites.add(i)

        # -- grammaire : elle voit le contexte, elle passe en premier.
        for suggestion in grammaire.analyser(
            texte, jetons, self.lexique, self.regles_ignorees
        ):
            indices = range(suggestion.index, suggestion.index + suggestion.portee)
            if traites.intersection(indices):
                continue
            debut = jetons[suggestion.index].debut
            fin = jetons[indices[-1]].fin
            if not utilisable(indices, debut, fin):
                continue
            propositions.append(
                Correction(debut, fin, texte[debut:fin], suggestion.texte,
                           suggestion.regle, suggestion.message)
            )
            traites.update(indices)

        # -- orthographe : uniquement les mots qu'aucun dictionnaire ne connait.
        for i, jeton in enumerate(jetons):
            if i in traites or not utilisable(range(i, i + 1), jeton.debut, jeton.fin):
                continue
            if self._connu(jeton.texte):
                continue
            remplacement = self._orthographe(jeton.texte)
            if remplacement is None or remplacement == jeton.texte:
                continue
            propositions.append(
                Correction(jeton.debut, jeton.fin, jeton.texte, remplacement,
                           "ORTHOGRAPHE", "mot absent du dictionnaire")
            )

        return self._appliquer(texte, propositions)

    @staticmethod
    def _appliquer(texte: str, propositions: list[Correction]):
        """Reecrit le texte de la fin vers le debut, pour ne pas decaler les offsets."""
        propositions.sort(key=lambda c: c.debut, reverse=True)
        appliquees: list[Correction] = []
        derniere_position = len(texte) + 1

        for proposition in propositions:
            if proposition.fin > derniere_position:
                continue
            texte = texte[:proposition.debut] + proposition.apres + texte[proposition.fin:]
            appliquees.append(proposition)
            derniere_position = proposition.debut

        appliquees.reverse()
        return texte, appliquees

    # -- regles optionnelles de mise en forme --------------------------------

    def _mise_en_forme(self, texte: str) -> tuple[str, list[Correction]]:
        corrections: list[Correction] = []

        if "MAJUSCULE_PHRASE" not in self.regles_ignorees:
            for jeton in reversed(grammaire.decouper(texte)):
                premiere = jeton.texte[:1]
                if not premiere.islower():
                    continue
                if not _DEBUT_DE_PHRASE.search(texte[:jeton.debut]):
                    continue
                corrections.append(
                    Correction(jeton.debut, jeton.debut + 1, premiere,
                               premiere.upper(), "MAJUSCULE_PHRASE",
                               "majuscule en debut de phrase")
                )
                texte = texte[:jeton.debut] + premiere.upper() + texte[jeton.debut + 1:]

        if "PONCTUATION_POINT" not in self.regles_ignorees:
            corps = texte.rstrip()
            if corps and corps[-1] not in _PONCTUATION_FINALE:
                position = len(corps)
                corrections.append(
                    Correction(position, position, "", ".", "PONCTUATION_POINT",
                               "point final manquant")
                )
                texte = corps + "." + texte[position:]

        corrections.reverse()
        return texte, corrections

    # -- entree publique ----------------------------------------------------

    def corriger(self, texte: str, passes: int = 2,
                 mise_en_forme: bool = True) -> tuple[str, list[Correction]]:
        """Corrige `texte` et renvoie (texte_corrige, corrections_appliquees).

        Deux passes par defaut : corriger « ils on manger » en « ils ont
        manger » debloque la regle du participe, que la premiere passe ne
        pouvait pas voir.

        `mise_en_forme` couvre la majuscule de debut de phrase et le point
        final. La correction au fil de la frappe la desactive : une phrase en
        cours d'ecriture n'est pas encore finie, et lui coller un point a
        chaque espace serait insupportable.
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

        if mise_en_forme:
            corps, corrections = self._mise_en_forme(corps)
            toutes.extend(corrections)

        return marge_gauche + corps + marge_droite, toutes


def construire(regles_optionnelles: dict[str, bool] | None = None,
               mots_perso: list[str] | None = None,
               remplacements_perso: dict[str, str] | None = None) -> Correcteur:
    """Le correcteur pret a l'emploi, dictionnaire compris."""
    return Correcteur(Lexique(), regles_optionnelles, mots_perso, remplacements_perso)


def depuis_config(config: dict, lexique: Lexique | None = None) -> Correcteur:
    """Le correcteur decrit par un fichier de reglages."""
    return Correcteur(
        lexique if lexique is not None else Lexique(),
        regles_optionnelles=config.get("regles_optionnelles"),
        mots_perso=config.get("mots_perso"),
        remplacements_perso=config.get("remplacements_perso"),
    )
