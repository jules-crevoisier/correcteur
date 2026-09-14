# -*- coding: utf-8 -*-
"""Point d'entree.

    python -m correcteur                  lance l'application (icone + raccourci)
    python -m correcteur --texte "..."    corrige un texte et l'affiche
    python -m correcteur --console        lance sans icone, journal en console
    python -m correcteur --demarrage on   se lance avec Windows
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, config as config_mod
from . import demarrage, java
from .app import Application


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        prog="correcteur",
        description="Correcteur d'orthographe francais qui respecte le francais parle.",
    )
    analyseur.add_argument("--texte", help="corrige ce texte, affiche le resultat et quitte")
    analyseur.add_argument("--console", action="store_true",
                           help="lance sans icone de barre des taches")
    analyseur.add_argument("--config", action="store_true",
                           help="affiche le chemin du fichier de reglages et quitte")
    analyseur.add_argument("--demarrage", choices=["on", "off", "etat"],
                           help="lancement automatique a l'ouverture de session Windows")
    analyseur.add_argument("--verifier", action="store_true",
                           help="controle l'installation (Java, moteur) et quitte")
    analyseur.add_argument("--version", action="version", version=f"correcteur {__version__}")
    args = analyseur.parse_args(argv)

    if args.config:
        print(config_mod.chemin_config())
        return 0

    if args.demarrage:
        return _gerer_demarrage(args.demarrage)

    if args.verifier:
        return _verifier()

    app = Application()

    if args.texte is not None:
        corrige, corrections = app.corriger_texte(args.texte)
        print(corrige)
        for c in corrections:
            print(f"  {c}   [{c.regle}]", file=sys.stderr)
        return 0

    if args.console:
        app.demarrer()
        app.prechauffer()
        print("Ctrl+C pour quitter.")
        try:
            import keyboard
            keyboard.wait()
        except KeyboardInterrupt:
            pass
        finally:
            app.arreter()
        return 0

    from .interface import InterfaceBarre
    InterfaceBarre(app).lancer()
    return 0


def _gerer_demarrage(action: str) -> int:
    if not demarrage.disponible():
        print("Le demarrage automatique n'est gere que sous Windows.", file=sys.stderr)
        return 1

    if action == "etat":
        print("active" if demarrage.actif() else "desactive")
        return 0

    if action == "on":
        print(f"Inscrit au demarrage de Windows :\n  {demarrage.activer()}")
    else:
        demarrage.desactiver()
        print("Retire du demarrage de Windows.")
    return 0


def _verifier() -> int:
    """Controle que tout est en place, avec un diagnostic lisible."""
    souci = False

    try:
        executable = java.preparer()
        print(f"[ok] Java {java.version(executable)} : {executable}")
    except java.JavaIntrouvable as e:
        print(f"[X]  {e}")
        return 1

    try:
        app = Application()
        corrige, corrections = app.corriger_texte("je sais pas si sa va marcher")
        attendu = "je sais pas si ça va marcher"
        if corrige == attendu:
            print(f"[ok] Moteur de correction : « {corrige} »")
        else:
            print(f"[X]  Correction inattendue : « {corrige} »")
            souci = True
    except Exception as e:
        print(f"[X]  Le moteur n'a pas pu demarrer : {e}")
        return 1

    print(f"[ok] Reglages : {config_mod.chemin_config()}")

    if demarrage.disponible():
        etat = "active" if demarrage.actif() else "desactive"
        print(f"[ok] Demarrage automatique : {etat}")

    return 1 if souci else 0


if __name__ == "__main__":
    raise SystemExit(main())
