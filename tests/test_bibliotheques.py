# -*- coding: utf-8 -*-
"""Le moteur vocal, telecharge au premier usage.

Rien ici ne touche au reseau. Ce qui compte, c'est que le module refuse tout
ce qui sort de l'ordinaire — une empreinte qui ne correspond pas, une
archive qui ecrirait ailleurs — et qu'il ne laisse jamais une bibliotheque a
moitie installee.

La verification de l'empreinte n'est pas une precaution contre les coupures
de reseau : ce qui est telecharge ici est du **code**, et il sera importe.
"""

import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import bibliotheques as bib  # noqa: E402


def roue_factice(contenu=b"# vosk\n", nom="vosk") -> bytes:
    """Une roue minuscule, avec le module que le module attend."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zip_:
        zip_.writestr(f"{nom}/__init__.py", contenu)
        zip_.writestr(f"{nom}/libvosk.dll", b"MZ")
    return tampon.getvalue()


@pytest.fixture
def faux_pypi(monkeypatch, tmp_path):
    """Remplace le telechargement par une roue fabriquee ici."""
    from papote import config as config_mod

    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    etat = {"octets": roue_factice()}

    def faux_recuperer(roue, archive, avancement):
        archive.write_bytes(etat["octets"])
        if avancement:
            avancement(len(etat["octets"]), len(etat["octets"]))

    monkeypatch.setattr(bib, "_recuperer", faux_recuperer)

    def avec(octets):
        etat["octets"] = octets
        return bib.Roue(paquet="vosk", nom="vosk", role="le moteur",
                        fichier="vosk.whl", url="https://exemple/vosk.whl",
                        empreinte=hashlib.sha256(octets).hexdigest(),
                        taille=len(octets))
    return avec


# -- l'installation ----------------------------------------------------------

def test_la_roue_est_depliee(faux_pypi, tmp_path):
    roue = faux_pypi(roue_factice())
    assert not bib.installee(roue)
    bib.telecharger(roue)
    assert bib.installee(roue)
    assert (tmp_path / "bibliotheques" / "vosk" / "libvosk.dll").is_file()


def test_le_dossier_passe_sur_le_chemin_des_imports(faux_pypi, tmp_path,
                                                    monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    bib.telecharger(faux_pypi(roue_factice()))
    assert str(tmp_path / "bibliotheques") in sys.path


def test_une_seconde_installation_ne_retelecharge_pas(faux_pypi, monkeypatch):
    roue = faux_pypi(roue_factice())
    bib.telecharger(roue)

    def interdit(*_a, **_k):
        raise AssertionError("elle a été retéléchargée")

    monkeypatch.setattr(bib, "_recuperer", interdit)
    bib.telecharger(roue)


# -- ce que le module refuse -------------------------------------------------

def test_une_empreinte_qui_ne_correspond_pas_fait_tout_annuler(faux_pypi,
                                                               tmp_path):
    """C'est du code qui sera importé : on ne déplie pas au petit bonheur."""
    roue = faux_pypi(roue_factice())
    menteuse = bib.Roue(paquet=roue.paquet, nom=roue.nom, role=roue.role,
                        fichier=roue.fichier, url=roue.url,
                        empreinte="0" * 64, taille=roue.taille)
    with pytest.raises(bib.BibliothequeIntrouvable):
        bib.telecharger(menteuse)
    assert not (tmp_path / "bibliotheques" / "vosk").exists()


def test_une_archive_qui_ecrirait_ailleurs_est_refusee(faux_pypi, tmp_path):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zip_:
        zip_.writestr("../dehors.py", b"# non")
    with pytest.raises(bib.BibliothequeIntrouvable):
        bib.telecharger(faux_pypi(tampon.getvalue()))
    assert not (tmp_path.parent / "dehors.py").exists()


def test_une_archive_sans_le_module_attendu_est_refusee(faux_pypi, tmp_path):
    with pytest.raises(bib.BibliothequeIntrouvable):
        bib.telecharger(faux_pypi(roue_factice(nom="autre_chose")))
    assert not (tmp_path / "bibliotheques" / "vosk").exists()


def test_une_archive_illisible_est_refusee(faux_pypi):
    with pytest.raises(bib.BibliothequeIntrouvable):
        bib.telecharger(faux_pypi(b"pas une archive"))


# -- l'etat ------------------------------------------------------------------

def test_sans_rien_d_installe_le_poids_est_nul(faux_pypi, tmp_path):
    assert bib.poids_installe() == 0


def test_le_poids_se_compte_une_fois_installe(faux_pypi):
    bib.telecharger(faux_pypi(roue_factice()))
    assert bib.poids_installe() > 0


def test_rendre_importable_sans_dossier_ne_fait_rien(monkeypatch, tmp_path):
    from papote import config as config_mod

    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    avant = list(sys.path)
    bib.rendre_importable()
    assert sys.path == avant


def test_l_adresse_et_l_empreinte_vont_ensemble():
    """Changer de version, c'est changer les deux lignes ensemble."""
    assert bib.VOSK.url.endswith(bib.VOSK.fichier)
    assert len(bib.VOSK.empreinte) == 64
    assert bib.VOSK.url.startswith("https://")


# -- ce que dit un modele introuvable ----------------------------------------

def test_un_404_designe_le_defaut_plutot_que_la_connexion(monkeypatch,
                                                          tmp_path):
    """L'adresse du grand modele n'a pas pu etre verifiee a l'ecriture.

    Si elle est fausse, le message doit envoyer au bon endroit du premier
    coup — « vérifiez votre connexion » ferait chercher pendant une heure.
    """
    import urllib.error

    from papote import config as config_mod, modeles

    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)

    def introuvable(*_a, **_k):
        raise urllib.error.HTTPError("u", 404, "Not Found", None,
                                     io.BytesIO(b""))

    monkeypatch.setattr(modeles.urllib.request, "urlopen", introuvable)
    with pytest.raises(modeles.ModeleIntrouvable) as capture:
        modeles.telecharger(modeles.PRECIS)
    message = str(capture.value)
    assert "connexion" not in message
    assert modeles.PRECIS.url in message
    assert "défaut de Papote" in message
