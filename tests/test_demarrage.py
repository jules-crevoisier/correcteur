# -*- coding: utf-8 -*-
"""Tests du lancement automatique au demarrage de Windows.

Le registre est simule : ces tests tournent sur n'importe quel systeme.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from correcteur import demarrage  # noqa: E402


class FauxRegistre:
    """Imite la cle Run de Windows avec un dictionnaire."""

    def __init__(self, contenu=None):
        self.valeurs = dict(contenu or {})

    def lire(self, nom):
        return self.valeurs.get(nom)

    def ecrire(self, nom, valeur):
        self.valeurs[nom] = valeur

    def supprimer(self, nom):
        self.valeurs.pop(nom, None)


@pytest.fixture
def sous_windows(monkeypatch):
    """Fait croire aux fonctions qu'elles tournent sous Windows."""
    monkeypatch.setattr(demarrage, "disponible", lambda: True)


def test_inactif_au_depart(sous_windows):
    assert demarrage.actif(FauxRegistre()) is False


def test_activer_inscrit_une_commande(sous_windows):
    registre = FauxRegistre()
    commande = demarrage.activer(registre)
    assert registre.valeurs[demarrage.NOM_VALEUR] == commande
    assert demarrage.actif(registre) is True


def test_desactiver_retire_la_cle(sous_windows):
    registre = FauxRegistre({demarrage.NOM_VALEUR: "peu importe"})
    demarrage.desactiver(registre)
    assert demarrage.actif(registre) is False


def test_desactiver_est_idempotent(sous_windows):
    registre = FauxRegistre()
    demarrage.desactiver(registre)
    demarrage.desactiver(registre)
    assert demarrage.actif(registre) is False


def test_basculer_fait_des_allers_retours(sous_windows):
    registre = FauxRegistre()
    assert demarrage.basculer(registre) is True
    assert demarrage.actif(registre) is True
    assert demarrage.basculer(registre) is False
    assert demarrage.actif(registre) is False


def test_activer_deux_fois_ne_cree_quune_entree(sous_windows):
    registre = FauxRegistre()
    demarrage.activer(registre)
    demarrage.activer(registre)
    assert len(registre.valeurs) == 1


def test_la_commande_est_entre_guillemets(sous_windows):
    """Un chemin contenant des espaces doit rester interpretable."""
    commande = demarrage.commande_lancement()
    assert commande.startswith('"')
    assert commande.count('"') % 2 == 0


def test_synchroniser_repare_un_chemin_obsolete(sous_windows):
    """Deplacer l'application ne doit pas casser le demarrage automatique."""
    registre = FauxRegistre({demarrage.NOM_VALEUR: r'"C:\ancien\Correcteur.exe"'})
    assert demarrage.synchroniser(registre) is True
    assert registre.valeurs[demarrage.NOM_VALEUR] == demarrage.commande_lancement()


def test_synchroniser_ne_reactive_pas_ce_qui_est_desactive(sous_windows):
    """Si l'utilisateur a desactive le demarrage, on n'y revient pas."""
    registre = FauxRegistre()
    assert demarrage.synchroniser(registre) is False
    assert demarrage.actif(registre) is False


def test_hors_windows_rien_ne_seffectue(monkeypatch):
    monkeypatch.setattr(demarrage.os, "name", "posix")
    registre = FauxRegistre()
    assert demarrage.disponible() is False
    assert demarrage.actif(registre) is False
    with pytest.raises(RuntimeError):
        demarrage.activer(registre)
