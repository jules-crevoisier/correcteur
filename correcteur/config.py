# -*- coding: utf-8 -*-
"""Chargement et sauvegarde des reglages."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAUTS = {
    # Raccourci global. Syntaxe de la bibliotheque `keyboard`.
    "raccourci": "ctrl+alt+c",
    # Recolle automatiquement le texte corrige a la place de la selection.
    "collage_auto": True,
    # Affiche une notification resumant les corrections appliquees.
    "notifications": True,
    # Regles desactivees par defaut que l'on peut reactiver ici.
    "regles_optionnelles": {
        "UPPERCASE_SENTENCE_START": False,
        "PONCTUATION_POINT": False,
    },
    # Mots supplementaires a ne jamais corriger (pseudos, jargon, jeux...).
    "lexique_perso": [],
    # Delais en secondes. A augmenter si une application est lente a repondre.
    "delai_copie": 0.35,
    "delai_collage": 0.08,
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


def charger() -> dict:
    """Lit la configuration, en creant le fichier au premier lancement."""
    chemin = chemin_config()
    if not chemin.exists():
        sauvegarder(DEFAUTS)
        return dict(DEFAUTS)
    try:
        with chemin.open(encoding="utf-8") as f:
            return _fusionner(DEFAUTS, json.load(f))
    except (json.JSONDecodeError, OSError):
        # Fichier corrompu ou illisible : on repart des defauts plutot que
        # d'empecher l'application de demarrer.
        return dict(DEFAUTS)


def sauvegarder(config: dict) -> Path:
    chemin = chemin_config()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return chemin
