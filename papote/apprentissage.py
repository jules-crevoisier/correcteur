# -*- coding: utf-8 -*-
"""Ce que Papote retient de vos habitudes.

Un correcteur qu'il faut configurer a la main reste mal configure. Celui-ci
observe deux choses, et en tire deux conclusions :

    vous annulez trois fois la meme correction sur un mot
        -> ce mot est le votre, il n'y touche plus ;

    vous annulez trois fois la meme regle, sur des mots differents
        -> cette regle vous derange, il propose de l'eteindre.

Il compte aussi les corrections appliquees, ce qui donne l'onglet « Vos
fautes » : savoir qu'on ecrit « malgres » vingt-trois fois par mois est le
genre de chose qu'on ne decouvre pas tout seul.

Tout cela vit dans un fichier a cote des reglages, sur votre machine, et se
vide d'un bouton. Rien n'est envoye nulle part. Le fichier contient des mots
que vous avez ecrits : c'est le prix de l'apprentissage, et c'est pourquoi il
s'efface aussi facilement.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Nombre d'annulations avant que Papote en tire une lecon.
SEUIL = 3

# Nombre d'entrees conservees dans le fichier : de quoi nourrir les
# statistiques sans le laisser grossir indefiniment.
MEMOIRE = 500


@dataclass(frozen=True)
class Lecon:
    """Ce que Papote propose de changer, ayant observe ce qu'il a observe."""

    genre: str      # « mot » ou « regle »
    valeur: str
    compte: int

    def __str__(self) -> str:
        if self.genre == "mot":
            return f"« {self.valeur} » ne sera plus corrigé."
        return f"la règle {self.valeur} vous dérange."


@dataclass
class Journal:
    """Les compteurs, et ce qu'on en deduit."""

    corrections: Counter = field(default_factory=Counter)
    annulations_mot: Counter = field(default_factory=Counter)
    annulations_regle: Counter = field(default_factory=Counter)
    seuil: int = SEUIL
    modifie: bool = False

    # -- observation --------------------------------------------------------

    def correction_appliquee(self, avant: str, apres: str) -> None:
        """Compte une correction, sans garder ce qui a ete tape.

        Seule la forme **corrigee** entre ici. C'est elle que la page « Vos
        fautes » montre : les mots que vous ratez le plus souvent.

        Le compteur retenait la paire — « jai → j'ai » —, ce qui disait plus
        de choses et coutait trop cher. Papote ne corrige que vers un mot
        qu'il connait : le cote droit est toujours du francais. Le cote
        gauche, lui, est par definition ce que le dictionnaire ignore, et
        rien ne distingue « jai » d'un mot de passe mal tape dans la
        mauvaise fenetre. Or ce fichier survit a la session.

        Le filtre pose en amont refusait donc la paire des que le cote
        gauche etait inconnu — c'est-a-dire presque toujours, puisque c'est
        la faute. La page restait vide. Ne garder que la forme juste tient
        la promesse **et** remplit la page.
        """
        forme = apres.strip()
        if not avant.strip() or not forme:
            return
        self.corrections[forme] += 1
        self.modifie = True
        self._elaguer()

    def _elaguer(self) -> None:
        """Ramene les compteurs a ce qu'on garde de toute facon.

        Le fichier ne retient que les `MEMOIRE` premieres entrees : c'est
        `en_dictionnaire` qui coupe. En memoire, rien ne coupait — et Papote
        tourne des semaines d'affilee. Le compteur enflait pour des paires
        vues une seule fois, qui ne seraient jamais ecrites nulle part.

        On laisse de la marge avant d'elaguer : couper a chaque correction
        ferait perdre des entrees qui montaient.
        """
        if len(self.corrections) <= MEMOIRE * 4:
            return
        self.corrections = Counter(dict(self.corrections.most_common(MEMOIRE)))

    def correction_annulee(self, mot: str, regle: str = "") -> list[Lecon]:
        """Enregistre un refus, et renvoie ce qu'il faut en conclure."""
        mot = mot.strip()
        lecons = []

        if mot:
            self.annulations_mot[mot.lower()] += 1
            compte = self.annulations_mot[mot.lower()]
            if compte == self.seuil:
                lecons.append(Lecon("mot", mot, compte))

        if regle and regle != "ORTHOGRAPHE":
            self.annulations_regle[regle] += 1
            compte = self.annulations_regle[regle]
            if compte == self.seuil:
                lecons.append(Lecon("regle", regle, compte))

        self.modifie = True
        return lecons

    def oublier_mot(self, mot: str) -> None:
        """Le mot est appris : son compteur n'a plus lieu d'etre."""
        if self.annulations_mot.pop(mot.strip().lower(), None) is not None:
            self.modifie = True

    # -- consultation -------------------------------------------------------

    def fautes_frequentes(self, combien: int = 20) -> list[tuple[str, int]]:
        """Vos corrections les plus repetees, de la plus a la moins frequente."""
        return self.corrections.most_common(combien)

    def total_corrections(self) -> int:
        return sum(self.corrections.values())

    def vider(self) -> None:
        self.corrections.clear()
        self.annulations_mot.clear()
        self.annulations_regle.clear()
        self.modifie = True

    # -- fichier ------------------------------------------------------------

    def en_dictionnaire(self) -> dict:
        return {
            "corrections": dict(self.corrections.most_common(MEMOIRE)),
            "annulations_mot": dict(self.annulations_mot.most_common(MEMOIRE)),
            "annulations_regle": dict(self.annulations_regle),
        }

    @classmethod
    def depuis_dictionnaire(cls, donnees: dict, seuil: int = SEUIL) -> "Journal":
        def compteur(cle):
            valeurs = donnees.get(cle) or {}
            if not isinstance(valeurs, dict):
                return Counter()
            return Counter({
                str(mot): int(compte) for mot, compte in valeurs.items()
                if isinstance(compte, int) and compte > 0
            })

        return cls(
            corrections=compteur("corrections"),
            annulations_mot=compteur("annulations_mot"),
            annulations_regle=compteur("annulations_regle"),
            seuil=seuil,
        )

    def enregistrer(self, chemin: Path) -> None:
        if not self.modifie:
            return
        chemin.parent.mkdir(parents=True, exist_ok=True)
        provisoire = chemin.with_suffix(".json.tmp")
        with provisoire.open("w", encoding="utf-8") as f:
            json.dump(self.en_dictionnaire(), f, ensure_ascii=False, indent=2)
        provisoire.replace(chemin)
        self.modifie = False


def chemin_journal() -> Path:
    from .config import dossier_config

    return dossier_config() / "apprentissage.json"


def charger(chemin: Path | None = None, seuil: int = SEUIL) -> Journal:
    chemin = chemin if chemin is not None else chemin_journal()
    try:
        with chemin.open(encoding="utf-8") as f:
            return Journal.depuis_dictionnaire(json.load(f), seuil)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        # Fichier absent ou abime : on repart de zero, ce n'est qu'un carnet
        # d'observations.
        return Journal(seuil=seuil)
