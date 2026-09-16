# -*- coding: utf-8 -*-
"""Tests de l'assemblage : ce que l'application dit quand quelque chose rate.

Un message d'erreur qui designe le mauvais coupable coute plus cher qu'une
absence de message : il envoie chercher le probleme la ou il n'est pas.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import config as config_mod, journal as journal_mod  # noqa: E402
from papote.app import Application  # noqa: E402
from papote.lexique import LexiqueIntrouvable  # noqa: E402


@pytest.fixture
def application(tmp_path, monkeypatch, lexique):
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    app = Application(config=dict(config_mod.DEFAUTS), journal=lambda _m: None)
    app._lexique = lexique
    app.messages = []
    app.notifier = lambda titre, corps: app.messages.append((titre, corps))
    return app


def attendre(application):
    """Le prechauffage part dans un fil : on l'attend."""
    import time

    application.prechauffer()
    for _ in range(100):
        if application.messages:
            return
        time.sleep(0.02)


def test_un_crochet_clavier_refuse_ne_parle_pas_du_dictionnaire(application,
                                                                monkeypatch):
    """Le vrai coupable doit etre nomme, et le raccourci reste utilisable."""
    class EcouteCassee:
        def activer(self):
            raise OSError("le systeme refuse le crochet clavier")

    monkeypatch.setattr(type(application), "ecoute",
                        property(lambda _self: EcouteCassee()))
    attendre(application)

    titre, corps = application.messages[0]
    assert "automatique" in titre.lower()
    assert "dictionnaire" not in titre.lower()
    assert "ctrl+alt+c" in corps.lower()
    assert "crochet clavier" in journal_mod.lire()


def test_un_dictionnaire_absent_le_dit(application, monkeypatch):
    def refuser(_self, _registre):
        raise LexiqueIntrouvable("donnees/lexique_fr.txt.gz est introuvable")

    monkeypatch.setattr(type(application), "correcteur_pour", refuser)
    attendre(application)

    titre, _corps = application.messages[0]
    assert "Dictionnaire" in titre


def test_sans_correction_automatique_aucun_crochet_n_est_pose(application,
                                                              monkeypatch):
    application.config["correction_auto"] = False
    poses = []
    monkeypatch.setattr(type(application), "ecoute",
                        property(lambda _s: poses.append(1)))
    application.prechauffer()
    import time
    time.sleep(0.3)
    assert poses == []
