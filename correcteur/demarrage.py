# -*- coding: utf-8 -*-
"""Lancement automatique a l'ouverture de session Windows.

On passe par la cle de registre « Run » de l'utilisateur courant plutot que
par un raccourci dans le dossier Demarrage : c'est reversible proprement, ca
ne demande aucun droit administrateur, et l'application peut afficher son
propre etat au lieu de demander a l'utilisateur de deplacer des fichiers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .chemins import racine_application

CLE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOM_VALEUR = "Correcteur"


class Registre:
    """Acces a la cle Run de l'utilisateur courant.

    Isole derriere une classe pour que la logique de `demarrage` reste
    testable sur une machine sans registre Windows.
    """

    def lire(self, nom: str) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLE_RUN) as cle:
                valeur, _ = winreg.QueryValueEx(cle, nom)
                return valeur
        except FileNotFoundError:
            return None
        except OSError:
            return None

    def ecrire(self, nom: str, valeur: str) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CLE_RUN) as cle:
            winreg.SetValueEx(cle, nom, 0, winreg.REG_SZ, valeur)

    def supprimer(self, nom: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, CLE_RUN, 0, winreg.KEY_SET_VALUE
            ) as cle:
                winreg.DeleteValue(cle, nom)
        except FileNotFoundError:
            pass


def disponible() -> bool:
    """Le demarrage automatique n'est gere que sous Windows."""
    return os.name == "nt"


def commande_lancement() -> str:
    """Ligne de commande a inscrire au registre.

    Compilee en .exe, l'application se relance elle-meme. Depuis les sources,
    on passe par `pythonw.exe` — sans console — et par le chemin absolu de
    `lancement.py`, pour ne dependre d'aucun repertoire courant.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    interpreteur = Path(sys.executable)
    sans_console = interpreteur.with_name("pythonw.exe")
    if sans_console.exists():
        interpreteur = sans_console

    return f'"{interpreteur}" "{racine_application() / "lancement.py"}"'


def actif(registre: Registre | None = None) -> bool:
    if not disponible():
        return False
    return (registre or Registre()).lire(NOM_VALEUR) is not None


def activer(registre: Registre | None = None) -> str:
    """Inscrit l'application au demarrage. Renvoie la commande enregistree."""
    if not disponible():
        raise RuntimeError(
            "Le demarrage automatique n'est gere que sous Windows."
        )
    commande = commande_lancement()
    (registre or Registre()).ecrire(NOM_VALEUR, commande)
    return commande


def desactiver(registre: Registre | None = None) -> None:
    if not disponible():
        return
    (registre or Registre()).supprimer(NOM_VALEUR)


def basculer(registre: Registre | None = None) -> bool:
    """Active ou desactive le demarrage automatique. Renvoie le nouvel etat."""
    registre = registre or Registre()
    if actif(registre):
        desactiver(registre)
        return False
    activer(registre)
    return True


def synchroniser(registre: Registre | None = None) -> bool:
    """Remet a jour la commande enregistree si l'application a ete deplacee.

    Sans cela, deplacer ou recompiler l'application laisserait au registre un
    chemin mort, et le lancement au demarrage echouerait en silence.
    """
    if not disponible():
        return False
    registre = registre or Registre()
    existante = registre.lire(NOM_VALEUR)
    if existante is None:
        return False
    attendue = commande_lancement()
    if existante != attendue:
        registre.ecrire(NOM_VALEUR, attendue)
    return True
