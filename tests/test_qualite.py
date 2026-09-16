# -*- coding: utf-8 -*-
"""La qualite du correcteur, mesuree et defendue.

Les autres tests verifient que chaque regle fait ce qu'elle annonce. Celui-ci
juge le resultat : sur un corpus de phrases fautives et de phrases correctes,
combien de fautes sont attrapees, et combien de phrases justes survivent.

La precision est le seuil dur : **aucune phrase correcte ne doit etre
abimee**. Une faute laissee passer se remarque a peine ; une phrase juste
corrompue se voit tout de suite, et fait desinstaller l'outil.

Le meme corpus se parcourt a la main, en couleurs :

    python outils/evaluer.py --detail
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "outils"))

from evaluer import FAUTES, INTOUCHABLES, evaluer  # noqa: E402

# En dessous, on a casse quelque chose : ces seuils ne descendent jamais.
RAPPEL_MINIMAL = 0.95


@pytest.fixture(scope="module")
def mesure(correcteur):
    return evaluer(correcteur)


def test_aucune_phrase_correcte_n_est_abimee(mesure):
    """Le seuil dur. Zero, pas « presque zero »."""
    abimees = "\n".join(f"  {phrase}\n    -> {obtenu}"
                        for phrase, obtenu in mesure["abimees"])
    assert not mesure["abimees"], f"phrases abimees :\n{abimees}"


def test_le_rappel_ne_baisse_pas(mesure):
    rappel = len(mesure["reussites"]) / len(FAUTES)
    manquees = "\n".join(f"  [{c}] {f}\n    attendu : {a}\n    obtenu  : {o}"
                         for c, f, a, o in mesure["echecs"])
    assert rappel >= RAPPEL_MINIMAL, (
        f"rappel tombe a {rappel:.0%}, seuil {RAPPEL_MINIMAL:.0%} :\n{manquees}"
    )


def test_le_corpus_reste_consequent():
    """Un corpus qu'on vide passerait tous les seuils."""
    assert len(FAUTES) >= 80
    assert len(INTOUCHABLES) >= 100


@pytest.mark.parametrize("categorie", ["accent", "accord", "apostrophe",
                                       "conjugaison", "frappe", "homophone"])
def test_chaque_categorie_est_representee(categorie):
    assert any(c == categorie for _, _, c in FAUTES)
