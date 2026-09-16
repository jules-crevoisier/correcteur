# -*- coding: utf-8 -*-
"""Tests de la table des genres.

Ce sont des faits de francais, qu'on ecrit en clair. Le vrai risque d'une
table ecrite a la main, c'est la faute d'inattention : ces tests en sont le
garde-fou, et ils valent relecture.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import genres  # noqa: E402


@pytest.mark.parametrize("nom", [
    # La liste
    "voiture", "porte", "table", "chaise", "fleur", "route", "maison",
    "eau", "peau", "nuit", "main", "voix", "fois", "mer", "dent",
    # Les terminaisons
    "nation", "question", "décision", "qualité", "société", "vitesse",
    "richesse", "fourchette", "chance", "patience", "raison", "saison",
    "voiture", "habitude", "salade", "vendeuse", "rivière", "boulangerie",
    "partie", "réunion",
])
def test_ce_qui_est_feminin(nom):
    assert genres.genre(nom) == genres.FEMININ, nom


@pytest.mark.parametrize("nom", [
    # La liste
    "jour", "soir", "matin", "temps", "travail", "pays", "ciel",
    "chien", "chat", "cheval", "pain", "train", "yeux", "cheveux", "gens",
    # Les terminaisons
    "moment", "gouvernement", "tourisme", "réalisme", "miroir", "couloir",
    "bureau", "chapeau", "journal", "hôpital", "ordinateur", "papier",
    "village", "téléphone",
])
def test_ce_qui_est_masculin(nom):
    assert genres.genre(nom) == genres.MASCULIN, nom


@pytest.mark.parametrize("nom, attendu", [
    # Les exceptions nommees : sans elles, la terminaison se tromperait.
    ("jument", genres.FEMININ),        # -ment est masculin
    ("silence", genres.MASCULIN),      # -ence est feminin
    ("eau", genres.FEMININ),           # -eau est masculin
    ("peau", genres.FEMININ),
    ("poisson", genres.MASCULIN),      # -sson est feminin
    ("squelette", genres.MASCULIN),    # -ette est feminin
    ("murmure", genres.MASCULIN),      # -ure est feminin
    ("stade", genres.MASCULIN),        # -ade est feminin
    ("incendie", genres.MASCULIN),     # -ie est feminin
    ("page", genres.FEMININ),          # -age est masculin
    ("image", genres.FEMININ),
    ("plage", genres.FEMININ),
])
def test_les_exceptions_sont_nommees(nom, attendu):
    assert genres.genre(nom) == attendu, nom


@pytest.mark.parametrize("mot", [
    "truc", "machin", "zbeul", "bidule", "",
    # Ceux-la changent de sens avec leur genre : une table a une colonne se
    # tromperait une fois sur deux.
    "livre", "poste", "tour", "mode", "voile", "somme",
])
def test_ce_qu_on_ne_sait_pas(mot):
    """Ne rien savoir est une reponse : elle fait taire les regles."""
    assert genres.genre(mot) is None


def test_la_liste_l_emporte_sur_la_terminaison():
    """« page » est feminin, et n'a pas a se defendre contre « -age »."""
    assert genres.genre("page") == genres.FEMININ
    assert genres.genre("village") == genres.MASCULIN


def test_aucun_mot_n_est_dans_les_deux_listes():
    communs = set(genres._FEMININS) & set(genres._MASCULINS)
    assert not communs, sorted(communs)
