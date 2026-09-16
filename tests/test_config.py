# -*- coding: utf-8 -*-
"""Tests des reglages : valeurs par defaut, migration, ecriture."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import config as config_mod  # noqa: E402


@pytest.fixture
def reglages(tmp_path, monkeypatch):
    """Isole les reglages dans un dossier temporaire."""
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    return tmp_path / "config.json"


def test_le_fichier_est_cree_au_premier_lancement(reglages):
    config = config_mod.charger()
    assert reglages.exists()
    assert config["correction_auto"] is True
    assert config["raccourci"] == "ctrl+alt+c"


def test_un_fichier_incomplet_garde_les_defauts(reglages):
    reglages.write_text('{"raccourci": "f9"}', encoding="utf-8")
    config = config_mod.charger()
    assert config["raccourci"] == "f9"
    assert config["correction_auto"] is True


def test_un_fichier_illisible_ne_bloque_pas_le_demarrage(reglages):
    reglages.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert config_mod.charger()["raccourci"] == "ctrl+alt+c"


def test_les_anciens_reglages_sont_repris(reglages):
    """Une version precedente appelait « mots_perso » autrement."""
    reglages.write_text(json.dumps({
        "lexique_perso": ["Valorant", "Kayn"],
        "regles_optionnelles": {"UPPERCASE_SENTENCE_START": True},
    }), encoding="utf-8")

    config = config_mod.charger()
    assert config["mots_perso"] == ["Valorant", "Kayn"]
    assert "lexique_perso" not in config
    assert config["regles_optionnelles"]["MAJUSCULE_PHRASE"] is True


def test_les_regles_de_l_ancien_moteur_sont_oubliees(reglages):
    """« P_V_PAS » etait une regle de LanguageTool : elle n'existe plus."""
    reglages.write_text(json.dumps({
        "regles_optionnelles": {"P_V_PAS": False, "PONCTUATION_POINT": True},
    }), encoding="utf-8")

    regles = config_mod.charger()["regles_optionnelles"]
    assert "P_V_PAS" not in regles
    assert regles["PONCTUATION_POINT"] is True


def test_l_ecriture_est_relisible(reglages):
    config = config_mod.charger()
    config["mots_perso"] = ["Zbeul"]
    config["remplacements_perso"] = {"ptetre": "peut-être"}
    config_mod.sauvegarder(config)

    relu = config_mod.charger()
    assert relu["mots_perso"] == ["Zbeul"]
    assert relu["remplacements_perso"] == {"ptetre": "peut-être"}


def test_l_ecriture_ne_laisse_pas_de_fichier_provisoire(reglages):
    config_mod.sauvegarder(config_mod.DEFAUTS)
    assert list(reglages.parent.glob("*.tmp")) == []


def test_les_reglages_de_l_ancien_nom_sont_repris(tmp_path, monkeypatch):
    """L'outil s'appelait « Correcteur » : on ne perd pas ce qu'il savait."""
    monkeypatch.setattr(config_mod, "_base_config", lambda: tmp_path)
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path / "Papote")

    ancien = tmp_path / config_mod.ANCIEN_DOSSIER
    ancien.mkdir()
    (ancien / "config.json").write_text(json.dumps({
        "raccourci": "f9",
        "lexique_perso": ["Kayn"],
        "remplacements_perso": {"ptetre": "peut-être"},
    }), encoding="utf-8")

    config = config_mod.charger()
    assert config["raccourci"] == "f9"
    assert config["mots_perso"] == ["Kayn"]
    assert config["remplacements_perso"] == {"ptetre": "peut-être"}
    # Et ils sont desormais ecrits sous le nouveau nom.
    assert (tmp_path / "Papote" / "config.json").exists()


def test_les_reglages_deja_migres_ne_sont_pas_ecrases(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "_base_config", lambda: tmp_path)
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path / "Papote")

    ancien = tmp_path / config_mod.ANCIEN_DOSSIER
    ancien.mkdir()
    (ancien / "config.json").write_text('{"raccourci": "f9"}', encoding="utf-8")

    nouveau = tmp_path / "Papote"
    nouveau.mkdir()
    (nouveau / "config.json").write_text('{"raccourci": "f8"}', encoding="utf-8")

    assert config_mod.charger()["raccourci"] == "f8"


# ---------------------------------------------------------------------------
# Un fichier de reglages abime
#
# Le fichier est du JSON ecrit par nous, mais il peut avoir ete edite a la
# main, tronque par une coupure, ou ecrase par un autre programme. Aucun de
# ces cas ne doit empecher Papote de demarrer.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("contenu", [
    "[1, 2, 3]",            # du JSON valide, mais pas un objet
    '"bonjour"',
    "42",
    "null",
    "true",
    "{",                    # tronque
    "",                     # vide
    "\x00\x01\x02",         # binaire
])
def test_un_fichier_abime_rend_les_reglages_d_origine(tmp_path, monkeypatch,
                                                      contenu):
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    (tmp_path / "config.json").write_text(contenu, encoding="utf-8",
                                          errors="ignore")
    config = config_mod.charger()
    assert config["registre"] == config_mod.DEFAUTS["registre"]
    assert config["correction_auto"] is True


def test_une_valeur_de_la_mauvaise_forme_ne_fait_pas_tomber_le_chargement(
        tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        '{"regles_optionnelles": "toutes"}', encoding="utf-8")
    # « regles_optionnelles » attend un dictionnaire ; une chaine ne doit pas
    # faire tomber le demarrage.
    assert config_mod.charger()["correction_auto"] is True


def test_un_dossier_ou_l_on_ne_peut_pas_ecrire_n_empeche_pas_de_demarrer(
        tmp_path, monkeypatch):
    """Un profil itinerant verrouille, un disque plein : on corrige quand meme."""
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path / "x")

    def refuser(_config):
        raise OSError("lecture seule")

    monkeypatch.setattr(config_mod, "sauvegarder", refuser)
    config = config_mod.charger()
    assert config["registre"] == config_mod.DEFAUTS["registre"]
