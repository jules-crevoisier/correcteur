# -*- coding: utf-8 -*-
"""Une seule Papote a la fois.

Deux Papote qui ecoutent le meme clavier, ce sont deux corrections pour une
frappe : la premiere efface trois lettres et en ecrit quatre, la seconde
efface trois lettres a son tour — mais le texte a change sous elle.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import instance  # noqa: E402


def test_le_premier_prend_le_verrou(tmp_path):
    verrou = instance.Verrou(tmp_path / "papote.verrou")
    verrou.prendre()
    try:
        assert (tmp_path / "papote.verrou").exists()
    finally:
        verrou.rendre()


def test_le_second_est_refuse(tmp_path):
    chemin = tmp_path / "papote.verrou"
    premier = instance.Verrou(chemin)
    premier.prendre()
    try:
        with pytest.raises(instance.Occupee):
            instance.Verrou(chemin).prendre()
    finally:
        premier.rendre()


def test_le_verrou_rendu_se_reprend(tmp_path):
    """Papote qu'on ferme et qu'on relance doit redemarrer."""
    chemin = tmp_path / "papote.verrou"
    premier = instance.Verrou(chemin)
    premier.prendre()
    premier.rendre()

    second = instance.Verrou(chemin)
    second.prendre()
    second.rendre()


def test_le_prendre_deux_fois_ne_fait_rien(tmp_path):
    verrou = instance.Verrou(tmp_path / "papote.verrou")
    verrou.prendre()
    verrou.prendre()
    verrou.rendre()


def test_le_rendre_sans_l_avoir_pris_ne_fait_rien(tmp_path):
    instance.Verrou(tmp_path / "papote.verrou").rendre()


def test_il_s_emploie_comme_gestionnaire_de_contexte(tmp_path):
    chemin = tmp_path / "papote.verrou"
    with instance.Verrou(chemin):
        with pytest.raises(instance.Occupee):
            instance.Verrou(chemin).prendre()
    # Rendu a la sortie du bloc.
    instance.Verrou(chemin).prendre()


def test_le_dossier_est_cree_au_besoin(tmp_path):
    verrou = instance.Verrou(tmp_path / "pas" / "encore" / "papote.verrou")
    verrou.prendre()
    verrou.rendre()


def test_le_numero_de_processus_est_ecrit(tmp_path):
    """Pour le diagnostic seulement : c'est le systeme qui arbitre."""
    import os

    chemin = tmp_path / "papote.verrou"
    verrou = instance.Verrou(chemin)
    verrou.prendre()
    verrou.rendre()
    assert chemin.read_text(encoding="ascii") == str(os.getpid())
