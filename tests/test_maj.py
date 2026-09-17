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

from papote import maj  # noqa: E402


def publication(tag="v1.0.20", nom="Papote.exe",
                adresse="https://github.com/x/y/releases/download/v1.0.20/Papote.exe",
                empreinte=None):
    return json.dumps({
        "tag_name": tag,
        "assets": [{"name": nom, "browser_download_url": adresse,
                    "digest": empreinte}],
    }).encode("utf-8")


@pytest.fixture
def github(monkeypatch, tmp_path):
    """Remplace les appels reseau par des reponses toutes faites.

    Le cache des reponses est detourne vers un dossier jetable : sans cela
    les tests ecriraient dans la vraie configuration de la machine, et
    liraient l'ETag laisse par le test precedent.
    """
    monkeypatch.setattr(maj, "_chemin_cache",
                        lambda: tmp_path / "derniere_version.json")
    reponses = {"json": publication(), "fichier": b"MZ nouvel executable"}

    class Reponse(io.BytesIO):
        """Une reponse HTTP de doublure.

        Elle porte des en-tetes depuis que la verification est
        conditionnelle : c'est l'ETag qui permet a GitHub de repondre
        « rien n'a change », et une reponse sans en-tetes ne ressemblerait
        plus a ce que le module recoit vraiment.
        """

        headers = {"ETag": '"abc123"'}

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
    """Fait croire au module qu'il tourne depuis un Papote.exe."""
    executable = tmp_path / "Papote.exe"
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
    assert version.adresse.endswith("Papote.exe")


def test_une_adresse_qui_n_est_pas_en_https_est_refusee(github):
    github["json"] = publication(adresse="http://ailleurs.example/Papote.exe")
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


# -- le numero de la version telechargee ------------------------------------

def test_le_numero_telecharge_est_note_a_cote(github, installe):
    """L'icone et la fenetre sont deux processus : le numero passe par un fichier."""
    version = maj.disponible()
    maj.installer_maintenant(version)
    assert maj.numero_en_attente() == version.numero


def test_sans_mise_a_jour_en_attente_il_n_y_a_pas_de_numero(installe):
    assert maj.numero_en_attente() is None


def test_le_numero_disparait_avec_le_menage(github, installe):
    maj.installer_maintenant(maj.disponible())
    maj.en_attente().unlink()
    maj.nettoyer()
    assert not (installe.parent / maj.NUMERO).exists()


def test_un_numero_illisible_ne_casse_rien(github, installe):
    """Le numero n'est qu'un confort : son absence ne bloque pas le redemarrage."""
    maj.installer_maintenant(maj.disponible())
    (installe.parent / maj.NUMERO).write_text("", encoding="utf-8")
    assert maj.numero_en_attente() is None
    assert maj.en_attente() is not None


# -- relancer un programme fige ---------------------------------------------

def test_l_environnement_de_relance_est_deballe(monkeypatch):
    """Le lanceur de PyInstaller ne doit pas suivre le nouveau processus.

    Il note dans l'environnement ou il a deballe l'executable. Transmises
    telles quelles, ces variables font croire au nouveau Papote qu'il est le
    second etage d'un demarrage deja fait : il cherche ses fichiers dans le
    dossier temporaire de l'ancien et s'arrete sur « Failed to start embedded
    python interpreter ».
    """
    monkeypatch.setenv("_MEIPASS2", r"C:\Temp\_MEI00002a102")
    monkeypatch.setenv("_PYI_ARCHIVE_FILE", r"C:\Papote\Papote.exe")
    monkeypatch.setenv("_PYI_PARENT_PROCESS_LEVEL", "1")
    monkeypatch.setenv("PATH", "/usr/bin")

    propre = maj.environnement_de_relance()

    assert "_MEIPASS2" not in propre
    assert not [nom for nom in propre if nom.startswith("_PYI")]
    # Tout le reste doit passer : le nouveau Papote a besoin du meme
    # environnement que l'ancien.
    assert propre["PATH"] == "/usr/bin"


def test_la_mise_en_place_relance_avec_un_environnement_propre(installe, tmp_path,
                                                               monkeypatch):
    """C'est ici que le defaut se voyait : la mise a jour ne demarrait pas."""
    monkeypatch.setenv("_MEIPASS2", r"C:\Temp\_MEI00002a102")
    lancements = []
    monkeypatch.setattr(
        maj.subprocess, "Popen",
        lambda commande, **options: lancements.append((commande, options)),
    )
    (tmp_path / maj.NOUVEAU).write_bytes(b"MZ nouvel executable")

    assert maj.appliquer() is True
    _commande, options = lancements[0]
    assert "_MEIPASS2" not in options["env"]




# -- ce que le serveur refuse, dit en francais --------------------------------
#
# Le message brut partait tel quel dans une notification Windows :
#
#     Vérification impossible : serveur injoignable :
#     HTTP Error 403: rate limit exceeded
#
# Le serveur n'etait pas injoignable — il a repondu, et vite. « rate limit
# exceeded » est de l'anglais dans un produit qui n'en dit pas un mot
# ailleurs. Et rien n'indiquait quoi faire, alors que la reponse le disait.

def _refus(code, raison, **entetes):
    import email.message

    message = email.message.Message()
    for cle, valeur in entetes.items():
        message[cle.replace("_", "-")] = valeur
    return maj.urllib.error.HTTPError("u", code, raison, message,
                                      io.BytesIO(b""))


@pytest.mark.parametrize("erreur,attendu", [
    (_refus(403, "rate limit exceeded", X_RateLimit_Remaining="0"),
     "GitHub limite le nombre de vérifications par heure"),
    (_refus(429, "Too Many Requests", X_RateLimit_Remaining="0"),
     "GitHub limite le nombre de vérifications par heure"),
    (_refus(403, "Forbidden"), "GitHub a refusé la demande."),
    (_refus(404, "Not Found"), "Aucune version publiée"),
    (_refus(503, "Service Unavailable"), "GitHub est en panne"),
    (_refus(418, "I'm a teapot"), "GitHub a répondu 418."),
])
def test_le_refus_du_serveur_se_dit_en_francais(erreur, attendu):
    message = maj._expliquer(erreur)
    assert attendu in message
    assert "rate limit" not in message
    assert "HTTP Error" not in message


def test_la_limite_dit_quand_reessayer():
    """Dire « plus tard » sans dire quand, c'est faire recliquer."""
    import time

    erreur = _refus(403, "rate limit exceeded", X_RateLimit_Remaining="0",
                    X_RateLimit_Reset=str(int(time.time()) + 12 * 60))
    assert "12 minutes" in maj._expliquer(erreur)


def test_une_heure_de_reprise_absurde_est_ignoree():
    """Une horloge decalee ne doit pas annoncer « dans 4000 minutes »."""
    erreur = _refus(403, "rate limit exceeded", X_RateLimit_Remaining="0",
                    X_RateLimit_Reset="99999999999")
    assert "Réessayez" not in maj._expliquer(erreur)


def test_le_message_ne_parle_plus_de_serveur_injoignable(monkeypatch, tmp_path):
    """Un 403 n'est pas une panne de reseau, et ne doit pas le dire."""
    monkeypatch.setattr(maj, "_chemin_cache", lambda: tmp_path / "c.json")

    def refuser(*_a, **_k):
        raise _refus(403, "rate limit exceeded", X_RateLimit_Remaining="0")

    monkeypatch.setattr(maj.urllib.request, "urlopen", refuser)
    with pytest.raises(maj.MiseAJourImpossible) as capture:
        maj.derniere_version()
    assert "injoignable" not in str(capture.value)


# -- la demande conditionnelle ------------------------------------------------
#
# GitHub n'accorde que soixante demandes par heure a qui ne s'annonce pas.
# Une demande a laquelle il repond « rien n'a change » ne compte pas dans ce
# quota : verifier dix fois de suite ne doit donc couter qu'une demande.

def test_l_etag_est_renvoye_a_la_demande_suivante(github):
    maj.derniere_version()

    envoyees = []

    def capturer(requete, timeout=None):
        envoyees.append(dict(requete.headers))
        raise _refus(304, "Not Modified")

    monkey = pytest.MonkeyPatch()
    monkey.setattr(maj.urllib.request, "urlopen", capturer)
    try:
        version = maj.derniere_version()
    finally:
        monkey.undo()

    assert envoyees and "If-none-match" in envoyees[0]
    # Et la reponse mise de cote fait l'affaire.
    assert version.numero == "v1.0.20"


def test_sans_cache_un_304_reste_une_erreur(monkeypatch, tmp_path):
    """Repondre « rien n'a change » sans qu'on ait rien : on ne devine pas."""
    monkeypatch.setattr(maj, "_chemin_cache", lambda: tmp_path / "vide.json")

    def refuser(*_a, **_k):
        raise _refus(304, "Not Modified")

    monkeypatch.setattr(maj.urllib.request, "urlopen", refuser)
    with pytest.raises(maj.MiseAJourImpossible):
        maj.derniere_version()


def test_un_cache_illisible_ne_casse_rien(github, tmp_path):
    maj._chemin_cache().write_text("{ pas du json", encoding="utf-8")
    assert maj.derniere_version().numero == "v1.0.20"


def test_le_cache_ne_contient_que_la_reponse_de_github(github):
    maj.derniere_version()
    garde = json.loads(maj._chemin_cache().read_text(encoding="utf-8"))
    assert set(garde) == {"etag", "corps"}
    assert json.loads(garde["corps"])["tag_name"] == "v1.0.20"
