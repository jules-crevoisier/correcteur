# -*- coding: utf-8 -*-
"""Tests du dictionnaire et de la fabrique de suggestions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import lexique as lexique_mod  # noqa: E402
from papote.lexique import (  # noqa: E402
    CLASSE_ACCENT,
    CLASSE_EDITION,
    Lexique,
    accentue,
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


# -- deux frappes d'ecart ----------------------------------------------------

# Les trois premieres ne coutent qu'une frappe — une inversion, une lettre en
# trop — mais elles etaient hors de portee avant que les variantes ne sachent
# inverser deux lettres. La derniere en demande bien deux.
DOUBLES_FAUTES = [
    ("jorunée", "journée"),
    ("bonjoru", "bonjour"),
    ("mercii", "merci"),
    ("anniverssairee", "anniversaire"),
]


@pytest.mark.parametrize("faute,attendu", DOUBLES_FAUTES)
def test_deux_frappes_d_ecart(lexique, faute, attendu):
    assert lexique.suggestion(faute) == attendu


def test_sur_trois_lettres_seules_les_lettres_interverties_comptent(lexique):
    """N'importe quel mot technique est a une substitution d'un mot francais.

    « tab » deviendrait « ta », « dev » deviendrait « des », « git »
    deviendrait « dit ». On n'accepte donc que les memes lettres dans le
    desordre : l'utilisateur a tape les bonnes touches, dans le mauvais
    ordre.
    """
    assert lexique.suggestion("qeu") == "que"
    assert lexique.suggestion("aps") == "pas"
    for technique in ("tab", "dev", "git", "npm", "css", "sql"):
        assert lexique.suggestion(technique) is None, technique


def test_les_candidats_courts_sont_tous_des_anagrammes(lexique):
    for candidat in lexique.candidats("abc"):
        assert sorted(candidat.mot) == sorted("abc"), candidat.mot


def test_un_anagramme_rare_ne_suffit_pas(lexique):
    """« abc » a bien « bac » pour anagramme — 2 156e, trop rare pour parier."""
    assert lexique.suggestion("abc") is None


def test_un_accent_tape_ne_se_perd_pas(lexique):
    """« pasé » devient « passé », jamais « pas » — pourtant bien plus courant."""
    assert lexique.suggestion("pasé") == "passé"
    assert all(accentue(c.mot) for c in lexique.candidats("pasé"))


def test_la_frappe_ne_cherche_pas_si_loin(lexique):
    """La recherche a deux frappes coute trop cher pour une touche."""
    from papote.lexique import CLASSE_EDITION

    assert lexique.suggestion("anniverssairee", classe_max=CLASSE_EDITION) is None
    # ... et elle ne la paie meme pas : aucun candidat lointain n'est fabrique.
    assert lexique.candidats("anniverssairee", CLASSE_EDITION) == []


# -- la courte liste, quand la certitude manque -------------------------------

def test_les_propositions_classent_le_mot_courant_en_tete(lexique):
    """« ourné » : le correcteur se tait, mais il a bien « journée » en main.

    « tourné » n'est qu'a une frappe, « journée » a deux — mais « journée »
    est le 384e mot du francais et « tourné » le 3217e. Devant un humain qui
    choisit, c'est la frequence qui doit parler la premiere.
    """
    assert lexique.suggestion("ourné") is None
    assert lexique.propositions("ourné")[0] == "journée"


def test_les_propositions_gardent_la_casse(lexique):
    assert lexique.propositions("Ourné")[0] == "Journée"


def test_les_propositions_ne_repetent_pas_le_mot(lexique):
    assert "près" not in lexique.propositions("près")


def test_un_mot_sans_voisin_ne_propose_rien(lexique):
    assert lexique.propositions("zbeulotron") == []


def test_un_mot_rare_ne_gagne_pas_par_defaut(lexique):
    """« jesper » ne devient pas « jasper », meme sans concurrent.

    Une lettre d'ecart suffit, mais « jasper » est le 22 000e mot du francais :
    il est plus probable que le mot vise soit ailleurs.
    """
    assert lexique.suggestion("jesper") != "jasper"


def test_une_majuscule_ne_bloque_pas_sa_jumelle(lexique):
    """« reunion » vaut « réunion » — l'ile ne compte pas comme concurrente."""
    assert lexique.suggestion("reunion") == "réunion"



def test_le_cache_des_candidats_est_borne(mini, monkeypatch):
    """Papote tourne des semaines : un cache sans borne retenait chaque mot
    jamais tape, avec sa liste d'objets."""
    monkeypatch.setattr(lexique_mod, "MEMOIRE_CANDIDATS", 8)
    for i in range(40):
        mini.candidats(f"motinconnu{i}")
    assert len(mini._cache) <= 8


def test_le_cache_garde_les_plus_recents(mini, monkeypatch):
    monkeypatch.setattr(lexique_mod, "MEMOIRE_CANDIDATS", 3)
    for mot in ("aaa", "bbb", "ccc"):
        mini.candidats(mot)
    # On redemande « aaa » : il redevient le plus recent.
    mini.candidats("aaa")
    mini.candidats("ddd")
    cles = {cle[0] for cle in mini._cache}
    assert "aaa" in cles
    assert "bbb" not in cles
