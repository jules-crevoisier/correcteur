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


def _methodes_appelees(script: str) -> set[str]:
    """Les methodes de la passerelle que le JavaScript appelle.

    L'espace apres la parenthese compte : les appels a plusieurs arguments
    sont souvent coupes en deux lignes, et une regex qui l'ignorait en
    manquait trois. Un test qui examine moins qu'il ne croit ne dit rien
    quand il passe.
    """
    return set(re.findall(r'appeler\(\s*"([^"]+)"', script))


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

    appelees = _methodes_appelees(script)
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


# -- l'annulation de la page « Corriger » -----------------------------------

def test_le_bouton_annuler_existe(page, script):
    """« Corriger » reecrit le texte : sans annulation, l'original est perdu."""
    assert 'id="annuler"' in page
    assert '$("#annuler")' in script


def test_l_etat_est_retenu_avant_chaque_reecriture(script):
    """Les trois endroits ou le programme ecrit dans le champ."""
    assert script.count("retenirLetat()") >= 3


def test_l_annulation_se_vide(script):
    """Un bouton qui ne mene nulle part est pire qu'un bouton absent."""
    assert 'hidden = etatsPrecedents.length === 0' in script


# -- ce qu'on ne peut pas defaire -------------------------------------------

def test_les_boutons_destructeurs_demandent_confirmation(script):
    """Effacer l'historique, le journal ou la transcription ne se reprend pas."""
    for bouton in ("#effacer-historique", "#vider-journal", "#dictee-oublier"):
        assert f'armer("{bouton}"' in script, bouton


def test_le_bouton_arme_se_voit(style):
    assert ".bouton.arme" in style


def test_l_armement_retombe_tout_seul(script):
    """Un bouton qui reste arme est un piege pose sur le chemin."""
    assert "DELAI_CONFIRMATION" in script
    assert 'bouton.addEventListener("blur", desarmer)' in script


# -- l'application courante ne s'applique plus toute seule ------------------

def test_le_champ_vide_n_exclut_plus_le_marque_page(script):
    """« champ.value || champ.placeholder » excluait « jeu.exe »."""
    assert "champ.placeholder" not in script


def test_l_application_courante_se_propose_d_un_clic(page, script):
    assert 'id="courante-exclusion"' in page
    assert 'id="courante-registre"' in page
    assert "proposerLapplicationCourante" in script


# -- la fenetre a sa propre taille minimale ---------------------------------

def test_les_entrees_de_navigation_s_enroulent(style):
    """A 560 px — le minimum de la fenetre —, la colonne passe en bandeau.

    Les entrees debordaient : « overflow-x: auto » promet un defilement
    qu'aucune molette ne declenche horizontalement ici, et « Dicter » comme
    « Réglages » etaient hors d'atteinte.
    """
    # Les commentaires sont retires : celui qui explique le correctif nomme
    # justement la declaration qu'on ne veut plus voir.
    regles = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
    bandeaux = regles.split("@media (max-width: 720px) {")[1:]
    assert bandeaux, "la fenetre n'a plus de mode bandeau"
    ensemble = "".join(bandeaux)
    assert "flex-wrap: wrap" in ensemble
    assert "overflow-x: auto" not in ensemble


# -- les reglages qui n'existaient que dans le fichier ----------------------

@pytest.mark.parametrize("identifiant", [
    "touche-prediction", "delai-oubli", "delai-copie",
])
def test_les_reglages_fins_ont_un_ecran(page, identifiant):
    """Exposer un reglage sans lui donner d'ecran, c'est promettre un ecran."""
    assert f'id="{identifiant}"' in page


def test_les_reglages_fins_sont_branches(script):
    for cle in ("touche_prediction", "delai_oubli", "delai_copie"):
        assert f'"{cle}"' in script, cle


def test_un_nombre_invalide_ne_part_pas_vers_python(script):
    """Un champ vide rend « NaN », que Python prendrait pour un reglage."""
    assert "Number.isFinite(valeur)" in script


# -- « Ce que Papote garde de vous » ----------------------------------------

def test_l_ecran_de_confidentialite_existe(page, script):
    """La promesse est ecrite partout ; celle-ci la rend verifiable."""
    assert 'id="fichiers-gardes"' in page
    assert 'id="dossier-config"' in page
    assert "chargerConfidentialite" in script


def test_toute_methode_de_la_passerelle_appelee_existe(script):
    """Une methode renommee en Python laisse un bouton mort dans la page."""
    from papote.passerelle import Passerelle

    manquantes = {m for m in _methodes_appelees(script)
                  if not hasattr(Passerelle, m)}
    assert not manquantes, f"introuvables : {sorted(manquantes)}"


def test_toute_methode_de_la_passerelle_sert_a_quelque_chose(script):
    """Et l'inverse : une methode que plus personne n'appelle.

    C'est le sens que le test d'au-dessus ne couvrait pas, et il manquait :
    « oublier_faute » et « tours_dictee » etaient restees sur le pont apres
    la disparition de l'ancienne fenetre tkinter. La premiere visait meme le
    mauvais compteur — « annulations_mot », alors que la page « Vos fautes »
    lit « corrections », dont les cles sont des paires « sa → ça ». La
    rebrancher telle quelle n'aurait jamais rien retire.

    Une methode appelee depuis la passerelle elle-meme compte : « etat_maj »
    ne sert qu'a garnir la reponse de « demarrer », et c'est tres bien.
    """
    from papote.chemins import dossier_web
    from papote.passerelle import Passerelle

    source = (Path(dossier_web()).parent / "passerelle.py").read_text(
        encoding="utf-8")
    internes = set(re.findall(r"self\.(\w+)\(", source))
    atteintes = _methodes_appelees(script) | internes

    publiques = {nom for nom in vars(Passerelle)
                 if not nom.startswith("_")
                 and callable(getattr(Passerelle, nom, None))}
    mortes = publiques - atteintes
    assert not mortes, f"sur le pont, mais plus personne n'appelle : {sorted(mortes)}"



# -- le message de la page « Dicter » ----------------------------------------

def test_le_message_n_accuse_plus_le_mode_d_installation(script):
    """« La dictée demande la version installée depuis Papote.msi » etait faux.

    Aucune version n'embarquait ces bibliotheques, MSI ou non — et celui qui
    avait bien installe le MSI se voyait dire que c'etait sa faute.
    """
    # Les commentaires sont retires : celui qui explique le correctif cite
    # justement la phrase qu'on ne veut plus voir s'afficher.
    sans_commentaires = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    sans_commentaires = re.sub(r"^\s*//.*$", "", sans_commentaires,
                               flags=re.M)
    assert "Papote.msi" not in sans_commentaires


# -- l'attente du moteur vocal ----------------------------------------------

def test_le_demarrage_de_la_dictee_montre_qu_il_travaille(page, script):
    """Le moteur charge quarante mégaoctets avant que le micro ne s'ouvre.

    Plusieurs secondes pendant lesquelles rien ne bougeait : un bouton qui
    ne répond pas passe pour un bouton cassé, et l'on reclique.
    """
    assert 'id="dictee-demarrage"' in page
    assert "demarrageEnCours" in script


def test_le_temoin_retombe_meme_si_le_demarrage_echoue(script):
    """Sans « finally », un micro absent laissait les boutons éteints."""
    debut = script.index("const lancer = async")
    corps = script[debut:debut + 700]
    assert "finally" in corps
    assert corps.count("demarrageEnCours") >= 2


def test_le_rouet_s_arrete_pour_qui_le_demande(style):
    assert ".rouet" in style
    assert "prefers-reduced-motion" in style


# -- le bouton des mises a jour ---------------------------------------------

def test_le_bouton_propose_de_redemarrer_quand_une_version_attend(script):
    """Chercher une version alors qu'une autre attend ne mène nulle part."""
    assert "Redémarrer pour installer" in script


def test_le_clic_suit_le_role_du_bouton(script):
    """Le libellé et l'action doivent changer ensemble, ou l'un ment."""
    debut = script.index('$("#verifier-maj").addEventListener')
    corps = script[debut:debut + 600]
    assert "prete" in corps and "redemarrer" in corps


def test_la_notification_n_envoie_plus_chercher_l_icone(script):
    """Windows replie les icônes : beaucoup ne la voient jamais."""
    from papote import app as app_mod
    import inspect

    source = inspect.getsource(app_mod)
    sans_commentaires = "\n".join(
        ligne for ligne in source.splitlines()
        if not ligne.strip().startswith("#"))
    assert "Cliquez l'icône Papote" not in sans_commentaires


# -- le choix du modele de dictee -------------------------------------------

def test_le_modele_se_choisit_avant_le_telechargement(page, script):
    """Revenir dessus après coup coûte un deuxième gigaoctet et demi."""
    assert 'id="modele-dictee"' in page
    assert "MODELES_DE_LANGUE" in script
    assert "montrerChoixDuModele" in script


def test_le_choix_reutilise_le_controle_segmente(script):
    """Il en existait déjà un : en écrire un second les ferait diverger."""
    debut = script.index("function montrerChoixDuModele")
    corps = script[debut:debut + 400]
    assert "segments(" in corps


def test_le_bouton_annonce_ce_qu_il_va_chercher(script):
    """Un gigaoctet et demi ne se télécharge pas par surprise."""
    assert '"Installer (" + poids(reste)' in script


@pytest.mark.parametrize("octets,attendu", [
    (512, "512 o"),
    (41_000_000, "39 Mo"),
    (1_400_000_000, "1,3 Go"),
])
def test_les_poids_se_lisent_en_francais(script, octets, attendu):
    """« 1347.5 Mo » demande une conversion de tête, et un point décimal
    n'est pas français."""
    assert "function poids(" in script
    assert 'replace(".", ",")' in script


def test_le_modele_par_defaut_est_le_precis(script):
    """Un outil qui se trompe ne sert à rien ; l'espace disque se récupère."""
    debut = script.index("const MODELES_DE_LANGUE")
    assert script[debut:debut + 120].index('"precis"') < \
        script[debut:debut + 400].index('"rapide"')
