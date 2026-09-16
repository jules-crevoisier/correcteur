# -*- coding: utf-8 -*-
"""Tests des regles de grammaire, une par une.

Chaque regle est jugee sur deux exemples : la faute qu'elle doit corriger, et
la phrase correcte voisine qu'elle ne doit surtout pas toucher.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import grammaire  # noqa: E402


# (texte fautif, texte attendu, nom de la regle)
CORRIGES = [
    ("je sais pas si sa va", "je sais pas si ça va", "SA_CA"),
    ("ca ma pris deux heures", "ça m'a pris deux heures", "APOSTROPHE_AVANT_PARTICIPE"),
    ("tas vu le film", "t'as vu le film", "APOSTROPHE_AVANT_PARTICIPE"),
    ("il me la dit hier", "il me l'a dit hier", "APOSTROPHE_AVANT_PARTICIPE"),
    ("il à mangé", "il a mangé", "IL_A"),
    ("je vais a la gare", "je vais à la gare", "A_ACCENT"),
    ("elle et contente", "elle est contente", "ET_EST"),
    ("ils on mangé", "ils ont mangé", "ILS_ONT"),
    ("elles son parties", "elles sont parties", "ILS_SONT"),
    ("je sais pas se que tu veux", "je sais pas ce que tu veux", "SE_CE"),
    ("il ce lave", "il se lave", "CE_SE"),
    ("s'est pas grave", "c'est pas grave", "S_EST_C_EST"),
    ("tu sais ou est mon sac", "tu sais où est mon sac", "OU_ACCENT"),
    ("je suis la", "je suis là", "LA_ACCENT"),
    ("je suis la bas", "je suis là-bas", "LA_ACCENT"),
    ("tout les jours", "tous les jours", "TOUT_TOUS"),
    ("mes je peux pas", "mais je peux pas", "MES_MAIS"),
    ("un peut plus tard", "un peu plus tard", "PEUT_PEU"),
    ("est ce que tu viens", "est-ce que tu viens", "EST_CE"),
    ("j'ai manger des frites", "j'ai mangé des frites", "PARTICIPE_APRES_AUXILIAIRE"),
    ("je vais mangé", "je vais manger", "INFINITIF_APRES_SEMI_AUXILIAIRE"),
    ("elles sont venu hier", "elles sont venues hier", "ACCORD_PARTICIPE_ETRE"),
    ("des enfant", "des enfants", "ACCORD_DETERMINANT_NOM"),
    ("je peut pas", "je peux pas", "ACCORD_SUJET_VERBE"),
    ("je croit pas", "je crois pas", "ACCORD_JE_TU_S"),
    ("tu mange quoi", "tu manges quoi", "ACCORD_TU_S"),
    ("ils mange trop", "ils mangent trop", "ACCORD_ILS_ENT"),
]

# Phrases correctes que les regles ci-dessus pourraient abimer.
INTOUCHABLES = [
    "sa mère est venue",              # « sa » possessif
    "un tas de trucs",                # « tas » nom commun
    "il a la flemme",                 # « a » verbe avoir
    "lui et elle sont partis",        # vraie coordination
    "on mange à midi",                # « on » pronom
    "son frère arrive",               # « son » possessif
    "ils se sont levés",              # « se » pronominal
    "ce que je veux",                 # « ce » demonstratif
    "il s'est levé tôt",              # « s'est » correct
    "du pain ou du fromage",          # « ou » conjonction
    "la maison est grande",           # « la » article
    "tout le monde est là",           # « tout » singulier
    "mes amis sont là",               # « mes » possessif
    "il peut venir demain",           # « peut » verbe
    "j'ai été manger dehors",         # infinitif apres « été »
    "je vais au café",                # « café » n'est pas un participe
    "je les mange",                   # « les » pronom, pas determinant
    "elle est venue",                 # accord deja fait
    "il est content",                 # rien a accorder
]


def corriger(correcteur, texte):
    return correcteur.corriger(texte)[0]


@pytest.mark.parametrize("texte,attendu,regle", CORRIGES)
def test_la_regle_corrige(correcteur, texte, attendu, regle):
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == attendu
    assert regle in {c.regle for c in corrections}


@pytest.mark.parametrize("texte", INTOUCHABLES)
def test_les_phrases_correctes_sont_intactes(correcteur, texte):
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == texte, f"corrections indues : {[str(c) for c in corrections]}"


# -- decoupage --------------------------------------------------------------

def test_le_decoupage_garde_les_apostrophes():
    jetons = [j.texte for j in grammaire.decouper("j'ai vu aujourd'hui qu'il partait")]
    assert jetons == ["j'ai", "vu", "aujourd'hui", "qu'il", "partait"]


def test_le_decoupage_separe_les_traits_d_union():
    jetons = [j.texte for j in grammaire.decouper("est-ce que peut-être")]
    assert jetons == ["est", "ce", "que", "peut", "être"]


@pytest.mark.parametrize("mot,elision,noyau", [
    ("c'est", "c'", "est"),
    ("j'ai", "j'", "ai"),
    ("qu'il", "qu'", "il"),
    ("aujourd'hui", "", "aujourd'hui"),
    ("bonjour", "", "bonjour"),
])
def test_separation_des_elisions(mot, elision, noyau):
    assert grammaire.separer_clitique(mot) == (elision, noyau)


# -- le registre soutenu -----------------------------------------------------

SOUTENUS = [
    ("j'ai pas compris", "Je n'ai pas compris."),
    ("il peut pas venir", "Il ne peut pas venir."),
    ("on a pas le temps", "On n'a pas le temps."),
    ("t'as pas vu", "Tu n'as pas vu."),
    ("c'est pas grave", "Ce n'est pas grave."),
    ("y a personne", "Il n'y a personne."),
    ("faut pas exagérer", "Il ne faut pas exagérer."),
    ("il me l'a pas dit", "Il ne me l'a pas dit."),
    ("ça marche", "Cela marche."),
    ("dsl bcp de travail", "Désolé beaucoup de travail."),
]


@pytest.fixture(scope="module")
def correcteur_soutenu(request):
    from papote.moteur import Correcteur
    from papote.politique import SOUTENU

    return Correcteur(request.getfixturevalue("lexique"), registre=SOUTENU)


@pytest.mark.parametrize("texte,attendu", SOUTENUS)
def test_le_registre_soutenu_releve_le_ton(correcteur_soutenu, texte, attendu):
    assert correcteur_soutenu.corriger(texte)[0] == attendu


@pytest.mark.parametrize("texte,_attendu", SOUTENUS)
def test_le_registre_parle_ne_touche_a_rien(correcteur, texte, _attendu):
    """Par defaut, aucune de ces phrases ne doit bouger d'un iota."""
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == texte, f"corrections indues : {[str(c) for c in corrections]}"


def test_le_soutenu_ne_nie_pas_deux_fois(correcteur_soutenu):
    texte = "il n'a pas compris."
    assert correcteur_soutenu.corriger(texte)[0] == "Il n'a pas compris."


def test_le_soutenu_ne_confond_pas_ne_que_et_que(correcteur_soutenu):
    """« faut que j'y aille » n'est pas une negation."""
    assert correcteur_soutenu.corriger("faut que j'y aille")[0] \
        == "Il faut que j'y aille."


def test_ca_va_reste_ca_va(correcteur_soutenu):
    """Personne n'ecrit « cela va ? »."""
    assert correcteur_soutenu.corriger("ça va ?")[0] == "Ça va ?"


# -- les mots justes qui en cachent un autre --------------------------------

def test_un_mot_reel_mais_improbable_est_corrige(correcteur):
    """« commet » est le verbe commettre — mais pas en tête de phrase."""
    assert correcteur.corriger("commet ça va")[0] == "comment ça va"


def test_le_meme_mot_reste_quand_il_est_a_sa_place(correcteur):
    assert correcteur.corriger("il commet une erreur")[0] == "il commet une erreur"


def test_un_mot_rare_ne_masque_plus_la_faute(correcteur):
    """« sui » est au dictionnaire ; « je sui » n'en reste pas moins faux."""
    assert correcteur.corriger("je sui en route")[0] == "je suis en route"
    assert correcteur.corriger("il fau qu'on parle")[0] == "il faut qu'on parle"


def test_l_elision_ne_cache_pas_l_auxiliaire(correcteur):
    """« j'ai » doit compter comme « ai » pour la condition qui le cherche."""
    assert correcteur.corriger("j'ai pri le bus")[0] == "j'ai pris le bus"


def test_un_nom_apres_determinant_reste_intact(correcteur):
    assert correcteur.corriger("le pri est correct")[0] == "le pri est correct"


# -- doublons ---------------------------------------------------------------

def test_un_mot_ecrit_deux_fois_est_reduit(correcteur):
    assert correcteur.corriger("je vais vais partir")[0] == "je vais partir"
    assert correcteur.corriger("c'est le le meilleur")[0] == "c'est le meilleur"


def test_les_doublons_legitimes_survivent(correcteur):
    """« nous nous levons » n'est pas une faute de frappe."""
    for phrase in ("nous nous levons tôt", "vous vous trompez",
                   "c'est très très bon", "il se se"):
        assert "  " not in correcteur.corriger(phrase)[0]
    assert correcteur.corriger("nous nous levons tôt")[0] == "nous nous levons tôt"
    assert correcteur.corriger("vous vous trompez")[0] == "vous vous trompez"


def test_une_ponctuation_entre_les_deux_protege_la_repetition(correcteur):
    """« bon, bon » est une insistance, pas une faute."""
    assert correcteur.corriger("bon, bon")[0] == "bon, bon"


# -- traits d'union ---------------------------------------------------------

@pytest.mark.parametrize("faute,attendu", [
    ("on prend rendez vous quand", "on prend rendez-vous quand"),
    ("peut etre que oui", "peut-être que oui"),
    ("c'est a dire quoi", "c'est-à-dire quoi"),
    ("qu'est ce que tu fais", "qu'est-ce que tu fais"),
    ("au dessus de la porte", "au-dessus de la porte"),
    ("il est la bas", "il est là-bas"),
])
def test_les_composes_prennent_leur_trait_d_union(correcteur, faute, attendu):
    assert correcteur.corriger(faute)[0] == attendu


def test_le_verbe_pouvoir_garde_ses_deux_mots(correcteur):
    """« il peut être là » n'est pas « il peut-être là »."""
    assert correcteur.corriger("il peut être là")[0] == "il peut être là"


@pytest.mark.parametrize("faute,attendu", [
    ("dis moi tout", "dis-moi tout"),
    ("envoie moi le lien", "envoie-moi le lien"),
    ("vas y doucement", "vas-y doucement"),
])
def test_l_imperatif_et_son_pronom_se_lient(correcteur, faute, attendu):
    assert correcteur.corriger(faute)[0] == attendu


def test_un_sujet_devant_empeche_la_liaison(correcteur):
    """« je dis moi aussi » n'est pas un impératif."""
    assert correcteur.corriger("je dis moi aussi")[0] == "je dis moi aussi"
