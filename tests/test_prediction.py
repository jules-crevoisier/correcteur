# -*- coding: utf-8 -*-
"""Tests de la prediction du mot en cours.

La prediction n'a pas les memes exigences que la correction. Se tromper y
est sans gravite — on continue a taper, la proposition disparait. Ce qui
compte, c'est qu'elle ne propose rien quand elle ne sait pas : une liste
de trois mots au hasard sous chaque debut de mot serait insupportable.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote.prediction import LONGUEUR_MINIMALE, Predicteur  # noqa: E402


@pytest.fixture(scope="module")
def predicteur(lexique):
    return Predicteur(lexique)


# -- ce qu'elle trouve ------------------------------------------------------

@pytest.mark.parametrize("debut,attendu", [
    ("anni", "anniversaire"),
    ("bonj", "bonjour"),
    ("merc", "merci"),
    ("deman", "demande"),
    ("impo", "importe"),
])
def test_un_debut_de_mot_trouve_sa_suite(predicteur, debut, attendu):
    assert attendu in predicteur.completer(debut)


def test_les_mots_a_apostrophe_et_trait_d_union_sont_proposes(predicteur):
    """Ce sont justement les plus penibles a taper en entier."""
    assert "aujourd'hui" in predicteur.completer("aujou")


def test_les_accents_ne_sont_pas_exiges(predicteur):
    """Personne ne tape les accents quand il est pressé."""
    assert "événement" in predicteur.completer("evene")
    assert "déjà" in predicteur.completer("deja")


def test_la_casse_du_debut_est_gardee(predicteur):
    assert "Anniversaire" in predicteur.completer("Anni")


# -- ce qu'elle refuse ------------------------------------------------------

def test_deux_lettres_ne_designent_rien(predicteur):
    """« be » ouvre sur « bien », « beaucoup », « besoin », et cent autres."""
    for debut in ("b", "be", "qu", "a"):
        assert predicteur.completer(debut) == [], debut


def test_un_mot_deja_courant_ne_se_fait_pas_completer(predicteur):
    """Qui a tapé « par » voulait « par », pas « parce »."""
    assert predicteur.completer("par") == []
    assert predicteur.completer("bon") == []


def test_le_mot_deja_ecrit_n_est_pas_propose(predicteur):
    """Compléter « bonjour » par « bonjour » n'aide personne."""
    assert "bonjour" not in predicteur.completer("bonjour")


def test_un_debut_qui_n_est_pas_un_mot_ne_propose_rien(predicteur):
    for debut in ("123", "a1b", "!!!", "  "):
        assert predicteur.completer(debut) == [], debut


def test_un_debut_inconnu_ne_propose_rien(predicteur):
    assert predicteur.completer("zbeulotr") == []


# -- ce que la touche de validation ecrirait --------------------------------

def test_la_suite_est_ce_qu_il_reste_a_taper(predicteur):
    assert predicteur.suite("anni") == "versaire"
    assert predicteur.suite("bonj") == "our"


def test_une_suite_qui_demanderait_d_effacer_est_refusee(predicteur):
    """« deja » -> « déjà » : la prediction n'efface jamais.

    Elle peut le proposer a l'affichage, mais la touche de validation ne
    fait qu'ajouter des lettres a droite — reculer sur un accent deja tape
    demanderait de savoir ce qu'il y a a l'ecran, ce qu'elle ignore.
    """
    assert "déjà" in predicteur.completer("deja")
    assert predicteur.suite("deja") is None


def test_sans_proposition_il_n_y_a_rien_a_ecrire(predicteur):
    assert predicteur.suite("par") is None
    assert predicteur.suite("zz") is None


# -- l'index ----------------------------------------------------------------

def test_l_index_ne_se_construit_qu_a_la_demande(lexique):
    """Qui n'emploie jamais la prediction ne doit pas la payer."""
    predicteur = Predicteur(lexique)
    assert predicteur._index is None
    predicteur.completer("anni")
    assert predicteur._index is not None


def test_l_index_ne_retient_que_des_mots_utilisables(predicteur):
    for squelette, mot in predicteur.index:
        assert len(mot) > LONGUEUR_MINIMALE
        assert mot[:1].islower()
        assert squelette == squelette.lower()


def test_la_prediction_est_immediate(predicteur):
    """Sous les doigts, tout ce qui depasse quelques millisecondes se sent."""
    import time

    predicteur.index  # hors mesure : il se construit une fois
    debut = time.perf_counter()
    for mot in ("anni", "bonj", "deman", "impo", "proble", "tele"):
        predicteur.completer(mot)
    ecoule = time.perf_counter() - debut
    assert ecoule < 0.05, f"{ecoule:.3f} s pour six predictions"
