# -*- coding: utf-8 -*-
"""Chargement, migration et sauvegarde des reglages."""

from __future__ import annotations

import json
import os
from pathlib import Path

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

    # -- correction a la demande --------------------------------------------
    # Raccourci global. Syntaxe de la bibliotheque `keyboard`.
    "raccourci": "ctrl+alt+c",
    # Recolle automatiquement le texte corrige a la place de la selection.
    "collage_auto": True,

    # -- ce que vous lui apprenez -------------------------------------------
    # Mots a ne jamais corriger : pseudos, jargon, noms de jeux.
    "mots_perso": [],
    # Remplacements maison : {"ptetre": "peut-être", "cdlt": "cordialement"}.
    # Ils passent avant tout le reste, y compris avant le dictionnaire.
    "remplacements_perso": {},

    # -- le reste -----------------------------------------------------------
    # Affiche une notification resumant les corrections appliquees.
    "notifications": True,
    # Regles desactivees par defaut que l'on peut reactiver ici.
    "regles_optionnelles": {
        "MAJUSCULE_PHRASE": False,
        "PONCTUATION_POINT": False,
    },
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


def dossier_config() -> Path:
    """%APPDATA%\\Correcteur sous Windows, ~/.config/correcteur ailleurs."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "Correcteur"


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


def charger() -> dict:
    """Lit la configuration, en creant le fichier au premier lancement."""
    chemin = chemin_config()
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
