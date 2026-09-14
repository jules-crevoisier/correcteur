# -*- coding: utf-8 -*-
"""Tests de bout en bout contre le vrai LanguageTool.

Ces tests demarrent un serveur Java et sont donc lents ; ils sont ignores
si LanguageTool n'est pas installable dans l'environnement. Ce sont eux qui
attestent du comportement reel, la ou test_moteur.py verifie la logique.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def correcteur():
    moteur = pytest.importorskip("correcteur.moteur")
    try:
        return moteur.construire()
    except Exception as e:  # Java absent, telechargement impossible...
        pytest.skip(f"LanguageTool indisponible : {e}")


# Tournures orales sans faute : l'outil doit les laisser strictement intactes.
INTOUCHABLES = [
    "j'ai pas compris ce que tu voulais dire",
    "faut que j'y aille",
    "y a rien à faire",
    "je peux pas venir dsl",
    "tkt jsp encore",
    "mdrrrr c'est trop drôle",
    "c'est pas grave, on se voit demain",
    "t'as vu le message que je t'ai envoyé ?",
]

# (texte fautif, texte attendu apres correction)
ATTENDUS = [
    ("je sais pas si sa va marcher", "je sais pas si ça va marcher"),
    ("c'est vraiment nimporte quoi", "c'est vraiment n'importe quoi"),
    ("Les filles sont venu hier", "Les filles sont venues hier"),
    ("ils on mangé tout les gateaux", "ils ont mangé tous les gâteaux"),
    ("ca ma pris 2 heures", "ça m'a pris 2 heures"),
    ("tu veut quelque chose ?", "tu veux quelque chose ?"),
    # Les accents se corrigent sans que la tournure orale bouge.
    ("faut que j'y aille la", "faut que j'y aille là"),
    ("y a rien a faire", "y a rien à faire"),
    ("mdrrrr c'est trop drole", "mdrrrr c'est trop drôle"),
]


@pytest.mark.parametrize("texte", INTOUCHABLES)
def test_le_francais_parle_est_preserve(correcteur, texte):
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == texte, f"corrections indues : {[str(c) for c in corrections]}"


@pytest.mark.parametrize("texte,attendu", ATTENDUS)
def test_les_vraies_fautes_sont_corrigees(correcteur, texte, attendu):
    assert correcteur.corriger(texte)[0] == attendu


def test_les_liens_sont_intacts(correcteur):
    texte = "regarde https://exemple.fr/a_b-c c'est enorme"
    corrige, _ = correcteur.corriger(texte)
    assert "https://exemple.fr/a_b-c" in corrige
    assert "énorme" in corrige


def test_aucune_degradation_sur_texte_deja_correct(correcteur):
    texte = "Je suis passé te voir hier soir, mais tu n'étais pas là."
    assert correcteur.corriger(texte)[0] == texte
