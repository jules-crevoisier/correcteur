# -*- coding: utf-8 -*-
"""Tests du moteur : ce qu'il protege, et l'ordre dans lequel il decide."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote.moteur import Correcteur  # noqa: E402


# Tout ce qui doit traverser le correcteur sans une egratignure.
INTOUCHABLES = [
    # Le francais parle : la raison d'etre de l'outil.
    "j'ai pas compris ce que tu voulais dire",
    "faut que j'y aille",
    "y a rien à faire",
    "c'est pas grave, on se voit demain",
    "je sais pas si ça va marcher",
    # L'argot d'Internet.
    "tkt jsp encore",
    "wsh frr askip c'est mort",
    "dsl je peux pas venir",
    # L'emphase volontaire.
    "mdrrrr c'est trop drôle",
    "ouiiii carrément",
    # Les liens, le code, les mentions.
    "regarde https://exemple.fr/a_b-c",
    "écris `git commit -m truc` dans le terminal",
    "salut <@123456789> tu viens ?",
    "le salon #general est mort",
    "||spoiler||",
    "j'ai 2 chats et 15 ans",
    # L'anglais, que le dictionnaire francais prendrait pour des fautes.
    "the game is over",
    "check this out",
]


@pytest.mark.parametrize("texte", INTOUCHABLES)
def test_rien_ne_bouge(correcteur, texte):
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == texte, f"corrections indues : {[str(c) for c in corrections]}"


def test_les_liens_sont_intacts_mais_le_reste_est_corrige(correcteur):
    corrige, _ = correcteur.corriger("regarde https://exemple.fr/a_b-c c'est enorme")
    assert "https://exemple.fr/a_b-c" in corrige
    assert "énorme" in corrige


def test_les_noms_propres_ne_sont_pas_remplaces(correcteur):
    """« Kayn » ne doit pas devenir « Kay » : on ne joue pas avec les noms."""
    assert correcteur.corriger("j'ai joué Kayn hier")[0] == "j'ai joué Kayn hier"


def test_le_lexique_personnel_protege_un_mot(lexique):
    sans = Correcteur(lexique)
    avec = Correcteur(lexique, mots_perso=["Tekken"])
    texte = "on lance un Tekken"
    assert avec.corriger(texte)[0] == texte
    # Sans protection, le mot reste inconnu : le moteur a le droit d'essayer.
    sans.corriger(texte)


def test_les_marges_sont_conservees(correcteur):
    assert correcteur.corriger("  sa va  ")[0] == "  ça va  "


def test_texte_vide(correcteur):
    assert correcteur.corriger("")[0] == ""
    assert correcteur.corriger("   ")[0] == "   "


def test_les_corrections_sont_rapportees(correcteur):
    _, corrections = correcteur.corriger("ils on mangé tout les gateaux")
    assert [str(c) for c in corrections] == [
        "on → ont", "tout → tous", "gateaux → gâteaux",
    ]
    assert all(c.message for c in corrections)


def test_deux_passes_debloquent_une_correction(correcteur):
    """« ils on manger » exige de corriger « on » avant de voir le participe."""
    assert correcteur.corriger("ils on manger")[0] == "ils ont mangé"
    assert correcteur.corriger("ils on manger", passes=1)[0] == "ils ont manger"


# -- regles optionnelles ----------------------------------------------------

def test_la_majuscule_de_phrase_est_desactivee_par_defaut(correcteur):
    assert correcteur.corriger("salut ça va")[0] == "salut ça va"


def test_la_majuscule_de_phrase_peut_etre_activee(lexique):
    c = Correcteur(lexique, regles_optionnelles={"MAJUSCULE_PHRASE": True})
    assert c.corriger("salut. ça va")[0] == "Salut. Ça va"


def test_le_point_final_peut_etre_active(lexique):
    c = Correcteur(lexique, regles_optionnelles={"PONCTUATION_POINT": True})
    assert c.corriger("salut ça va")[0] == "salut ça va."
    assert c.corriger("salut ça va ?")[0] == "salut ça va ?"


# -- remplacements personnels ------------------------------------------------

def test_un_remplacement_perso_est_applique(lexique):
    c = Correcteur(lexique, remplacements_perso={"ptetre": "peut-être"})
    assert c.corriger("ptetre que oui")[0] == "peut-être que oui"


def test_un_remplacement_perso_garde_la_majuscule(lexique):
    c = Correcteur(lexique, remplacements_perso={"ptetre": "peut-être"})
    assert c.corriger("Ptetre")[0] == "Peut-être"


def test_un_remplacement_perso_passe_avant_l_argot_protege(lexique):
    """« dsl » est protégé d'origine ; l'utilisateur reste maître chez lui."""
    c = Correcteur(lexique, remplacements_perso={"dsl": "désolé"})
    assert c.corriger("dsl")[0] == "désolé"


def test_un_remplacement_perso_ne_touche_pas_a_un_lien(lexique):
    c = Correcteur(lexique, remplacements_perso={"ptetre": "peut-être"})
    texte = "regarde https://exemple.fr/ptetre"
    assert c.corriger(texte)[0] == texte


def test_un_remplacement_perso_sert_aussi_d_abreviation(lexique):
    c = Correcteur(lexique, remplacements_perso={"cdlt": "cordialement"})
    assert c.corriger("cdlt")[0] == "cordialement"


def test_les_remplacements_vides_sont_ignores(lexique):
    c = Correcteur(lexique, remplacements_perso={"": "x", "y": "  "})
    assert c.corriger("y")[0] == "y"
