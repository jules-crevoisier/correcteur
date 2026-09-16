# -*- coding: utf-8 -*-
"""La qualite du correcteur, mesuree et defendue.

Les autres tests verifient que chaque regle fait ce qu'elle annonce. Celui-ci
juge le resultat, sur deux corpus qui ne disent pas la meme chose :

    developpement    les phrases qui ont servi a ecrire les regles. Leur
                     score ne mesure rien — un moteur les connait par coeur.
                     Il sert de garde-fou : s'il baisse, on a casse quelque
                     chose qui marchait.

    tenu a l'ecart   des phrases ecrites d'un trait, jamais passees dans le
                     correcteur pendant qu'on le construisait. C'est la seule
                     mesure qui vaille, et c'est celle qui doit monter.

La precision est le seuil dur, des deux cotes : **aucune phrase correcte ne
doit etre abimee**. Une faute laissee passer se remarque a peine ; une phrase
juste corrompue se voit tout de suite, et fait desinstaller l'outil.

    python outils/evaluer.py            les deux tableaux de bord
    python outils/evaluer.py --detail   le detail du corpus de developpement
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "outils"))

from corpus import developpement, tenu_a_lecart  # noqa: E402
from evaluer import evaluer  # noqa: E402

# En dessous, on a casse quelque chose : ces seuils ne descendent jamais.
RAPPEL_MINIMAL_DEV = 0.95

# Le rappel sur le corpus tenu a l'ecart, mesure le jour ou il a ete ecrit.
# Il monte a chaque progres du moteur, et ce chiffre monte avec lui. Il ne
# redescend jamais : le faire baisser, c'est avouer une regression.
RAPPEL_MINIMAL_A_PART = 0.63

# Une phrase correcte abimee est un defaut grave. Le corpus en tolerait une,
# heritee du jour de son ecriture ; en l'agrandissant on a trouve les trois
# bugs qui la causaient, et le plafond est descendu a zero. Il n'y remonte
# pas : zero, pas « presque zero ».
ABIMEES_MAXIMUM_A_PART = 0


@pytest.fixture(scope="module")
def mesure(correcteur):
    return evaluer(correcteur, developpement.FAUTES, developpement.INTOUCHABLES)


@pytest.fixture(scope="module")
def mesure_a_part(correcteur):
    return evaluer(correcteur, tenu_a_lecart.FAUTES, tenu_a_lecart.INTOUCHABLES)


# -- corpus de developpement : le garde-fou ---------------------------------

def test_aucune_phrase_correcte_n_est_abimee(mesure):
    """Le seuil dur. Zero, pas « presque zero »."""
    abimees = "\n".join(f"  {phrase}\n    -> {obtenu}"
                        for phrase, obtenu in mesure["abimees"])
    assert not mesure["abimees"], f"phrases abimees :\n{abimees}"


def test_le_rappel_ne_baisse_pas(mesure):
    rappel = len(mesure["reussites"]) / len(developpement.FAUTES)
    manquees = "\n".join(f"  [{c}] {f}\n    attendu : {a}\n    obtenu  : {o}"
                         for c, f, a, o in mesure["echecs"])
    assert rappel >= RAPPEL_MINIMAL_DEV, (
        f"rappel tombe a {rappel:.0%}, seuil {RAPPEL_MINIMAL_DEV:.0%} :\n"
        f"{manquees}"
    )


# -- corpus tenu a l'ecart : la mesure --------------------------------------
#
# Ces deux tests ne disent jamais *quelles* phrases ont rate. Les lire, c'est
# se mettre a corriger le moteur phrase par phrase — et le corpus ne mesure
# plus rien. Ils ne rendent qu'un chiffre.

def test_le_rappel_tenu_a_l_ecart_ne_baisse_pas(mesure_a_part):
    rappel = len(mesure_a_part["reussites"]) / len(tenu_a_lecart.FAUTES)
    assert rappel >= RAPPEL_MINIMAL_A_PART, (
        f"rappel tombe a {rappel:.0%} sur le corpus tenu a l'ecart, "
        f"seuil {RAPPEL_MINIMAL_A_PART:.0%}. Le detail reste sous enveloppe : "
        f"« python outils/evaluer.py --ouvrir-l-enveloppe », en sachant que "
        f"le corpus est alors brule."
    )


def test_la_precision_tenue_a_l_ecart_ne_baisse_pas(mesure_a_part):
    abimees = len(mesure_a_part["abimees"])
    assert abimees <= ABIMEES_MAXIMUM_A_PART, (
        f"{abimees} phrases correctes abimees sur le corpus tenu a l'ecart, "
        f"plafond {ABIMEES_MAXIMUM_A_PART}."
    )


# -- les corpus eux-memes ---------------------------------------------------

def test_les_corpus_restent_consequents():
    """Un corpus qu'on vide passerait tous les seuils."""
    assert len(developpement.FAUTES) >= 80
    assert len(developpement.INTOUCHABLES) >= 100
    assert len(tenu_a_lecart.FAUTES) >= 100
    assert len(tenu_a_lecart.INTOUCHABLES) >= 100


def test_les_deux_corpus_ne_se_recouvrent_pas():
    """Une phrase presente des deux cotes rendrait la mesure complaisante."""
    dev = {f for f, _a, _c in developpement.FAUTES}
    a_part = {f for f, _a, _c in tenu_a_lecart.FAUTES}
    assert not dev & a_part, f"phrases communes : {sorted(dev & a_part)}"

    dev_justes = set(developpement.INTOUCHABLES)
    a_part_justes = set(tenu_a_lecart.INTOUCHABLES)
    assert not dev_justes & a_part_justes


@pytest.mark.parametrize("categorie", ["accent", "accord", "apostrophe",
                                       "conjugaison", "frappe", "homophone"])
def test_chaque_categorie_est_representee(categorie):
    assert any(c == categorie for _, _, c in developpement.FAUTES)
    assert any(c == categorie for _, _, c in tenu_a_lecart.FAUTES)


@pytest.mark.parametrize("categorie", ["trait-union", "mot-rare", "doublon",
                                       "majuscule"])
def test_le_corpus_a_part_couvre_ce_que_le_moteur_ne_sait_pas_encore(categorie):
    """Un corpus qui n'eprouve que les acquis ne sert qu'a se rassurer."""
    assert any(c == categorie for _, _, c in tenu_a_lecart.FAUTES)
