# -*- coding: utf-8 -*-
"""Une seule Papote a la fois.

Papote s'installe au demarrage de Windows, et pose une icone pres de
l'horloge. Rien n'empeche pourtant d'en lancer une seconde : un raccourci du
menu Demarrer, un double-clic sur l'executable, ou simplement le doute — on
ne voit pas l'icone, on relance.

Deux Papote qui ecoutent le meme clavier, ce sont deux corrections pour une
frappe. La premiere efface trois lettres et en ecrit quatre ; la seconde,
qui a lu la meme phrase, efface trois lettres a son tour — mais le texte a
change sous elle. Le resultat est illisible, et l'utilisateur ne peut pas
savoir d'ou il vient.

Le verrou pose ici est un fichier ouvert en exclusif : le systeme le libere
quand le processus meurt, meme brutalement. Un fichier verrou qui traine
apres un plantage ne bloque donc rien — c'est la difference avec un fichier
temoin, qu'il faudrait effacer soi-meme, et qu'on n'efface jamais.
"""

from __future__ import annotations

import os
from pathlib import Path


class Occupee(RuntimeError):
    """Une autre Papote tourne deja."""


class Verrou:
    """Le verrou d'instance, a tenir tant que Papote tourne.

    S'emploie comme un gestionnaire de contexte, ou se prend et se rend a la
    main. `prendre` leve `Occupee` si une autre instance le tient deja.
    """

    def __init__(self, chemin: Path):
        self.chemin = chemin
        self._fichier = None

    def prendre(self) -> None:
        if self._fichier is not None:
            return
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        fichier = open(self.chemin, "a+b")
        try:
            _verrouiller(fichier)
        except OSError as e:
            fichier.close()
            raise Occupee(str(e)) from e
        # Le numero de processus sert au diagnostic, pas au verrou : c'est
        # le systeme qui arbitre, pas ce qui est ecrit dedans. Il s'ecrit
        # apres le premier octet, que le verrou occupe sous Windows.
        try:
            fichier.seek(1)
            fichier.truncate()
            fichier.write(str(os.getpid()).encode("ascii"))
            fichier.flush()
        except OSError:
            pass
        self._fichier = fichier

    def rendre(self) -> None:
        if self._fichier is None:
            return
        fichier, self._fichier = self._fichier, None
        try:
            _deverrouiller(fichier)
        except OSError:
            pass
        try:
            fichier.close()
        except OSError:
            pass

    def __enter__(self) -> "Verrou":
        self.prendre()
        return self

    def __exit__(self, *_) -> None:
        self.rendre()


def _verrouiller(fichier) -> None:
    """Pose un verrou exclusif, sans attendre.

    Deux systemes, deux appels. Aucun des deux n'est portable, et aucun des
    deux ne survit a la mort du processus — ce qui est precisement ce qu'on
    veut.

    Le `seek(0)` n'est pas une precaution : sous Windows, `msvcrt.locking`
    verrouille a partir de **la position courante**. Le fichier s'ouvre en
    ajout, donc a la fin — et comme la premiere instance y ecrit son numero
    de processus, la seconde s'ouvrait quatre octets plus loin et
    verrouillait une plage que personne ne tenait. Le verrou existait, et ne
    verrouillait rien.
    """
    fichier.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(fichier.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(fichier.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _deverrouiller(fichier) -> None:
    fichier.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(fichier.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(fichier.fileno(), fcntl.LOCK_UN)


def verrou_par_defaut() -> Verrou:
    """Le verrou pose a cote des reglages."""
    from . import config as config_mod

    return Verrou(config_mod.dossier_config() / "papote.verrou")
