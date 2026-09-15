# -*- coding: utf-8 -*-
"""Point d'entree.

    python -m correcteur                  lance l'application (icone + raccourci)
    python -m correcteur --fenetre        ouvre la fenetre de correction
    python -m correcteur --texte "..."    corrige un texte et l'affiche
    python -m correcteur --console        lance sans icone, journal en console
    python -m correcteur --demarrage on   se lance avec Windows
"""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__, config as config_mod
from . import demarrage
from .app import Application


def brancher_sortie() -> None:
    """Rend la sortie de l'application exploitable, compilee comme interpretee.

    Deux corrections, dont une seule concerne l'executable :

    1. **Retrouver une sortie.** Correcteur.exe est compile en mode fenetre :
       il vit dans la zone de notification, Windows ne lui donne donc aucune
       console et PyInstaller met sys.stdout a None. On rouvre le descripteur
       1 quand l'appelant a redirige la sortie, et a defaut on se rattache a
       la console du terminal qui nous a lances. Lance d'un double-clic, rien
       de tout cela ne marche, et c'est tres bien : personne ne lit.

    2. **Ne pas perdre les accents.** Rediriger la sortie vers un fichier ou
       un tube lui fait prendre l'encodage local — cp1252 sous Windows — ou
       « ça » ne survit pas. Un correcteur francais doit ecrire en UTF-8 des
       qu'il n'ecrit plus a l'ecran ; devant un vrai terminal, on laisse au
       contraire l'encodage de la console, seul capable de l'afficher.
    """
    if sys.stdout is None or sys.stderr is None:
        _rattacher_sortie()

    for nom in ("stdout", "stderr"):
        flux = getattr(sys, nom)
        if flux is None:
            continue
        try:
            if not flux.isatty():
                flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _rattacher_sortie() -> None:
    """Redonne un sys.stdout a une application compilee en mode fenetre."""
    def rouvrir(descripteur: int):
        try:
            return os.fdopen(descripteur, "w", encoding="utf-8",
                             errors="replace", buffering=1)
        except OSError:
            return None

    sortie, erreur = rouvrir(1), rouvrir(2)

    if sortie is None and os.name == "nt":
        import ctypes

        ATTACHER_AU_PARENT = -1
        try:
            rattache = ctypes.windll.kernel32.AttachConsole(ATTACHER_AU_PARENT)
        except (AttributeError, OSError):
            rattache = False
        if rattache:
            try:
                # Pas d'encodage impose ici : ce qui s'affiche dans une console
                # doit parler la langue de cette console.
                sortie = open("CONOUT$", "w", errors="replace", buffering=1)
                erreur = open("CONOUT$", "w", errors="replace", buffering=1)
            except OSError:
                pass

    if sys.stdout is None and sortie is not None:
        sys.stdout = sortie
    if sys.stderr is None and erreur is not None:
        sys.stderr = erreur


def main(argv: list[str] | None = None) -> int:
    brancher_sortie()


    analyseur = argparse.ArgumentParser(
        prog="correcteur",
        description="Correcteur d'orthographe francais qui respecte le francais parle.",
    )
    analyseur.add_argument("--texte", help="corrige ce texte, affiche le resultat et quitte")
    analyseur.add_argument("--fenetre", action="store_true",
                           help="ouvre la fenetre de correction")
    analyseur.add_argument("--console", action="store_true",
                           help="lance sans icone de barre des taches")
    analyseur.add_argument("--config", action="store_true",
                           help="affiche le chemin du fichier de reglages et quitte")
    analyseur.add_argument("--demarrage", choices=["on", "off", "etat"],
                           help="lancement automatique a l'ouverture de session Windows")
    analyseur.add_argument("--verifier", action="store_true",
                           help="controle l'installation et quitte")
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
            print(f"  {c}   [{c.regle}] {c.message}", file=sys.stderr)
        return 0

    if args.fenetre:
        from .fenetre import Fenetre
        Fenetre(app).lancer()
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
    from .chemins import dossier_donnees
    from .lexique import LexiqueIntrouvable

    souci = False

    try:
        app = Application()
        corrige, _ = app.corriger_texte("je sais pas si sa va marcher")
        print(f"[ok] Dictionnaire : {dossier_donnees()}")
    except LexiqueIntrouvable as e:
        print(f"[X]  {e}")
        return 1
    except Exception as e:
        print(f"[X]  Le correcteur n'a pas pu demarrer : {e}")
        return 1

    attendu = "je sais pas si ça va marcher"
    if corrige == attendu:
        print(f"[ok] Correction : « {corrige} »")
    else:
        print(f"[X]  Correction inattendue : « {corrige} »")
        souci = True

    print(f"[ok] Reglages : {config_mod.chemin_config()}")

    if demarrage.disponible():
        etat = "active" if demarrage.actif() else "desactive"
        print(f"[ok] Demarrage automatique : {etat}")

    return 1 if souci else 0


if __name__ == "__main__":
    raise SystemExit(main())
