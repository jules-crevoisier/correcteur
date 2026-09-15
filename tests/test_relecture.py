# -*- coding: utf-8 -*-
"""Tests de la relecture : voir ce qui changerait, et choisir."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote.relecture import changements, composer  # noqa: E402


def test_deux_textes_identiques_ne_changent_rien():
    assert changements("bonjour", "bonjour") == []


def test_chaque_difference_est_un_changement():
    liste = changements("sa va bien", "ça va bien")
    assert [(c.avant, c.apres) for c in liste] == [("sa", "ça")]


def test_les_changements_sont_lisibles():
    liste = changements("ils on mangé", "ils ont mangé")
    assert str(liste[0]) == "on → ont"


def test_tout_accepter_redonne_le_texte_corrige():
    original, corrige = "sa va, jai faim", "ça va, j'ai faim"
    assert composer(original, corrige, changements(original, corrige)) == corrige


def test_tout_refuser_redonne_le_texte_d_origine():
    original, corrige = "sa va, jai faim", "ça va, j'ai faim"
    liste = changements(original, corrige)
    for changement in liste:
        changement.accepte = False
    assert composer(original, corrige, liste) == original


def test_on_peut_n_en_accepter_qu_un():
    original, corrige = "sa va, jai faim", "ça va, j'ai faim"
    liste = changements(original, corrige)
    liste[0].accepte = False
    assert composer(original, corrige, liste) == "sa va, j'ai faim"


def test_un_ajout_se_choisit_aussi():
    """La ponctuation ajoutee est un changement comme un autre."""
    original, corrige = "bonjour", "Bonjour."
    liste = changements(original, corrige)
    assert liste
    for changement in liste:
        changement.accepte = False
    assert composer(original, corrige, liste) == original


def test_les_sauts_de_ligne_sont_preserves():
    original = "salut,\nsa va ?"
    corrige = "salut,\nça va ?"
    assert composer(original, corrige, changements(original, corrige)) == corrige


def test_sur_un_vrai_texte(correcteur):
    original = "salut sa va ? jai pas compris se que tu dit"
    corrige = correcteur.corriger(original)[0]
    liste = changements(original, corrige)
    assert len(liste) >= 4
    assert composer(original, corrige, liste) == corrige
