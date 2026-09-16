# -*- coding: utf-8 -*-
"""Tests de ce que Papote retient de votre facon d'ecrire.

La prediction seule classe les mots par leur frequence dans le francais en
general, ce qui donne « déso » -> « désormais » alors que personne n'ecrit
cela dans un message. Le contexte corrige ce classement, et la seule source
de contexte disponible hors ligne, c'est ce que l'utilisateur tape.

On verifie donc deux choses : que l'apprentissage marche, et qu'il ne
retient que ce qu'il a le droit de retenir.
"""

import json
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import memoire as memoire_mod  # noqa: E402
from papote.frappe import Frappe  # noqa: E402
from papote.memoire import Memoire  # noqa: E402
from papote.prediction import Predicteur  # noqa: E402


def taper(frappe, texte: str) -> None:
    for caractere in texte:
        frappe.caractere(caractere)


# -- les comptes ------------------------------------------------------------

def test_un_mot_vu_une_fois_ne_dit_rien():
    """Ce peut etre une faute de frappe passee entre les mailles."""
    memoire = Memoire()
    memoire.noter("", "désolé")
    assert memoire.avantage("désolé") == 1.0


def test_un_mot_vu_deux_fois_remonte():
    memoire = Memoire()
    memoire.noter("", "désolé")
    memoire.noter("", "désolé")
    assert memoire.avantage("désolé") > 1.0


def test_une_suite_pese_plus_qu_un_mot_seul():
    """Apres « bonne », « journée » est bien plus probable qu'ailleurs."""
    memoire = Memoire()
    for _ in range(3):
        memoire.noter("bonne", "journée")
    seul = memoire.avantage("journée")
    en_contexte = memoire.avantage("journée", precedent="bonne")
    assert en_contexte > seul


def test_le_mot_precedent_doit_correspondre():
    memoire = Memoire()
    for _ in range(3):
        memoire.noter("bonne", "journée")
    assert memoire.avantage("journée", precedent="mauvaise") < \
        memoire.avantage("journée", precedent="bonne")


def test_la_casse_ne_compte_pas():
    memoire = Memoire()
    memoire.noter("Bonne", "Journée")
    memoire.noter("bonne", "journée")
    assert memoire.avantage("journée", precedent="bonne") > 1.0


def test_le_fichier_ne_grandit_pas_indefiniment():
    memoire = Memoire()
    for i in range(memoire_mod.PAIRES_MAXIMUM + 500):
        memoire.noter(f"mot{i}", f"suite{i}")
    assert len(memoire.paires) <= memoire_mod.PAIRES_MAXIMUM


# -- le fichier -------------------------------------------------------------

def test_la_memoire_survit_a_un_aller_retour(tmp_path):
    memoire = Memoire()
    for _ in range(3):
        memoire.noter("bonne", "journée")
    chemin = tmp_path / "habitudes.json"
    memoire.enregistrer(chemin)

    relue = memoire_mod.charger(chemin)
    assert relue.avantage("journée", precedent="bonne") == \
        memoire.avantage("journée", precedent="bonne")


def test_un_fichier_absent_donne_une_memoire_vide(tmp_path):
    memoire = memoire_mod.charger(tmp_path / "rien.json")
    assert memoire.avantage("journée") == 1.0


def test_un_fichier_abime_ne_fait_pas_tomber_papote(tmp_path):
    """Un fichier tronque par un arret brutal ne doit rien emporter."""
    chemin = tmp_path / "habitudes.json"
    chemin.write_text('{"mots": {"bonjo', encoding="utf-8")
    assert memoire_mod.charger(chemin).avantage("bonjour") == 1.0

    chemin.write_text(json.dumps({"paires": {"une seule part": 3}}),
                      encoding="utf-8")
    assert memoire_mod.charger(chemin).avantage("part") == 1.0


def test_vider_efface_tout():
    memoire = Memoire()
    for _ in range(3):
        memoire.noter("bonne", "journée")
    memoire.vide()
    assert memoire.avantage("journée", precedent="bonne") == 1.0


# -- ce qu'elle refuse de retenir -------------------------------------------

def test_seuls_les_mots_du_dictionnaire_sont_retenus(correcteur):
    """Un mot de passe tapé dans la mauvaise fenêtre n'a rien à faire là."""
    memoire = Memoire()
    frappe = Frappe(correcteur, memoire=memoire)
    taper(frappe, "bonjour Tr0ub4dor ")
    assert "bonjour" in memoire.mots
    assert not any("tr0ub4dor" in mot.lower() for mot in memoire.mots)


def test_un_mot_inconnu_ne_devient_pas_un_precedent(correcteur):
    """Sinon la moitié des paires seraient bâties sur du bruit."""
    memoire = Memoire()
    frappe = Frappe(correcteur, memoire=memoire)
    taper(frappe, "zbeulotron bonjour ")
    assert ("zbeulotron", "bonjour") not in memoire.paires


def test_les_mots_d_une_lettre_ne_sont_pas_retenus(correcteur):
    memoire = Memoire()
    frappe = Frappe(correcteur, memoire=memoire)
    taper(frappe, "a b c ")
    assert not memoire.mots


# -- le resultat, sous les doigts -------------------------------------------

def test_ce_qu_on_ecrit_souvent_finit_par_passer_devant(lexique, correcteur):
    """« déso » propose « désormais » — jusqu'à ce qu'on écrive « désolé »."""
    memoire = Memoire()
    predicteur = Predicteur(lexique, memoire)
    assert predicteur.completer("deso")[0] == "désormais"

    for _ in range(4):
        memoire.noter("vraiment", "désolé")
    assert predicteur.completer("deso")[0] == "désolé"


def test_le_mot_precedent_oriente_la_proposition(lexique):
    memoire = Memoire()
    predicteur = Predicteur(lexique, memoire)
    for _ in range(5):
        memoire.noter("bonne", "journée")
    assert predicteur.completer("jour", precedent="bonne")[0] == "journée"


def test_la_frappe_apprend_ce_qu_on_lui_tape(correcteur, lexique):
    memoire = Memoire()
    frappe = Frappe(correcteur, predicteur=Predicteur(lexique, memoire),
                    memoire=memoire)
    for _ in range(4):
        frappe.oublier()
        taper(frappe, "passe une bonne journée ")

    frappe.oublier()
    taper(frappe, "je te souhaite une bonne jour")
    assert frappe.mot_precedent() == "bonne"
    assert frappe.prediction()[0] == "journée"


def test_sans_memoire_la_frappe_fonctionne_pareil(correcteur, lexique):
    frappe = Frappe(correcteur, predicteur=Predicteur(lexique))
    taper(frappe, "mon anni")
    assert "anniversaire" in frappe.prediction()
