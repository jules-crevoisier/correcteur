# -*- coding: utf-8 -*-
"""Chargement, migration et sauvegarde des reglages."""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import politique, regles

DEFAUTS = {
    # -- correction au fil de la frappe -------------------------------------
    # Corrige pendant que vous ecrivez, sans rien demander. C'est la facon
    # normale de se servir de l'outil ; le raccourci reste la pour le reste.
    "correction_auto": True,
    # Annule la derniere correction automatique et remet ce qui etait ecrit.
    "raccourci_annuler": "ctrl+alt+z",
    # Au-dela de ce silence (en secondes), on oublie la phrase en cours : le
    # curseur a pu bouger entre-temps, et corriger a l'aveugle abimerait le
    # texte.
    "delai_oubli": 5.0,

    # Propose la suite du mot en cours, comme un clavier de telephone, dans
    # une bulle posee dans un coin de l'ecran.
    "prediction": True,
    # Touche qui accepte la proposition. Elle n'est detournee que pendant que
    # la bulle est affichee : ailleurs, la tabulation garde son role.
    "touche_prediction": "tab",
    # Ou poser la bulle : bas-droite, bas-gauche, haut-droite, haut-gauche.
    "position_bulle": "bas-droite",

    # -- correction a la demande --------------------------------------------
    # Raccourci global. Syntaxe de la bibliotheque `keyboard`.
    "raccourci": "ctrl+alt+c",
    # Ouvre la fenetre. Vide pour s'en passer.
    "raccourci_fenetre": "ctrl+alt+f",
    # Relit la selection et montre les corrections avant de les appliquer.
    "raccourci_relecture": "ctrl+alt+r",
    # Recolle automatiquement le texte corrige a la place de la selection.
    "collage_auto": True,

    # -- ou corriger, et sur quel ton ---------------------------------------
    # « parle » respecte le francais parle ; « soutenu » remet les « ne » de
    # negation et deplie les abreviations.
    "registre": "parle",
    # Applications ou la correction automatique ne doit pas intervenir.
    # La liste par defaut couvre les terminaux et les editeurs de code.
    "applications_exclues": list(politique.EXCLUES_PAR_DEFAUT),
    # Registre particulier a certaines applications :
    # {"outlook.exe": "soutenu"}.
    "registre_par_application": {},

    # -- ce que vous lui apprenez -------------------------------------------
    # Mots a ne jamais corriger : pseudos, jargon, noms de jeux.
    "mots_perso": [],
    # Remplacements maison : {"ptetre": "peut-être", "cdlt": "cordialement"}.
    # Ils passent avant tout le reste, y compris avant le dictionnaire.
    "remplacements_perso": {},
    # Retient les corrections que vous annulez, et finit par s'y plier.
    "apprentissage": True,

    # -- mises a jour -------------------------------------------------------
    # Cherche une nouvelle version au demarrage puis une fois par jour, et la
    # telecharge. Elle prend la place de l'ancienne au demarrage suivant :
    # jamais pendant que vous ecrivez.
    "verifier_maj": True,

    # -- le reste -----------------------------------------------------------
    # Affiche une notification resumant les corrections appliquees.
    "notifications": True,
    # Regles desactivees par defaut que l'on peut reactiver ici. La liste
    # vient de « regles.py » : la dupliquer ici, c'etait la laisser diverger,
    # et perdre en silence tout reglage portant sur une regle plus recente.
    "regles_optionnelles": dict(regles.REGLES_OPTIONNELLES),
    # Delais en secondes. A augmenter si une application est lente a repondre.
    "delai_copie": 0.35,
    "delai_collage": 0.08,
}

# Anciens noms encore acceptes, pour ne pas perdre les reglages de ceux qui
# ont installe une version precedente.
RENOMMAGES = {
    "lexique_perso": "mots_perso",
}

RENOMMAGES_REGLES = {
    "UPPERCASE_SENTENCE_START": "MAJUSCULE_PHRASE",
}


# L'application s'est appelee « Correcteur » jusqu'a la version 1.0 : ses
# reglages sont repris au premier lancement sous le nouveau nom.
ANCIEN_DOSSIER = "Correcteur"


def _base_config() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home()))
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def dossier_config() -> Path:
    """%APPDATA%\\Papote sous Windows, ~/.config/Papote ailleurs."""
    return _base_config() / "Papote"


def chemin_config() -> Path:
    return dossier_config() / "config.json"


def _fusionner(defauts: dict, charges: dict) -> dict:
    """Fusion en profondeur : un fichier incomplet garde les valeurs par defaut."""
    resultat = dict(defauts)
    for cle, valeur in charges.items():
        if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
            resultat[cle] = _fusionner(resultat[cle], valeur)
        else:
            resultat[cle] = valeur
    return resultat


def _migrer(charges: dict) -> dict:
    """Traduit les reglages ecrits par une version precedente."""
    migre = dict(charges)

    for ancien, nouveau in RENOMMAGES.items():
        if ancien in migre:
            migre.setdefault(nouveau, migre.pop(ancien))
        migre.pop(ancien, None)

    regles = migre.get("regles_optionnelles")
    if isinstance(regles, dict):
        migre["regles_optionnelles"] = {
            RENOMMAGES_REGLES.get(nom, nom): actif
            for nom, actif in regles.items()
            # Les regles de l'ancien moteur qui n'ont plus d'equivalent sont
            # simplement oubliees.
            if RENOMMAGES_REGLES.get(nom, nom) in DEFAUTS["regles_optionnelles"]
        }

    return migre


def _reprendre_anciens_reglages() -> dict | None:
    """Les reglages ecrits du temps ou l'application s'appelait autrement."""
    ancien = _base_config() / ANCIEN_DOSSIER / "config.json"
    if not ancien.is_file():
        return None
    try:
        with ancien.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def charger() -> dict:
    """Lit la configuration, en creant le fichier au premier lancement."""
    chemin = chemin_config()

    if not chemin.exists():
        anciens = _reprendre_anciens_reglages()
        if anciens is not None:
            config = _fusionner(DEFAUTS, _migrer(anciens))
            sauvegarder(config)
            return config

    if not chemin.exists():
        sauvegarder(DEFAUTS)
        return dict(DEFAUTS)
    try:
        with chemin.open(encoding="utf-8") as f:
            return _fusionner(DEFAUTS, _migrer(json.load(f)))
    except (json.JSONDecodeError, OSError, AttributeError):
        # Fichier corrompu ou illisible : on repart des defauts plutot que
        # d'empecher l'application de demarrer.
        return dict(DEFAUTS)


def sauvegarder(config: dict) -> Path:
    chemin = chemin_config()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # Ecriture en deux temps : une coupure de courant au mauvais moment ne
    # doit pas laisser un fichier de reglages a moitie ecrit.
    provisoire = chemin.with_suffix(".json.tmp")
    with provisoire.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    provisoire.replace(chemin)
    return chemin
