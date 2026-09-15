# -*- coding: utf-8 -*-
"""Tests de la mise a jour automatique.

Rien ici ne touche au reseau : les reponses de GitHub sont simulees. Ce qui
compte, c'est que le module refuse tout ce qui sort de l'ordinaire — une
adresse qui n'est pas la sienne, un fichier dont l'empreinte ne correspond
pas — et qu'il ne casse jamais l'installation existante.
"""

import hashlib
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from correcteur import maj  # noqa: E402


def publication(tag="v1.0.20", nom="Correcteur.exe",
                adresse="https://github.com/x/y/releases/download/v1.0.20/Correcteur.exe",
                empreinte=None):
    return json.dumps({
        "tag_name": tag,
        "assets": [{"name": nom, "browser_download_url": adresse,
                    "digest": empreinte}],
    }).encode("utf-8")


@pytest.fixture
def github(monkeypatch):
    """Remplace les appels reseau par des reponses toutes faites."""
    reponses = {"json": publication(), "fichier": b"MZ nouvel executable"}

    class Reponse(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *_): self.close()

    def faux_urlopen(requete, timeout=None):
        adresse = requete.full_url if hasattr(requete, "full_url") else requete
        if adresse.startswith("https://api.github.com"):
            return Reponse(reponses["json"])
        return Reponse(reponses["fichier"])

    monkeypatch.setattr(maj.urllib.request, "urlopen", faux_urlopen)
    return reponses


@pytest.fixture
def installe(monkeypatch, tmp_path):
    """Fait croire au module qu'il tourne depuis un Correcteur.exe."""
    executable = tmp_path / "Correcteur.exe"
    executable.write_bytes(b"MZ ancien executable")
    monkeypatch.setattr(maj, "compilee", lambda: True)
    monkeypatch.setattr(maj, "dossier", lambda: tmp_path)
    monkeypatch.setattr(maj.sys, "executable", str(executable))
    return executable


# -- comparaison des numeros ------------------------------------------------

@pytest.mark.parametrize("candidate,reference,attendu", [
    ("v1.0.14", "1.0.11", True),
    ("v1.0.11", "1.0.14", False),
    ("v1.0.14", "1.0.14", False),
    ("v1.1.0", "1.0.99", True),
    ("v1.0.2", "1.0.10", False),      # 2 vient bien avant 10
    ("v2.0.0", "1.9.9", True),
    ("bidon", "1.0.0", False),        # un numero illisible n'est jamais plus recent
])
def test_comparaison_des_versions(candidate, reference, attendu):
    assert maj.plus_recente(candidate, reference) is attendu


# -- lecture de la derniere version -----------------------------------------

def test_la_derniere_version_est_lue(github):
    version = maj.derniere_version()
    assert version.numero == "v1.0.20"
    assert version.adresse.endswith("Correcteur.exe")


def test_une_adresse_qui_n_est_pas_en_https_est_refusee(github):
    github["json"] = publication(adresse="http://ailleurs.example/Correcteur.exe")
    with pytest.raises(maj.MiseAJourImpossible):
        maj.derniere_version()


def test_une_version_sans_executable_est_refusee(github):
    github["json"] = publication(nom="autre-chose.zip")
    with pytest.raises(maj.MiseAJourImpossible):
        maj.derniere_version()


def test_un_serveur_muet_ne_fait_pas_tomber_l_application(monkeypatch):
    def refuser(*_a, **_k):
        raise OSError("pas de reseau")

    monkeypatch.setattr(maj.urllib.request, "urlopen", refuser)
    with pytest.raises(maj.MiseAJourImpossible):
        maj.derniere_version()


def test_depuis_les_sources_rien_ne_se_met_a_jour(github, monkeypatch):
    monkeypatch.setattr(maj, "compilee", lambda: False)
    assert maj.disponible() is None


# -- telechargement ---------------------------------------------------------

def test_le_telechargement_depose_le_fichier_a_cote(github, installe, tmp_path):
    version = maj.derniere_version()
    depose = maj.telecharger(version)
    assert depose == tmp_path / maj.NOUVEAU
    assert depose.read_bytes() == b"MZ nouvel executable"
    # L'executable en place n'a pas bouge.
    assert installe.read_bytes() == b"MZ ancien executable"


def test_une_empreinte_conforme_est_acceptee(github, installe):
    empreinte = hashlib.sha256(github["fichier"]).hexdigest()
    github["json"] = publication(empreinte=f"sha256:{empreinte}")
    assert maj.telecharger(maj.derniere_version()).exists()


def test_une_empreinte_qui_ne_correspond_pas_fait_tout_annuler(github, installe,
                                                               tmp_path):
    github["json"] = publication(empreinte="sha256:" + "0" * 64)
    with pytest.raises(maj.MiseAJourImpossible):
        maj.telecharger(maj.derniere_version())
    assert not (tmp_path / maj.NOUVEAU).exists()
    assert list(tmp_path.glob("*.partiel")) == []


# -- mise en place ----------------------------------------------------------

def test_sans_rien_en_attente_le_demarrage_suit_son_cours(installe):
    assert maj.en_attente() is None
    assert maj.appliquer() is False


def test_la_version_telechargee_prend_la_place(installe, tmp_path, monkeypatch):
    lancements = []
    monkeypatch.setattr(maj.subprocess, "Popen",
                        lambda commande, **_k: lancements.append(commande))
    (tmp_path / maj.NOUVEAU).write_bytes(b"MZ nouvel executable")

    assert maj.appliquer() is True
    assert installe.read_bytes() == b"MZ nouvel executable"
    assert (tmp_path / maj.ANCIEN).read_bytes() == b"MZ ancien executable"
    assert not (tmp_path / maj.NOUVEAU).exists()
    assert lancements and lancements[0][0] == str(installe)


def test_l_ancienne_version_est_effacee_ensuite(installe, tmp_path):
    (tmp_path / maj.ANCIEN).write_bytes(b"MZ ancien executable")
    maj.nettoyer()
    assert not (tmp_path / maj.ANCIEN).exists()


def test_un_echec_de_mise_en_place_laisse_l_executable_intact(installe, tmp_path,
                                                              monkeypatch):
    (tmp_path / maj.NOUVEAU).write_bytes(b"MZ nouvel executable")

    vrai_rename = Path.rename
    appels = []

    def rename_capricieux(self, cible):
        appels.append(cible)
        if len(appels) == 2:      # le second renommage echoue
            raise OSError("verrouille")
        return vrai_rename(self, cible)

    monkeypatch.setattr(Path, "rename", rename_capricieux)
    assert maj.appliquer() is False
    assert installe.exists()
    assert installe.read_bytes() == b"MZ ancien executable"
