# -*- coding: utf-8 -*-
"""Tests de la grammaire lue dans le dictionnaire.

Deux choses a verifier, et elles ne se verifient pas de la meme facon.

**La table est juste.** Ce sont des faits de francais, qu'on ecrit en clair :
« pensent » est une 3e personne du pluriel, « bijou » fait « bijoux ». Ces
tests-la portent sur les fichiers livres, parce que c'est eux que
l'application lit.

**La lecture est prudente.** Devant deux reponses possibles, `accorder` ne
rend rien. Ces tests-la se font sur des paradigmes inventes, ou l'on maitrise
exactement ce que la table contient.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote.morphologie import Morphologie  # noqa: E402


@pytest.fixture(scope="module")
def morpho():
    table = Morphologie()
    if not table.analyses:
        pytest.skip("les tables de morphologie sont absentes")
    return table


# -- ce que le dictionnaire sait --------------------------------------------

@pytest.mark.parametrize("mot, trait", [
    ("pensent", "3p"),
    ("pense", "1s"),
    ("pense", "3s"),
    ("penses", "2s"),
    ("pensons", "1p"),
    ("pensez", "2p"),
    ("penser", "inf"),
    ("pensant", "ppr"),
    ("pensé", "pms"),
    ("pensées", "pfp"),
    # Les verbes irreguliers, que l'ancienne voie ne voyait pas du tout.
    ("finissent", "3p"),
    ("dorment", "3p"),
    ("prennent", "3p"),
    ("vont", "3p"),
    ("veulent", "3p"),
    # « vient » finit par « ent » sans etre un pluriel : la terminaison ne
    # dit rien, l'ordre des regles dit tout.
    ("vient", "3s"),
    ("tient", "3s"),
    ("ment", "3s"),
    # Noms et adjectifs.
    ("chats", "mp"),
    ("chattes", "fp"),
    ("dernières", "fp"),
    ("chevaux", "xp"),
    ("gens", "xp"),
])
def test_le_trait_est_juste(morpho, mot, trait):
    assert trait in morpho.traits(mot), sorted(morpho.traits(mot))


@pytest.mark.parametrize("mot, absent", [
    ("vient", "3p"),      # le piege de la terminaison
    ("pensent", "3s"),
    ("vas", "3p"),        # « aller » n'est pas pronominal : aucune elision
    ("vont", "2s"),       #   ne distingue « tu vas » de « ils vont »
    ("es", "1s"),
    ("suis", "3s"),
])
def test_le_trait_est_absent(morpho, mot, absent):
    assert absent not in morpho.traits(mot), sorted(morpho.traits(mot))


def test_un_mot_inconnu_ne_dit_rien(morpho):
    assert morpho.traits("zbeulotron") == frozenset()
    assert morpho.accorder("zbeulotron", "3p") is None


# -- le nombre, la ou la terminaison se trompe ------------------------------

@pytest.mark.parametrize("mot", ["chats", "chevaux", "gens", "maisons"])
def test_ce_qui_est_pluriel(morpho, mot):
    assert morpho.pluriel(mot)


def test_un_mot_qui_est_aussi_un_verbe_n_est_pas_un_pluriel_sur(morpho):
    """« affiches » est le pluriel du nom et la 2e personne du verbe."""
    assert not morpho.pluriel("affiches")
    assert morpho.est("affiches", "xp")


@pytest.mark.parametrize("mot", [
    # Ils finissent par « s » ou « x » sans etre des pluriels. C'est ce que
    # l'ancienne regle — « finit par s, donc pluriel » — ne savait pas.
    "temps", "prix", "souris", "fois", "mois", "corps", "choix", "voix",
])
def test_ce_qui_n_est_pas_forcement_pluriel(morpho, mot):
    assert not morpho.pluriel(mot)


# -- accorder ---------------------------------------------------------------

@pytest.mark.parametrize("mot, cible, attendu", [
    # Tous les groupes, la ou l'ancienne voie ne conjuguait que le premier.
    ("pense", "3p", "pensent"),
    ("finit", "3p", "finissent"),
    ("dort", "3p", "dorment"),
    ("prend", "3p", "prennent"),
    ("va", "3p", "vont"),
    ("est", "3p", "sont"),
    ("a", "3p", "ont"),
    ("fait", "3p", "font"),
    ("peut", "1s", "peux"),
    ("part", "1s", "pars"),
    ("cours", "3s", "court"),
])
def test_accorder_trouve_la_forme(morpho, mot, cible, attendu):
    assert morpho.accorder(mot, cible) == attendu


@pytest.mark.parametrize("mot, cible, attendu", [
    # Le temps se garde : « pensait » est un imparfait, « pensera » un futur.
    ("pensait", "3p", "pensaient"),
    ("pensera", "3p", "penseront"),
    ("pensa", "3p", "pensèrent"),
    # Sans ce decoupage, « finit » donnerait « finirent » — une 3e personne
    # du pluriel parfaitement correcte, mais au passe simple.
    ("finit", "3p", "finissent"),
    ("finissait", "3p", "finissaient"),
])
def test_accorder_reste_dans_le_temps(morpho, mot, cible, attendu):
    assert morpho.accorder(mot, cible) == attendu


@pytest.mark.parametrize("singulier, pluriel", [
    ("cheval", "chevaux"),
    ("travail", "travaux"),
    ("journal", "journaux"),
    ("bureau", "bureaux"),
    # Les deux que la regle ecrite a la main confondait : meme terminaison
    # en « ou »/« eu », pluriels differents.
    ("bijou", "bijoux"),
    ("pneu", "pneus"),
    ("membre", "membres"),
    ("délai", "délais"),
])
def test_le_pluriel_se_lit(morpho, singulier, pluriel):
    assert morpho.au_pluriel(singulier) == pluriel


def test_le_pluriel_garde_le_genre(morpho):
    assert morpho.au_pluriel("contente") == "contentes"
    assert morpho.au_pluriel("content") == "contents"


def test_le_singulier_se_lit(morpho):
    assert morpho.au_singulier("chevaux") == "cheval"
    assert morpho.au_singulier("bijoux") == "bijou"


def test_une_forme_hors_du_temps_se_cherche_partout(morpho):
    """« prit » est un passe simple ; « pris » n'y figure pas."""
    assert morpho.accorder("prit", {"pms", "pmp"}) is None
    assert morpho.forme("prit", {"pms", "pmp"}) == "pris"


# -- la prudence, sur des paradigmes maitrises ------------------------------

def table(paradigmes):
    return Morphologie.depuis_paradigmes(paradigmes)


def test_deux_formes_egalement_proches_ne_se_departagent_pas():
    morpho = table({"gloub": [{"gloub": {"3s"}, "glaba": {"3p"},
                               "glabo": {"3p"}}]})
    assert morpho.accorder("gloub", "3p") is None


def test_la_forme_qui_prolonge_le_mot_l_emporte():
    """« pouvoir » a deux premieres personnes, « peux » et « puis »."""
    morpho = table({"gloubir": [{"gloubit": {"3s"}, "gloubent": {"3p"},
                                 "zarbent": {"3p"}}]})
    assert morpho.accorder("gloubit", "3p") == "gloubent"


def test_deux_lemmes_qui_ne_disent_pas_la_meme_chose_font_taire():
    morpho = table({
        "gloubir": [{"glouba": {"3s"}, "gloubent": {"3p"}}],
        "gloubar": [{"glouba": {"3s"}, "gloubarent": {"3p"}}],
    })
    assert morpho.accorder("glouba", "3p") is None


def test_un_seul_lemme_repond():
    morpho = table({"gloubir": [{"glouba": {"3s"}, "gloubent": {"3p"}}]})
    assert morpho.accorder("glouba", "3p") == "gloubent"


def test_une_table_absente_ne_fait_rien_tomber(tmp_path):
    """Sans les fichiers, les regles d'accord se taisent — rien de plus."""
    morpho = Morphologie(dossier=tmp_path)
    assert morpho.traits("pensent") == frozenset()
    assert morpho.au_pluriel("cheval") is None
    assert not morpho.pluriel("chats")
