# -*- coding: utf-8 -*-
"""Point d'entree.

    python -m correcteur                  lance l'application (icone + raccourci)
    python -m correcteur --texte "..."    corrige un texte et l'affiche
    python -m correcteur --console        lance sans icone, journal en console
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, config as config_mod
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
    analyseur.add_argument("--version", action="version", version=f"correcteur {__version__}")
    args = analyseur.parse_args(argv)

    if args.config:
        print(config_mod.chemin_config())
        return 0

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


if __name__ == "__main__":
    raise SystemExit(main())
