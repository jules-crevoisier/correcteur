# -*- coding: utf-8 -*-
"""Tests de la fenetre en HTML, sans navigateur.

On ne juge pas ici de l'apparence — cela se regarde, avec
`outils/apercu_fenetre.py`. On verifie les jointures, qui sont ce qui casse
en silence : un identifiant renomme dans le HTML et pas dans le JavaScript,
une methode Python supprimee que la page appelle encore. Rien de tout cela
ne leve a la compilation ; cela se decouvre en ouvrant la fenetre, ou pire,
chez quelqu'un d'autre.
"""

import re
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import passerelle as passerelle_mod  # noqa: E402
from papote.chemins import dossier_web  # noqa: E402


@pytest.fixture(scope="module")
def page() -> str:
    return (dossier_web() / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def script() -> str:
    return (dossier_web() / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def style() -> str:
    return (dossier_web() / "style.css").read_text(encoding="utf-8")


# -- les fichiers sont la ---------------------------------------------------

def test_la_page_et_ses_deux_fichiers_existent():
    dossier = dossier_web()
    for nom in ("index.html", "style.css", "app.js"):
        assert (dossier / nom).is_file(), nom


def test_la_page_reference_bien_ses_fichiers(page):
    assert 'href="style.css"' in page
    assert 'src="app.js"' in page


def test_rien_n_est_charge_depuis_le_reseau(page, style, script):
    """Une fenetre qui attend un serveur est une fenetre qui s'ouvre vide.

    Papote fonctionne sans connexion ; sa fenetre aussi.
    """
    # L'espace de noms SVG n'est pas une adresse a joindre : c'est un
    # identifiant, et le navigateur ne le telecharge jamais.
    espace_svg = "http://www.w3.org/2000/svg"
    for contenu in (page, style, script):
        reste = contenu.replace(espace_svg, "")
        assert "http://" not in reste
        assert "https://" not in reste


# -- les jointures entre le HTML et le JavaScript ---------------------------

def test_chaque_identifiant_appele_existe_dans_la_page(page, script):
    """`$("#truc")` sur un identifiant absent rend null, et la page se fige."""
    dans_la_page = set(re.findall(r'id="([^"]+)"', page))
    appeles = set(re.findall(r'\$\("#([^"]+)"\)', script))
    manquants = sorted(appeles - dans_la_page)
    assert not manquants, f"identifiants absents du HTML : {manquants}"


def test_chaque_page_du_html_est_declaree_en_python(page):
    declarees = {p["cle"] for p in passerelle_mod.PAGES}
    dans_la_page = set(re.findall(r'data-page="([^"]+)"', page))
    assert dans_la_page == declarees


# -- la jointure entre le JavaScript et Python ------------------------------

def test_chaque_methode_appelee_existe_sur_la_passerelle(script):
    """Le pont ne verifie rien : une methode disparue rend une erreur muette."""
    appelees = set(re.findall(r'appeler\("([^"]+)"', script))
    assert appelees, "aucun appel trouve — le motif a-t-il change ?"
    absentes = sorted(
        nom for nom in appelees
        if not callable(getattr(passerelle_mod.Passerelle, nom, None))
    )
    assert not absentes, f"methodes absentes de la passerelle : {absentes}"


def test_la_doublure_de_l_apercu_couvre_toutes_les_methodes(script):
    """Sinon l'apercu montre une page a moitie vide, et on croit a un bug CSS."""
    sys.path.insert(0, str(RACINE / "outils"))
    from apercu_fenetre import DOUBLURE

    appelees = set(re.findall(r'appeler\("([^"]+)"', script))
    fournies = set(re.findall(r"^\s+(\w+): async", DOUBLURE, re.MULTILINE))
    assert not appelees - fournies, f"non doublees : {sorted(appelees - fournies)}"


# -- ce que le JavaScript doit se refuser -----------------------------------

def test_aucun_texte_venu_de_python_n_est_pose_en_html(script):
    """Un pseudo contenant « <b> » ne doit pas devenir du gras.

    Le seul `innerHTML` autorise est celui du logo, qui est du SVG fabrique
    par `logo.py` — pas du texte saisi par quelqu'un.
    """
    lignes = [ligne.strip() for ligne in script.splitlines()
              if "innerHTML" in ligne and not ligne.lstrip().startswith("-")]
    assert lignes == ['$("#marque-logo").innerHTML = etat.logo;'], lignes


# -- le theme ---------------------------------------------------------------

def test_les_deux_themes_sont_ecrits(style):
    assert "prefers-color-scheme: light" in style
    assert "--fond:" in style


def test_la_fenetre_se_replie_en_dessous_d_une_certaine_largeur(style):
    """L'ancienne fenetre devenait inutilisable a moitie reduite."""
    assert "max-width: 720px" in style


def test_le_mouvement_se_coupe_pour_qui_le_demande(style):
    assert "prefers-reduced-motion" in style


def test_l_attribut_hidden_gagne_sur_les_affichages(style):
    """`[hidden]` perd contre n'importe quel `display` : il faut l'imposer.

    Sans cette regle, l'annonce de mise a jour restait visible en
    permanence.
    """
    assert re.search(r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important",
                     style)


# -- le repli ---------------------------------------------------------------

def _guetter_l_ancienne_fenetre(monkeypatch) -> list:
    """Remplace l'ancienne fenetre par un temoin, sans charger tkinter.

    Le module n'est pas installe sur toutes les machines de test, et ce
    n'est pas lui qu'on eprouve ici : c'est le fait qu'on l'appelle.
    """
    import types

    ouvertes: list = []

    class FausseFenetre:
        def __init__(self, app):
            ouvertes.append(app)

        def lancer(self):
            pass

    faux = types.ModuleType("papote.fenetre")
    faux.Fenetre = FausseFenetre
    monkeypatch.setitem(sys.modules, "papote.fenetre", faux)
    return ouvertes


def test_sans_moteur_de_rendu_l_ancienne_fenetre_prend_le_relais(monkeypatch):
    """Une fenetre qui refuse de s'ouvrir ne peut pas dire pourquoi."""
    from papote import __main__ as principal
    from papote import fenetre_web

    monkeypatch.setattr(fenetre_web, "disponible", lambda: False)
    ouvertes = _guetter_l_ancienne_fenetre(monkeypatch)

    assert principal._ouvrir_fenetre(object()) == 0
    assert ouvertes, "l'ancienne fenetre n'a pas pris le relais"


def test_une_fenetre_web_qui_echoue_se_replie_aussi(monkeypatch):
    """Le moteur est la, mais la fenetre ne s'ouvre pas : meme repli."""
    from papote import __main__ as principal
    from papote import fenetre_web

    monkeypatch.setattr(fenetre_web, "disponible", lambda: True)
    monkeypatch.setattr(fenetre_web, "ouvrir", lambda _app: False)
    ouvertes = _guetter_l_ancienne_fenetre(monkeypatch)

    assert principal._ouvrir_fenetre(object()) == 0
    assert ouvertes


def test_avec_le_moteur_l_ancienne_fenetre_reste_fermee(monkeypatch):
    from papote import __main__ as principal
    from papote import fenetre_web

    monkeypatch.setattr(fenetre_web, "disponible", lambda: True)
    monkeypatch.setattr(fenetre_web, "ouvrir", lambda _app: True)
    ouvertes = _guetter_l_ancienne_fenetre(monkeypatch)

    assert principal._ouvrir_fenetre(object()) == 0
    assert not ouvertes


def test_la_page_est_embarquee_dans_l_executable():
    """Oubliee dans la recette, la fenetre se replierait une fois compilee."""
    recette = (RACINE / "papote.spec").read_text(encoding="utf-8")
    assert '"papote/web"' in recette
    assert "webview.platforms.edgechromium" in recette
