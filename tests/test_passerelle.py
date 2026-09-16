# -*- coding: utf-8 -*-
"""Tests de la passerelle entre la page et Papote.

La fenetre est une page web ; tout ce qu'elle sait faire passe par ici. Ces
tests n'ouvrent ni navigateur ni ecran — c'est tout l'interet d'avoir sorti
la logique de l'affichage.

Deux choses sont verifiees partout : que la reponse traverserait le pont
(donc qu'elle se serialise en JSON), et qu'une erreur revient dans la
reponse plutot que de remonter en exception. Une exception qui traverse le
pont laisse la fenetre muette.
"""

import json
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import config as config_mod  # noqa: E402
from papote import maj  # noqa: E402
from papote.app import Application  # noqa: E402
from papote.passerelle import Passerelle  # noqa: E402


@pytest.fixture
def passerelle(tmp_path, monkeypatch, lexique):
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    app = Application(config=dict(config_mod.DEFAUTS), journal=lambda _m: None)
    app._lexique = lexique
    return Passerelle(app)


def traversable(reponse) -> dict:
    """La reponse passe-t-elle le pont ? Un objet Python ne le passerait pas."""
    return json.loads(json.dumps(reponse, ensure_ascii=False))


# -- au chargement ----------------------------------------------------------

def test_demarrer_donne_de_quoi_dessiner_la_page(passerelle):
    etat = traversable(passerelle.demarrer())
    assert etat["version"]
    assert [p["cle"] for p in etat["pages"]][0] == "corriger"
    assert etat["logo"].startswith("<svg")
    assert "correction_auto" in etat["reglages"]


def test_les_reglages_exposes_ne_contiennent_que_ce_qui_se_regle(passerelle):
    """Exposer un delai que nul ecran ne montre, c'est promettre un ecran."""
    reglages = passerelle.demarrer()["reglages"]
    assert "delai_collage" not in reglages
    assert "raccourci" in reglages
    # Ces deux-la ont un ecran, desormais : Tab sert ailleurs, et une
    # application lente a repondre au Ctrl+C fait echouer le raccourci.
    assert "touche_prediction" in reglages
    assert "delai_copie" in reglages


# -- corriger ---------------------------------------------------------------

def test_corriger_rend_le_texte_et_le_detail(passerelle):
    reponse = traversable(passerelle.corriger("je sais pas si sa va"))
    assert reponse["texte"] == "je sais pas si ça va"
    assert reponse["corrections"][0]["apres"] == "ça"


def test_un_texte_vide_ne_declenche_rien(passerelle):
    assert passerelle.corriger("   ")["corrections"] == []
    assert passerelle.corriger("")["texte"] == ""


def test_une_correction_qui_echoue_revient_en_erreur(passerelle, monkeypatch):
    def tomber(_texte):
        raise RuntimeError("le moteur a glissé")

    monkeypatch.setattr(passerelle.app, "corriger_texte", tomber)
    reponse = passerelle.corriger("bonjour")
    assert "le moteur a glissé" in reponse["erreur"]


def test_les_mots_inconnus_arrivent_avec_leurs_propositions(passerelle):
    """« ourné » n'est pas corrige tout seul : il revient avec « journée »."""
    reponse = passerelle.corriger("une bonne ourné")
    inconnus = {i["mot"]: i["propositions"] for i in reponse["inconnus"]}
    assert "ourné" in inconnus
    assert "journée" in inconnus["ourné"]


def test_un_mot_du_dictionnaire_perso_n_est_plus_inconnu(passerelle):
    passerelle.ajouter_mot("zbeulotron")
    reponse = passerelle.corriger("un zbeulotron passe")
    assert not any(i["mot"] == "zbeulotron" for i in reponse["inconnus"])


def test_remplacer_ne_touche_que_le_mot_entier(passerelle):
    reponse = passerelle.remplacer("ourné et retourné", "ourné", "journée")
    assert reponse["texte"] == "journée et retourné"
    assert reponse["remplaces"] == 1


def test_remplacer_un_mot_absent_ne_change_rien(passerelle):
    reponse = passerelle.remplacer("bonjour", "absent", "présent")
    assert reponse["texte"] == "bonjour"
    assert reponse["remplaces"] == 0


# -- dictionnaire personnel -------------------------------------------------

def test_ajouter_un_mot_l_enregistre_sur_le_disque(passerelle):
    passerelle.ajouter_mot("Zbeul")
    assert "Zbeul" in passerelle.dictionnaire()["mots"]
    assert config_mod.charger()["mots_perso"] == ["Zbeul"]


def test_le_meme_mot_deux_fois_est_refuse(passerelle):
    passerelle.ajouter_mot("Zbeul")
    assert "erreur" in passerelle.ajouter_mot("zbeul")


def test_un_mot_vide_est_refuse(passerelle):
    assert "erreur" in passerelle.ajouter_mot("   ")


def test_une_expression_est_renvoyee_vers_les_remplacements(passerelle):
    reponse = passerelle.ajouter_mot("deux mots")
    assert "remplacements" in reponse["erreur"]


def test_retirer_un_mot_le_retire(passerelle):
    passerelle.ajouter_mot("Zbeul")
    passerelle.retirer_mot("Zbeul")
    assert passerelle.dictionnaire()["mots"] == []


def test_un_remplacement_se_pose_et_s_applique(passerelle):
    passerelle.ajouter_remplacement("ptetre", "peut-être")
    assert passerelle.corriger("ptetre demain")["texte"] == "peut-être demain"


def test_un_remplacement_incomplet_est_refuse(passerelle):
    assert "erreur" in passerelle.ajouter_remplacement("ptetre", "")
    assert "erreur" in passerelle.ajouter_remplacement("", "peut-être")


def test_un_remplacement_vers_lui_meme_est_refuse(passerelle):
    assert "erreur" in passerelle.ajouter_remplacement("mot", "Mot")


# -- applications -----------------------------------------------------------

def test_exclure_une_application_l_ajoute_a_la_liste(passerelle):
    passerelle.exclure("Jeu.EXE")
    assert "jeu.exe" in passerelle.applications()["exclues"]


def test_reintegrer_une_application_la_retire(passerelle):
    passerelle.exclure("jeu.exe")
    passerelle.reintegrer("jeu.exe")
    assert "jeu.exe" not in passerelle.applications()["exclues"]


def test_un_registre_inconnu_est_refuse(passerelle):
    assert "erreur" in passerelle.registre_application("outlook.exe", "chantant")


def test_un_registre_par_application_s_enregistre(passerelle):
    passerelle.registre_application("outlook.exe", "soutenu")
    registres = passerelle.applications()["registres"]
    assert {"application": "outlook.exe", "registre": "soutenu"} in registres


# -- reglages ---------------------------------------------------------------

def test_regler_ecrit_aussitot(passerelle):
    """Pas de bouton « Enregistrer » : il ne servait qu'a perdre le reglage."""
    passerelle.regler("correction_auto", False)
    assert config_mod.charger()["correction_auto"] is False


def test_un_reglage_inconnu_est_refuse(passerelle):
    assert "erreur" in passerelle.regler("couleur_des_boutons", "rose")


def test_une_regle_optionnelle_s_allume(passerelle):
    passerelle.regler_regle("TYPOGRAPHIE", True)
    assert config_mod.charger()["regles_optionnelles"]["TYPOGRAPHIE"] is True


# -- mises a jour -----------------------------------------------------------

def test_l_etat_de_la_mise_a_jour_traverse_le_pont(passerelle):
    assert traversable(passerelle.etat_maj())["compilee"] in (True, False)


def test_une_mise_a_jour_deja_telechargee_est_annoncee(passerelle, monkeypatch,
                                                        tmp_path):
    monkeypatch.setattr(maj, "compilee", lambda: True)
    monkeypatch.setattr(maj, "en_attente", lambda: tmp_path / "Papote.nouveau.exe")
    monkeypatch.setattr(maj, "numero_en_attente", lambda: "v9.9.9")
    etat = passerelle.etat_maj()
    assert etat["prete"] is True and etat["numero"] == "v9.9.9"


def test_depuis_les_sources_la_verification_le_dit(passerelle, monkeypatch):
    monkeypatch.setattr(maj, "compilee", lambda: False)
    assert "git pull" in passerelle.verifier_maj()["message"]


def test_redemarrer_pose_le_marqueur(passerelle, tmp_path):
    passerelle.redemarrer()
    assert (tmp_path / maj.MARQUEUR).is_file()


# -- journal ----------------------------------------------------------------

def test_le_journal_se_lit_et_se_vide(passerelle):
    journal = traversable(passerelle.journal())
    assert "contenu" in journal and "chemin" in journal
    assert "message" in passerelle.vider_journal()


# -- robustesse -------------------------------------------------------------

def test_aucune_methode_ne_leve_sur_une_application_muette(tmp_path,
                                                            monkeypatch):
    """Si l'application est cassee, la fenetre doit quand meme s'ouvrir.

    Une fenetre qui refuse de s'afficher parce que le dictionnaire manque ne
    laisse aucun moyen de le dire a l'utilisateur — ni d'aller lire le
    journal, qui est justement dans cette fenetre.
    """
    monkeypatch.setattr(config_mod, "dossier_config", lambda: tmp_path)
    app = Application(config=dict(config_mod.DEFAUTS), journal=lambda _m: None)

    class Muette:
        def __getattr__(self, nom):
            raise RuntimeError("rien ne va")

    app._lexique = Muette()
    passerelle = Passerelle(app)

    traversable(passerelle.demarrer())
    traversable(passerelle.dictionnaire())
    traversable(passerelle.fautes())
    traversable(passerelle.applications())
    traversable(passerelle.journal())
    assert "erreur" in passerelle.corriger("bonjour")


# -- le texte du raccourci de relecture --------------------------------------

def test_le_texte_a_relire_arrive_avec_la_page(passerelle):
    passerelle.app.texte_a_relire = "jai pas vu sa"
    assert passerelle.demarrer()["texte_a_relire"] == "jai pas vu sa"


def test_le_texte_a_relire_ne_sort_qu_une_fois(passerelle):
    """Recharger la page ne doit pas ressusciter un texte deja traite."""
    passerelle.app.texte_a_relire = "jai pas vu sa"
    passerelle.demarrer()
    assert passerelle.demarrer()["texte_a_relire"] == ""
    assert passerelle.app.texte_a_relire == ""


def test_sans_relecture_le_champ_reste_vide(passerelle):
    assert passerelle.demarrer()["texte_a_relire"] == ""
