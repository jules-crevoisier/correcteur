# -*- coding: utf-8 -*-
"""Tests de ce que Papote retient de vos habitudes."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import apprentissage  # noqa: E402


@pytest.fixture
def journal():
    return apprentissage.Journal(seuil=3)


def test_au_depart_il_ne_sait_rien(journal):
    assert journal.fautes_frequentes() == []
    assert journal.total_corrections() == 0


def test_les_corrections_sont_comptees(journal):
    journal.correction_appliquee("sa ", "ça ")
    journal.correction_appliquee("sa ", "ça ")
    journal.correction_appliquee("malgres ", "malgré ")
    # Seule la forme corrigee est retenue : la faute, elle, n'est pas un
    # mot du dictionnaire, et rien ne la distingue d'un mot de passe.
    assert journal.fautes_frequentes() == [("ça", 2), ("malgré", 1)]
    assert journal.total_corrections() == 3


def test_deux_annulations_ne_suffisent_pas(journal):
    assert journal.correction_annulee("zbeul", "ORTHOGRAPHE") == []
    assert journal.correction_annulee("zbeul", "ORTHOGRAPHE") == []


def test_la_troisieme_annulation_apprend_le_mot(journal):
    for _ in range(2):
        journal.correction_annulee("zbeul", "ORTHOGRAPHE")
    lecons = journal.correction_annulee("zbeul", "ORTHOGRAPHE")
    assert [(l.genre, l.valeur) for l in lecons] == [("mot", "zbeul")]


def test_la_lecon_ne_se_repete_pas(journal):
    for _ in range(3):
        journal.correction_annulee("zbeul", "ORTHOGRAPHE")
    assert journal.correction_annulee("zbeul", "ORTHOGRAPHE") == []


def test_trois_annulations_d_une_regle_la_mettent_en_cause(journal):
    lecons = []
    for i in range(3):
        lecons += journal.correction_annulee(f"mot{i}", "SE_CE")
    assert [(l.genre, l.valeur) for l in lecons] == [("regle", "SE_CE")]


def test_l_orthographe_n_est_pas_une_regle_a_eteindre(journal):
    """« ORTHOGRAPHE » n'est pas une regle de style : on ne l'eteint pas."""
    lecons = []
    for i in range(5):
        lecons += journal.correction_annulee(f"mot{i}", "ORTHOGRAPHE")
    assert all(lecon.genre != "regle" for lecon in lecons)


def test_un_mot_appris_repart_de_zero(journal):
    for _ in range(3):
        journal.correction_annulee("zbeul", "ORTHOGRAPHE")
    journal.oublier_mot("zbeul")
    assert journal.annulations_mot.get("zbeul") is None


def test_vider_efface_tout(journal):
    journal.correction_appliquee("sa", "ça")
    journal.correction_annulee("zbeul", "ORTHOGRAPHE")
    journal.vider()
    assert journal.total_corrections() == 0
    assert journal.annulations_mot == {}


# -- fichier ----------------------------------------------------------------

def test_ce_qui_est_ecrit_se_relit(tmp_path, journal):
    chemin = tmp_path / "apprentissage.json"
    journal.correction_appliquee("sa", "ça")
    journal.correction_annulee("zbeul", "SE_CE")
    journal.enregistrer(chemin)

    relu = apprentissage.charger(chemin)
    assert relu.fautes_frequentes() == [("ça", 1)]
    assert relu.annulations_mot["zbeul"] == 1


def test_un_fichier_absent_donne_un_journal_vierge(tmp_path):
    assert apprentissage.charger(tmp_path / "rien.json").total_corrections() == 0


def test_un_fichier_abime_ne_bloque_rien(tmp_path):
    chemin = tmp_path / "apprentissage.json"
    chemin.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert apprentissage.charger(chemin).total_corrections() == 0


def test_les_valeurs_absurdes_sont_ecartees(tmp_path):
    chemin = tmp_path / "apprentissage.json"
    chemin.write_text(json.dumps({
        "corrections": {"ça": 3, "bidon": "beaucoup", "negatif": -1},
    }), encoding="utf-8")
    assert apprentissage.charger(chemin).fautes_frequentes() == [("ça", 3)]


def test_le_fichier_ne_grossit_pas_indefiniment(tmp_path, journal):
    for i in range(apprentissage.MEMOIRE + 200):
        journal.correction_appliquee(f"faute{i}", f"correction{i}")
    journal.enregistrer(tmp_path / "apprentissage.json")

    with (tmp_path / "apprentissage.json").open(encoding="utf-8") as f:
        ecrit = json.load(f)
    assert len(ecrit["corrections"]) == apprentissage.MEMOIRE


def test_rien_a_ecrire_n_ecrit_rien(tmp_path, journal):
    chemin = tmp_path / "apprentissage.json"
    journal.enregistrer(chemin)
    assert not chemin.exists()


# ---------------------------------------------------------------------------
# Ce qui enfle pendant que Papote tourne
#
# Le fichier ne retient que les MEMOIRE premieres entrees. En memoire, rien
# ne coupait — et Papote tourne des semaines d'affilee.
# ---------------------------------------------------------------------------

def test_les_compteurs_ne_grossissent_pas_sans_fin():
    journal = apprentissage.Journal()
    for i in range(apprentissage.MEMOIRE * 6):
        journal.correction_appliquee(f"faute{i}", f"correction{i}")
    assert len(journal.corrections) <= apprentissage.MEMOIRE * 4


def test_l_elagage_garde_les_plus_frequentes():
    journal = apprentissage.Journal()
    for _ in range(50):
        journal.correction_appliquee("sa", "ça")
    for i in range(apprentissage.MEMOIRE * 6):
        journal.correction_appliquee(f"faute{i}", f"correction{i}")
    assert journal.corrections["ça"] == 50
