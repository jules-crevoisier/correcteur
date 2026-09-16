# -*- coding: utf-8 -*-
"""Tests du menu de l'icone, sans pystray.

`pystray` n'est importe que dans `lancer()`, qui ouvre une vraie icone :
tout le reste de la classe se teste sans ecran ni barre des taches. Ce qui
compte ici, c'est ce que le menu propose — la seule porte de sortie quand la
fenetre n'est pas ouverte.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import config as config_mod, maj  # noqa: E402
from papote.app import Application  # noqa: E402
from papote.interface import InterfaceBarre  # noqa: E402


@pytest.fixture
def barre(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    app = Application(config=dict(config_mod.DEFAUTS), journal=lambda _m: None)
    return InterfaceBarre(app)


def test_sans_mise_a_jour_le_menu_propose_d_en_chercher(barre, monkeypatch):
    monkeypatch.setattr(maj, "en_attente", lambda: None)
    assert "Rechercher" in barre._libelle_maj()


def test_une_mise_a_jour_telechargee_par_la_fenetre_est_vue(barre, monkeypatch,
                                                            tmp_path):
    """La fenetre est un autre processus : `app.maj_prete` y reste vide.

    Le menu proposait donc encore de chercher une mise a jour deja prete, et
    le seul moyen de l'installer etait de fermer Papote a la main.
    """
    monkeypatch.setattr(maj, "en_attente", lambda: tmp_path / "Papote.nouveau.exe")
    monkeypatch.setattr(maj, "numero_en_attente", lambda: "v9.9.9")

    assert barre._maj_en_attente() == "v9.9.9"
    assert barre._libelle_maj() == "Redémarrer pour installer la version v9.9.9"


def test_un_numero_manquant_ne_fait_pas_disparaitre_l_offre(barre, monkeypatch,
                                                            tmp_path):
    monkeypatch.setattr(maj, "en_attente", lambda: tmp_path / "Papote.nouveau.exe")
    monkeypatch.setattr(maj, "numero_en_attente", lambda: None)

    assert barre._maj_en_attente() == ""
    assert barre._libelle_maj() == "Redémarrer pour installer la mise à jour"


def test_la_version_trouvee_par_l_icone_elle_meme_prime(barre, monkeypatch):
    monkeypatch.setattr(maj, "en_attente", lambda: None)
    barre.app.maj_prete = maj.Version("v8.8.8", "https://exemple/Papote.exe")
    assert "v8.8.8" in barre._libelle_maj()
