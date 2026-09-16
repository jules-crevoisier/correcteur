# -*- coding: utf-8 -*-
"""Tests du compte rendu.

Ce module ne comprend pas une reunion : il repere des formules. Les tests
disent donc deux choses — ce qu'il doit reperer, et ce qu'il ne doit **pas**
inventer. La seconde liste compte plus que la premiere : une action attribuee
au hasard est pire qu'une action sans responsable, parce que personne ne la
reprend.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote.reunion import (  # noqa: E402
    compte_rendu, decouper_en_sujets, relever,
)
from papote.transcription import Tour, Transcription  # noqa: E402


def reunion(*repliques) -> Transcription:
    """« Marion », « ce qu'elle dit » ... — une reunion ecrite court."""
    transcription = Transcription()
    instant = 0.0
    for locuteur, texte in repliques:
        transcription.tours.append(
            Tour(locuteur, instant, instant + 20, texte))
        instant += 20
    return transcription


def especes(tours, espece):
    return [r for r in relever(tours) if r.espece == espece]


# -- les decisions ----------------------------------------------------------

@pytest.mark.parametrize("phrase", [
    "Donc on part sur la deuxième option.",
    "C'est validé, on lance lundi.",
    "On retient la proposition de Claire.",
    "Bon, on fait comme ça.",
    "On reporte le sujet à la semaine prochaine.",
])
def test_une_decision_est_reperee(phrase):
    tours = reunion(("Marion", phrase)).tours
    assert especes(tours, "décision"), phrase


@pytest.mark.parametrize("phrase", [
    "Je pense qu'on devrait peut-être en reparler.",
    "Il y a plusieurs options sur la table.",
    "C'est compliqué de trancher maintenant.",
])
def test_une_hesitation_n_est_pas_une_decision(phrase):
    tours = reunion(("Marion", phrase)).tours
    assert not especes(tours, "décision"), phrase


# -- les actions ------------------------------------------------------------

def test_celui_qui_s_engage_prend_l_action():
    tours = reunion(("Claire", "Je m'occupe de relancer la compta.")).tours
    actions = especes(tours, "action")
    assert actions and actions[0].qui == "Claire"


def test_une_action_nommee_va_a_la_personne_nommee():
    tours = reunion(("Marion", "Il faut que Pierre prépare le dossier.")).tours
    actions = especes(tours, "action")
    assert actions and actions[0].qui == "Pierre"


def test_une_action_sans_nom_reste_a_attribuer():
    """Une action attribuee au hasard est pire qu'une action sans
    responsable : personne ne la reprend."""
    tours = reunion(("Marion", "Il faut qu'on relance le client.")).tours
    actions = especes(tours, "action")
    assert actions and actions[0].qui == "à attribuer"


@pytest.mark.parametrize("phrase, attendu", [
    ("Je m'occupe de ça d'ici vendredi.", "d'ici vendredi"),
    ("Tu peux m'envoyer le fichier demain ?", "demain"),
    ("Il faut que Marion réponde avant lundi.", "avant lundi"),
    ("Je prépare la présentation pour la semaine prochaine.",
     "la semaine prochaine"),
])
def test_l_echeance_est_relevee(phrase, attendu):
    tours = reunion(("Claire", phrase)).tours
    actions = especes(tours, "action")
    assert actions and attendu in actions[0].quand


def test_une_action_sans_echeance_n_en_invente_pas():
    tours = reunion(("Claire", "Je m'occupe du dossier.")).tours
    assert especes(tours, "action")[0].quand == ""


# -- les questions ----------------------------------------------------------

def test_une_question_est_relevee():
    tours = reunion(("Marion", "Est-ce qu'on a le budget ?")).tours
    assert especes(tours, "question")


def test_une_affirmation_n_est_pas_une_question():
    tours = reunion(("Marion", "On a le budget.")).tours
    assert not especes(tours, "question")


# -- les sujets -------------------------------------------------------------

def test_une_transition_ouvre_un_sujet():
    transcription = reunion(
        ("Marion", "Bonjour à tous."),
        ("Marion", "On passe au budget de janvier."),
        ("Claire", "D'accord."),
    )
    sujets = decouper_en_sujets(transcription.tours)
    assert len(sujets) == 2
    assert "budget" in sujets[1].titre.lower()


def test_une_reunion_sans_transition_tient_en_un_bloc():
    """Beaucoup de reunions n'annoncent rien : c'est la reponse honnete."""
    transcription = reunion(("Marion", "Bonjour."), ("Claire", "Salut."))
    assert len(decouper_en_sujets(transcription.tours)) == 1


# -- le compte rendu --------------------------------------------------------

def test_le_compte_rendu_rassemble_tout():
    transcription = reunion(
        ("Marion", "Bonjour. On passe au budget. Est-ce qu'on a les chiffres ?"),
        ("Claire", "Pas encore. Je m'occupe de relancer d'ici vendredi."),
        ("Marion", "Donc on part sur la deuxième option."),
    )
    rendu = compte_rendu(transcription, "Point hebdo", "16 septembre")

    assert "# Point hebdo" in rendu
    assert "**Participants** : Marion, Claire" in rendu
    assert "## Décisions" in rendu and "deuxième option" in rendu
    assert "## Actions" in rendu and "d'ici vendredi" in rendu
    assert "## Questions restées ouvertes" in rendu
    # La transcription entiere est toujours la : ce qui n'a pas ete repere
    # n'est pas perdu.
    assert "## Transcription" in rendu
    assert "Pas encore." in rendu


def test_un_compte_rendu_sans_rien_a_relever_le_dit():
    transcription = reunion(("Marion", "Il fait beau aujourd'hui."))
    rendu = compte_rendu(transcription)
    assert "Aucune décision ni action" in rendu
    assert "## Transcription" in rendu


def test_une_reunion_vide_ne_fabrique_pas_de_compte_rendu():
    assert "Rien n'a été enregistré" in compte_rendu(Transcription())


def test_le_tableau_des_actions_supporte_une_barre_verticale():
    """Un « | » dans une phrase casserait le tableau Markdown."""
    transcription = reunion(("Claire", "Je m'occupe du champ a | b."))
    assert "\\|" in compte_rendu(transcription)


def test_la_duree_courte_s_affiche_en_secondes():
    transcription = reunion(("Marion", "Bonjour."))
    assert " s" in compte_rendu(transcription).split("**Durée** : ")[1][:8]
