# -*- coding: utf-8 -*-
"""Tests du dictionnaire et de la fabrique de suggestions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from correcteur.lexique import (  # noqa: E402
    CLASSE_ACCENT,
    CLASSE_EDITION,
    Lexique,
    squelette,
)


@pytest.fixture
def mini():
    """Un lexique minuscule, pour eprouver la logique de decision seule.

    L'ordre de la liste fait l'ordre des frequences : « pres » n'existe pas,
    « près » est courant, « prés » est rare.
    """
    return Lexique.depuis_formes(
        ["bonjour", "près", "prêts", "prés", "gâteaux", "gâteau", "maison",
         "maisons", "élève", "élevé", "cœur", "chat", "chats", "char"],
        frequences=["bonjour", "près", "gâteaux", "maison", "chat", "cœur",
                    "élève", "élevé", "maisons", "chats", "gâteau", "prés",
                    "prêts", "char"],
    )


def test_squelette_retire_accents_et_ligatures():
    assert squelette("Gâteaux") == "gateaux"
    assert squelette("cœur") == "coeur"
    assert squelette("Ça") == "ca"


def test_connait_tient_compte_de_la_casse(mini):
    assert mini.connait("gâteaux")
    assert mini.connait("Gâteaux")      # debut de phrase
    assert not mini.connait("gateaux")  # accents manquants


def test_les_accents_manquants_sont_une_correction_sure(mini):
    assert mini.suggestion("gateaux") == "gâteaux"
    assert mini.candidats("gateaux")[0].classe == CLASSE_ACCENT


def test_la_casse_du_mot_dorigine_est_conservee(mini):
    assert mini.suggestion("Gateaux") == "Gâteaux"


def test_deux_accentuations_aussi_courantes_ne_sont_pas_departagees(mini):
    """« élève » et « élevé » se valent : mieux vaut ne rien faire."""
    assert mini.suggestion("eleve") is None


def test_un_candidat_nettement_plus_courant_l_emporte(mini):
    """« près » est en tete de liste, « prés » et « prêts » loin derriere."""
    assert mini.suggestion("pres") == "près"


def test_la_faute_de_frappe_se_corrige_par_edition(mini):
    assert mini.suggestion("maisn") == "maison"
    assert mini.candidats("maisn")[0].classe == CLASSE_EDITION


def test_les_mots_courts_echappent_a_la_distance_d_edition(mini):
    """Sur trois lettres, une lettre d'ecart ne prouve plus rien."""
    assert mini.candidats("cht") == []


def test_un_mot_inconnu_sans_voisin_reste_inconnu(mini):
    assert mini.suggestion("zbeulotron") is None


# -- contre le vrai dictionnaire -------------------------------------------

ACCENTS_OUBLIES = [
    ("gateaux", "gâteaux"), ("tres", "très"), ("meme", "même"),
    ("etait", "était"), ("deja", "déjà"), ("francais", "français"),
    ("probleme", "problème"), ("apres", "après"), ("coeur", "cœur"),
    ("developpement", "développement"), ("ca", "ça"), ("connait", "connaît"),
]

FAUTES_DE_FRAPPE = [
    ("anniverssaire", "anniversaire"), ("exmple", "exemple"),
    ("interressant", "intéressant"), ("dificile", "difficile"),
]


@pytest.mark.parametrize("faute,attendu", ACCENTS_OUBLIES)
def test_accents_oublies(lexique, faute, attendu):
    assert lexique.suggestion(faute) == attendu


@pytest.mark.parametrize("faute,attendu", FAUTES_DE_FRAPPE)
def test_fautes_de_frappe(lexique, faute, attendu):
    assert lexique.suggestion(faute) == attendu


def test_les_mots_corrects_sont_reconnus(lexique):
    for mot in ("bonjour", "gâteaux", "aujourd'hui", "être", "français",
                "vingt-quatre".split("-")[0], "œuvre", "Paris"):
        assert lexique.connait(mot), mot
