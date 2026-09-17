# -*- coding: utf-8 -*-
"""Tests de la fenetre, sans ecran.

tkinter est remplace par une doublure stricte (`faux_tkinter`). Ces tests ne
disent rien de l'apparence — ils disent que chaque page se construit, que
chaque bouton appelle ce qu'il doit appeler, et que rien ne leve. C'est
exactement ce qu'on ne peut pas verifier a l'oeil, et exactement ce qui casse
quand on renomme une methode.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import faux_tkinter  # noqa: E402

faux_tkinter.installer()

from papote import config as config_mod  # noqa: E402
from papote import icones, maj, theme  # noqa: E402
from papote.app import Application  # noqa: E402
from papote.fenetre import PAGES, Fenetre, _cle  # noqa: E402


@pytest.fixture
def application(tmp_path, monkeypatch, lexique):
    """Une application complete, dont les reglages vivent dans un dossier a part."""
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    app = Application(config=dict(config_mod.DEFAUTS), journal=lambda _m: None)
    app._lexique = lexique
    return app


@pytest.fixture
def fenetre(application):
    return Fenetre(application)


def corriger_et_attendre(fenetre, texte: str) -> None:
    """Tape un texte, lance la correction, attend qu'elle revienne.

    La fenetre corrige dans un fil pour ne pas se figer ; le test doit donc
    l'attendre, comme le ferait un utilisateur.
    """
    import time

    fenetre.champ.insert("1.0", texte)
    fenetre.corriger()
    for _ in range(200):
        if fenetre.bouton_corriger.actif:
            return
        time.sleep(0.02)
    raise AssertionError("la correction n'est jamais revenue")


# -- construction ------------------------------------------------------------

def test_la_fenetre_s_ouvre_sur_la_correction(fenetre):
    assert fenetre.racine.titre == "Papote"
    assert fenetre.pages["Corriger"].visible


@pytest.mark.parametrize("nom", [nom for nom, _i, _s in PAGES])
def test_chaque_page_s_affiche(fenetre, nom):
    fenetre._afficher(nom)
    assert fenetre.pages[nom].visible
    assert fenetre.titre_page.options["text"] == nom
    assert all(not page.visible for autre, page in fenetre.pages.items()
               if autre != nom)


@pytest.mark.parametrize("nom,icone,_s", PAGES)
def test_chaque_page_a_son_icone(nom, icone, _s):
    assert icone in icones.DESSINS


def test_chaque_page_a_sa_methode():
    for nom, _icone, _sous_titre in PAGES:
        assert hasattr(Fenetre, "_page_" + _cle(nom)), nom


# -- corriger ----------------------------------------------------------------

def test_corriger_remplace_le_texte(fenetre):
    corriger_et_attendre(fenetre, "je sais pas si sa va")
    assert fenetre.champ.get("1.0") == "je sais pas si ça va"
    assert "correction" in fenetre.etat.options["text"]


def test_corriger_sur_un_texte_vide_ne_fait_rien(fenetre):
    fenetre.corriger()
    assert fenetre.champ.get("1.0") == ""


def test_les_mots_inconnus_sont_proposes(fenetre):
    corriger_et_attendre(fenetre, "un zbeulotron est passé")
    assert fenetre.inconnus.winfo_children(), "aucun mot inconnu propose"


def test_un_mot_incertain_montre_ses_remplacements(fenetre):
    """« ourné » n'est pas corrige tout seul, mais il est propose."""
    corriger_et_attendre(fenetre, "une bonne ourné")
    assert "journée" in fenetre._propositions("ourné")


def test_cliquer_une_proposition_remplace_le_mot(fenetre):
    corriger_et_attendre(fenetre, "une bonne ourné")
    fenetre._remplacer_mot("ourné", "journée")
    assert fenetre.champ.get("1.0") == "une bonne journée"


def test_un_remplacement_ne_touche_pas_les_mots_qui_le_contiennent(fenetre):
    fenetre.champ.insert("1.0", "ourné et retourné")
    fenetre._remplacer_mot("ourné", "journée")
    assert fenetre.champ.get("1.0") == "journée et retourné"


def test_copier_met_le_texte_dans_le_presse_papiers(fenetre):
    fenetre.champ.insert("1.0", "bonjour")
    fenetre.copier()
    assert fenetre.racine.presse_papiers == "bonjour"


# -- dictionnaire ------------------------------------------------------------

def test_ajouter_un_mot_l_enregistre(fenetre):
    fenetre.saisie_mot.insert(0, "Zbeul")
    fenetre._ajouter_mot()
    assert "Zbeul" in fenetre.config["mots_perso"]
    assert config_mod.charger()["mots_perso"] == ["Zbeul"]


def test_retirer_un_mot_le_retire(fenetre):
    fenetre.config["mots_perso"] = ["Zbeul"]
    fenetre._afficher("Mon dictionnaire")
    fenetre.liste_mots.choisir(0)
    fenetre._retirer_mot()
    assert fenetre.config["mots_perso"] == []


def test_retirer_sans_selection_le_dit(fenetre):
    fenetre._afficher("Mon dictionnaire")
    fenetre._retirer_mot()
    assert "Choisissez" in fenetre.etat.options["text"]


def test_ajouter_un_remplacement(fenetre):
    fenetre.saisie_de.insert(0, "ptetre")
    fenetre.saisie_vers.insert(0, "peut-être")
    fenetre._ajouter_remplacement()
    assert fenetre.config["remplacements_perso"] == {"ptetre": "peut-être"}


def test_un_remplacement_incomplet_est_refuse(fenetre):
    fenetre.saisie_de.insert(0, "ptetre")
    fenetre._ajouter_remplacement()
    assert fenetre.config["remplacements_perso"] == {}


# -- applications ------------------------------------------------------------

def test_exclure_une_application(fenetre):
    fenetre.saisie_application.insert(0, "Jeu.exe")
    fenetre._exclure()
    assert "jeu.exe" in fenetre.config["applications_exclues"]


def test_donner_un_registre_a_une_application(fenetre):
    fenetre.saisie_registre_app.insert(0, "outlook.exe")
    fenetre._registre_application("soutenu")
    assert fenetre.config["registre_par_application"]["outlook.exe"] == "soutenu"


# -- vos fautes --------------------------------------------------------------

def test_les_fautes_frequentes_s_affichent(fenetre, application):
    application.journal_habitudes.correction_appliquee("sa ", "ça ")
    fenetre._afficher("Vos fautes")
    assert any("ça" in ligne for ligne in fenetre.liste_fautes.lignes)


def test_effacer_l_historique(fenetre, application):
    application.journal_habitudes.correction_appliquee("sa ", "ça ")
    fenetre._afficher("Vos fautes")
    fenetre._effacer_historique()
    assert application.journal_habitudes.total_corrections() == 0


# -- reglages ----------------------------------------------------------------

def test_enregistrer_les_reglages(fenetre):
    fenetre.bascules["correction_auto"].set(False)
    fenetre.bascules["TYPOGRAPHIE"].set(True)
    fenetre.choix_registre.set("soutenu")
    fenetre._enregistrer_reglages()

    enregistre = config_mod.charger()
    assert enregistre["correction_auto"] is False
    assert enregistre["regles_optionnelles"]["TYPOGRAPHIE"] is True
    assert enregistre["registre"] == "soutenu"


def test_deux_raccourcis_identiques_sont_refuses(fenetre):
    fenetre.champs_raccourcis["raccourci_annuler"].valeur = \
        fenetre.champs_raccourcis["raccourci"].get()
    fenetre._enregistrer_reglages()
    assert "identiques" in fenetre.etat.options["text"]


def test_le_raccourci_de_correction_ne_peut_pas_disparaitre(fenetre):
    fenetre.champs_raccourcis["raccourci"].valeur = ""
    fenetre._enregistrer_reglages()
    assert "ne peut pas être supprimé" in fenetre.etat.options["text"]


def test_la_capture_de_raccourci_refuse_une_touche_seule(fenetre):
    champ = fenetre.champs_raccourcis["raccourci"]
    champ._capturer()
    champ._enfoncee(type("E", (), {"keysym": "a"})())
    assert champ.get() == "ctrl+alt+c"
    assert "Ctrl" in fenetre.etat.options["text"]


def test_la_capture_de_raccourci_accepte_une_combinaison(fenetre):
    champ = fenetre.champs_raccourcis["raccourci"]
    champ._capturer()
    champ._enfoncee(type("E", (), {"keysym": "Control_L"})())
    champ._enfoncee(type("E", (), {"keysym": "j"})())
    assert champ.get() == "ctrl+j"


# -- mises a jour ------------------------------------------------------------

def test_depuis_les_sources_on_ne_propose_pas_de_mise_a_jour(fenetre):
    """« git pull » fait le travail : pas de bouton, mais une explication."""
    assert fenetre.boutons_maj.winfo_children()
    assert not _canevas(fenetre.boutons_maj)


def test_compile_on_propose_de_verifier(application, monkeypatch):
    monkeypatch.setattr(maj, "compilee", lambda: True)
    monkeypatch.setattr(maj, "en_attente", lambda: None)
    fenetre = Fenetre(application)
    assert any("Vérifier" in libelle for libelle in _libelles(fenetre.boutons_maj))


def test_une_mise_a_jour_prete_propose_de_redemarrer(fenetre):
    fenetre._maj_prete(maj.Version("v9.9.9", "https://exemple/Papote.exe"))
    libelles = _libelles(fenetre.boutons_maj)
    assert any("Redémarrer" in libelle for libelle in libelles)
    assert any("v9.9.9" in libelle for libelle in libelles)


def test_la_mise_a_jour_prete_s_annonce_aussi_dans_la_colonne(fenetre):
    fenetre._maj_prete(maj.Version("v9.9.9", "https://exemple/Papote.exe"))
    assert fenetre.bandeau_maj.winfo_children()


def test_une_mise_a_jour_deja_la_se_propose_des_l_ouverture(application,
                                                           monkeypatch,
                                                           tmp_path):
    """Le telechargement se fait souvent dans l'autre processus, celui de l'icone.

    La fenetre ne l'apprend qu'en regardant a cote de l'executable — sans
    quoi il fallait aller ouvrir les reglages pour decouvrir qu'une version
    attendait.
    """
    monkeypatch.setattr(maj, "compilee", lambda: True)
    monkeypatch.setattr(maj, "en_attente", lambda: tmp_path / "Papote.nouveau.exe")
    monkeypatch.setattr(maj, "numero_en_attente", lambda: "v9.9.9")

    fenetre = Fenetre(application)
    assert fenetre.bandeau_maj.winfo_children(), "aucune proposition de redemarrage"
    assert any("Redémarrer" in libelle
               for libelle in _libelles(fenetre.bandeau_maj))


def test_plus_tard_renvoie_la_proposition(fenetre):
    """Refuser le redemarrage doit etre possible : on ecrit peut-etre."""
    fenetre._maj_prete(maj.Version("v9.9.9", "https://exemple/Papote.exe"))
    assert fenetre.bandeau_maj.winfo_children()
    fenetre._remettre_maj()
    assert not fenetre.bandeau_maj.winfo_children()


def test_le_bandeau_propose_de_remettre_a_plus_tard(fenetre):
    fenetre._maj_prete(maj.Version("v9.9.9", "https://exemple/Papote.exe"))
    assert any("Plus tard" in libelle
               for libelle in _libelles(fenetre.bandeau_maj))


def test_redemarrer_pose_le_marqueur(fenetre, tmp_path):
    fenetre._redemarrer()
    assert (tmp_path / maj.MARQUEUR).is_file()
    assert maj.redemarrage_demande() is True


def _libelles(widget) -> list[str]:
    """Les textes dessines dans les boutons d'une branche de l'arbre."""
    return [objet["text"] for canevas in _canevas(widget)
            for objet in canevas.objets.values() if "text" in objet]


def _canevas(widget):
    """Tous les canevas d'une branche de l'arbre : c'est la que sont les boutons."""
    trouves = []
    for enfant in widget.winfo_children():
        if isinstance(enfant, faux_tkinter.Canvas):
            trouves.append(enfant)
        trouves.extend(_canevas(enfant))
    return trouves


# -- theme et icones ---------------------------------------------------------

@pytest.mark.parametrize("nom", sorted(icones.DESSINS))
def test_chaque_icone_est_carree_et_lisible(nom):
    grille = icones.pixels(nom)
    assert all(len(ligne) == icones.TAILLE for ligne in grille), nom
    assert len(grille) <= icones.TAILLE
    dessine = sum(1 for ligne in grille for c in ligne if c not in icones.VIDE)
    assert dessine > 20, f"{nom} est presque vide"


def test_une_icone_inconnue_le_dit_clairement():
    with pytest.raises(KeyError, match="icone inconnue"):
        icones.pixels("licorne")


def test_les_couleurs_se_traduisent_en_pixels():
    assert icones._en_rvba("#2b7ade") == (43, 122, 222, 255)
    assert icones._en_rvba("#fff") == (255, 255, 255, 255)


def test_la_palette_couvre_tous_les_caracteres_dessines():
    couleurs = icones.palette("#111111", "#222222")
    for nom in icones.DESSINS:
        for ligne in icones.pixels(nom):
            for caractere in ligne:
                assert caractere in icones.VIDE or caractere in couleurs, \
                    f"{nom} emploie « {caractere} », absent de la palette"


# -- journal des erreurs -----------------------------------------------------

def test_le_journal_se_copie(fenetre, tmp_path):
    from papote import journal as journal_mod

    journal_mod.erreur("un essai", ValueError("quelque chose"))
    fenetre._copier_journal()
    assert "un essai" in fenetre.racine.presse_papiers


def test_un_journal_vide_se_dit_sans_alarmer(fenetre):
    from papote import journal as journal_mod

    journal_mod.vider()
    fenetre._copier_journal()
    assert "vide" in fenetre.etat.options["text"]


def test_effacer_le_journal(fenetre):
    from papote import journal as journal_mod

    journal_mod.ecrire("quelque chose")
    fenetre._effacer_journal()
    assert journal_mod.lire() == ""
