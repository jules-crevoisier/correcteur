# -*- coding: utf-8 -*-
"""Le journal des erreurs.

Papote.exe est compile en mode fenetre : il n'a pas de console, et tout ce
qu'il pourrait dire se perd. Quand quelque chose tourne mal, l'utilisateur
voit passer un message et n'a rien a montrer.

Ce module ecrit donc dans un fichier, a cote des reglages :

    %APPDATA%\\Papote\\journal.log

Il capture ce qui n'a ete rattrape par personne — l'exception d'un fil
d'execution comme celle du fil principal — et se coupe tout seul au-dela
d'une certaine taille, pour ne pas grossir indefiniment sur une machine qui
tourne des mois.

Rien n'en sort : le fichier reste sur la machine, et la fenetre propose de
l'ouvrir.
"""

from __future__ import annotations

import datetime
import sys
import threading
import traceback
from pathlib import Path

NOM = "journal.log"

# Au-dela, on repart d'un fichier neuf en gardant l'ancien sous « .1 ».
TAILLE_MAX = 200 * 1024

_verrou = threading.Lock()


def chemin() -> Path:
    from .config import dossier_config

    return dossier_config() / NOM


def ecrire(message: str, categorie: str = "info") -> None:
    """Ajoute une ligne au journal. N'echoue jamais : ce n'est qu'un journal."""
    horodatage = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ligne = f"{horodatage}  [{categorie}] {message}\n"
    try:
        with _verrou:
            fichier = chemin()
            fichier.parent.mkdir(parents=True, exist_ok=True)
            _faire_de_la_place(fichier)
            with fichier.open("a", encoding="utf-8", errors="replace") as f:
                f.write(ligne)
    except OSError:
        pass


def _faire_de_la_place(fichier: Path) -> None:
    try:
        if fichier.exists() and fichier.stat().st_size > TAILLE_MAX:
            fichier.replace(fichier.with_suffix(".log.1"))
    except OSError:
        pass


def erreur(message: str, exception: BaseException | None = None) -> None:
    """Consigne une erreur, avec sa pile quand on en a une."""
    ecrire(message, "erreur")
    if exception is not None:
        trace = "".join(traceback.format_exception(
            type(exception), exception, exception.__traceback__))
        ecrire(trace.rstrip(), "trace")


def lire(lignes: int = 200) -> str:
    """La fin du journal, pour l'afficher ou la copier."""
    try:
        with chemin().open(encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lignes:])
    except OSError:
        return ""


def vider() -> None:
    try:
        chemin().unlink(missing_ok=True)
        chemin().with_suffix(".log.1").unlink(missing_ok=True)
    except OSError:
        pass


def installer() -> None:
    """Fait consigner par le journal tout ce que personne n'a rattrape.

    Sans cela, une exception dans un fil d'execution s'affiche sur une sortie
    d'erreur qui n'existe pas, et disparait avec elle.
    """
    def sur_exception(genre, valeur, pile):
        erreur(f"exception non rattrapee : {genre.__name__}: {valeur}",
               valeur if isinstance(valeur, BaseException) else None)
        if pile is not None and not isinstance(valeur, BaseException):
            ecrire("".join(traceback.format_tb(pile)).rstrip(), "trace")

    def sur_exception_de_fil(details):
        erreur(
            f"exception dans le fil « {getattr(details.thread, 'name', '?')} » : "
            f"{details.exc_type.__name__}: {details.exc_value}",
            details.exc_value,
        )

    sys.excepthook = sur_exception
    threading.excepthook = sur_exception_de_fil
