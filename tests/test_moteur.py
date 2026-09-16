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


# -- typographie française ---------------------------------------------------

def typographe(lexique):
    return Correcteur(lexique, regles_optionnelles={"TYPOGRAPHIE": True})


def test_la_typographie_est_desactivee_par_defaut(correcteur):
    assert correcteur.corriger("vraiment ? oui...")[0] == "vraiment ? oui..."


def test_les_points_de_suspension_deviennent_un_caractere(lexique):
    assert typographe(lexique).corriger("bon... voilà")[0] == "bon… voilà"


def test_les_guillemets_deviennent_francais(lexique):
    corrige = typographe(lexique).corriger('il a dit "bonjour" hier')[0]
    assert "« bonjour »" in corrige


def test_l_espace_avant_la_ponctuation_est_insecable(lexique):
    assert typographe(lexique).corriger("vraiment ?")[0] == "vraiment ?"
    assert typographe(lexique).corriger("vraiment?")[0] == "vraiment ?"


def test_la_typographie_epargne_les_liens(lexique):
    texte = "regarde https://exemple.fr/a?b=1 et dis-moi"
    assert typographe(lexique).corriger(texte)[0] == texte


def test_la_typographie_epargne_le_code(lexique):
    texte = "tape `ls -l | grep x?` pour voir"
    assert typographe(lexique).corriger(texte)[0] == texte


def test_une_apostrophe_oubliee_supporte_une_faute_de_frappe(correcteur):
    """« jesper » -> « j'espère » : l'apostrophe manque, et le e aussi."""
    assert correcteur.corriger("jesper que oui")[0].startswith("j'espère")


def test_l_apostrophe_n_invente_pas_de_mot_rare(correcteur):
    """« subject » ne devient pas « s'abject » : « abject » est trop rare."""
    assert "s'abject" not in correcteur.corriger("le subject du jour")[0]


def test_les_mots_incertains_sont_proposes_sans_etre_imposes(correcteur):
    """« ourné » reste en place, mais le correcteur sait quoi offrir."""
    assert "ourné" in correcteur.corriger("une bonne ourné")[0]
    assert correcteur.propositions("ourné")[0] == "journée"



# -- l'espace sautee ---------------------------------------------------------

@pytest.mark.parametrize("colle,attendu", [
    ("ilfaut voir", "il faut voir"),
    ("commenttesté", "comment testé"),
    ("bonjourtout le monde", "bonjour tout le monde"),
    ("jevais partir", "je vais partir"),
    ("parcontre", "par contre"),
])
def test_deux_mots_colles_se_separent(correcteur, colle, attendu):
    """L'espace est la touche la plus large du clavier, et la plus manquée."""
    assert correcteur.corriger(colle)[0] == attendu


def test_la_coupure_passe_avant_la_faute_de_frappe(correcteur):
    """« ilfaut » devenait « faut » : la distance d'édition escamotait un mot."""
    assert correcteur.corriger("ilfaut")[0] == "il faut"


@pytest.mark.parametrize("mot", ["github", "facebook", "portable", "important"])
def test_un_mot_entier_ne_se_coupe_pas(correcteur, mot):
    """« hub » est au dictionnaire, 18 000e — cela ne suffit pas à couper."""
    assert correcteur.corriger(f"sur {mot} demain")[0] == f"sur {mot} demain"


def test_un_mot_qui_hesite_sur_ses_accents_ne_se_coupe_pas(correcteur):
    """« decolle » est « décolle » ou « décollé », pas « de colle »."""
    assert "de colle" not in correcteur.corriger("l'avion decolle")[0]


def test_l_apostrophe_ne_passe_pas_devant_une_hesitation_d_accent(correcteur):
    assert "d'école" not in correcteur.corriger("l'avion decolle")[0]


def test_un_mot_trop_court_ne_se_coupe_pas(correcteur):
    """Sur quatre lettres, la coupure est plus souvent une coïncidence."""
    for mot in ("cela", "sont", "dont"):
        assert correcteur.corriger(mot)[0] == mot


# -- le moins d'inventions possible ------------------------------------------

def test_une_lettre_suffit_avant_d_inventer_une_apostrophe(correcteur):
    """« menbre » est « membre » — une lettre. Il devenait « m'entre » :
    une apostrophe *et* une lettre."""
    assert correcteur.corriger("un menbre du staff")[0] == "un membre du staff"
    assert correcteur.corriger("les menbres")[0] == "les membres"


def test_l_apostrophe_garde_les_cas_qu_elle_seule_repare(correcteur):
    """Le garde-fou ne doit pas emporter ce qui marchait."""
    assert correcteur.corriger("jesper que oui")[0] == "j'espère que oui"
    assert correcteur.corriger("cetait bien")[0] == "c'était bien"
    assert correcteur.corriger("daccord jarrive")[0] == "d'accord j'arrive"


# -- un mot que des gens ecrivent n'est pas une faute de frappe ---------------

@pytest.mark.parametrize("mot", ["perm", "chanel", "facebook", "cool", "mail"])
def test_un_mot_de_la_liste_de_frequences_reste_intact(correcteur, mot):
    """« perm » devenait « père ». Le dictionnaire l'ignore, mais la liste de
    fréquences le connaît : c'est un mot que des gens écrivent — une
    abréviation, une marque, un mot anglais passé dans l'usage."""
    assert correcteur.corriger(f"je pense à {mot}")[0] == f"je pense à {mot}"


@pytest.mark.parametrize("faute,attendu", [
    ("un anniverssaire", "un anniversaire"),
    ("c'est un exmple", "c'est un exemple"),
    ("je vais au bureua", "je vais au bureau"),
    ("un menbre", "un membre"),
])
def test_les_vraies_fautes_de_frappe_restent_corrigees(correcteur, faute,
                                                        attendu):
    """La séparation est nette : aucune faute de frappe ne figure dans la
    liste de fréquences, et tous les mots réels y sont."""
    assert correcteur.corriger(faute)[0] == attendu
