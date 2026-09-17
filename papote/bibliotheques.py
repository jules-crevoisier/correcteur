# -*- coding: utf-8 -*-
"""Le moteur vocal, telecharge au premier usage.

`vosk` pese cinquante-quatre megaoctets de bibliotheques natives — vingt-six
pour `libvosk.dll`, vingt-six pour `libstdc++`. Papote est un executable
« onefile » : tout ce qu'il embarque est extrait dans un dossier temporaire
**a chaque demarrage**, et il demarre avec Windows. Embarquer vosk aurait
coute une a deux secondes a chaque ouverture de session, a tout le monde, y
compris a ceux qui ne dicteront jamais.

Il se telecharge donc au premier usage, comme les modeles — et dans le meme
geste, puisque la page « Dicter » n'offre qu'un bouton.

Ce qui reste embarque, parce que c'est petit et que cela ne se telecharge
pas commodement : `sounddevice` et son PortAudio (un megaoctet), `cffi` — que
vosk charge par un module compile, lie a la version de Python —, et les trois
modules que `vosk/__init__.py` importe sans les employer ici : `srt`,
`tqdm`, `requests`.

La roue est deployee telle quelle dans le dossier de configuration, et ce
dossier est ajoute a `sys.path`. Vosk trouve alors ses DLL tout seul : son
`open_dll()` les cherche a cote de son propre fichier, et appelle
`os.add_dll_directory` pour les dependances.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class BibliothequeIntrouvable(RuntimeError):
    """La bibliotheque n'a pas pu etre recuperee ou depliee."""


@dataclass(frozen=True)
class Roue:
    """Une roue Python a deplier a cote des reglages."""

    paquet: str       # le nom du module a importer, une fois deplie
    nom: str          # ce qu'on en dit a l'utilisateur
    role: str
    fichier: str
    url: str
    empreinte: str    # sha256, publiee par PyPI
    taille: int       # octets, pour l'avancement quand le serveur se tait


# L'adresse et l'empreinte sont celles que PyPI publie pour cette version
# precise. Elles sont ecrites ici plutot que cherchees a l'execution, et
# c'est voulu : ce que l'on telecharge n'est pas une donnee, c'est du **code
# qui sera importe**. Une adresse figee et une empreinte verifiee sont le
# minimum ; demander a PyPI laquelle prendre reviendrait a lui laisser
# choisir ce que Papote execute.
#
# Changer de version, c'est donc changer ces deux lignes ensemble.
VOSK = Roue(
    paquet="vosk",
    nom="vosk",
    role="le moteur de reconnaissance vocale",
    fichier="vosk-0.3.45-py3-none-win_amd64.whl",
    url="https://files.pythonhosted.org/packages/c0/4c/"
        "deb0861f7da9696f8a255f1731bb73e9412cca29c4b3888a3fcb2a930a59/"
        "vosk-0.3.45-py3-none-win_amd64.whl",
    empreinte="6994ddc68556c7e5730c3b6f6bad13320e3519b13ce3ed2aa25a86724e7c10ac",
    taille=13_997_596,
)

TOUTES = (VOSK,)


def dossier_bibliotheques() -> Path:
    from .config import dossier_config

    return dossier_config() / "bibliotheques"


def installee(roue: Roue) -> bool:
    """La bibliotheque est-elle depliee, et entiere ?

    On cherche le module lui-meme plutot que le dossier : une extraction
    interrompue laisse un dossier a moitie rempli, et l'import echouerait
    plus loin, avec un message incomprehensible.
    """
    return (dossier_bibliotheques() / roue.paquet / "__init__.py").is_file()


def manquantes() -> list[Roue]:
    return [r for r in TOUTES if not installee(r)]


def poids_installe() -> int:
    dossier = dossier_bibliotheques()
    if not dossier.is_dir():
        return 0
    return sum(p.stat().st_size for p in dossier.rglob("*") if p.is_file())


def rendre_importable() -> None:
    """Met le dossier des bibliotheques sur le chemin des imports.

    Sans effet s'il n'existe pas : la page « Dicter » dira alors qu'il faut
    installer, ce qui est vrai.
    """
    dossier = dossier_bibliotheques()
    if not dossier.is_dir():
        return
    chemin = str(dossier)
    if chemin not in sys.path:
        # En tete : ce que l'on a deplie doit primer sur ce qui aurait pu
        # etre embarque par une version precedente.
        sys.path.insert(0, chemin)


def telecharger(roue: Roue,
                avancement: Callable[[int, int], None] | None = None) -> Path:
    """Telecharge et deplie une roue. Rend son dossier.

    Le deploiement se fait dans un dossier temporaire et n'est deplace
    qu'une fois complet : une coupure de reseau ne laisse jamais une
    bibliotheque a moitie installee, qui serait pire qu'une absente.
    """
    destination = dossier_bibliotheques()
    if installee(roue):
        return destination

    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as provisoire:
        archive = Path(provisoire) / roue.fichier
        _recuperer(roue, archive, avancement)
        _verifier_l_empreinte(roue, archive)
        deplie = Path(provisoire) / "deplie"
        try:
            with zipfile.ZipFile(archive) as zip_:
                _verifier_les_chemins(zip_)
                zip_.extractall(deplie)
        except zipfile.BadZipFile as erreur:
            raise BibliothequeIntrouvable(
                f"L'archive de « {roue.nom} » est illisible.") from erreur

        paquet = deplie / roue.paquet
        if not (paquet / "__init__.py").is_file():
            raise BibliothequeIntrouvable(
                f"L'archive de « {roue.nom} » ne contient pas le module "
                f"attendu.")

        arrivee = destination / roue.paquet
        if arrivee.exists():
            shutil.rmtree(arrivee, ignore_errors=True)
        shutil.move(str(paquet), str(arrivee))

    rendre_importable()
    return destination


def _recuperer(roue: Roue, archive: Path, avancement) -> None:
    try:
        requete = urllib.request.Request(
            roue.url, headers={"User-Agent": "Papote"})
        with urllib.request.urlopen(requete, timeout=30) as reponse, \
                open(archive, "wb") as sortie:
            total = int(reponse.headers.get("Content-Length") or roue.taille)
            recu = 0
            while True:
                bloc = reponse.read(262_144)
                if not bloc:
                    break
                sortie.write(bloc)
                recu += len(bloc)
                if avancement:
                    avancement(recu, total)
    except (urllib.error.URLError, OSError, TimeoutError) as erreur:
        raise BibliothequeIntrouvable(
            f"« {roue.nom} » n'a pas pu être téléchargé : {erreur}. "
            f"Vérifiez votre connexion et réessayez."
        ) from erreur


def _verifier_l_empreinte(roue: Roue, archive: Path) -> None:
    """Le fichier recu est-il bien celui qu'on attendait ?

    Les modeles sont des donnees ; ceci est du code, et il sera importe.
    L'empreinte n'est donc pas une precaution contre les coupures de
    reseau — pour cela la taille suffirait — mais contre un fichier qui ne
    serait pas celui que l'on a lu et choisi.
    """
    condense = hashlib.sha256()
    with archive.open("rb") as f:
        for bloc in iter(lambda: f.read(262_144), b""):
            condense.update(bloc)
    if condense.hexdigest() != roue.empreinte:
        raise BibliothequeIntrouvable(
            f"Le fichier reçu pour « {roue.nom} » ne correspond pas à ce qui "
            f"était attendu. Rien n'a été installé.")


def _verifier_les_chemins(zip_: zipfile.ZipFile) -> None:
    """Refuse une archive qui ecrirait hors de son dossier.

    La roue vient d'un serveur tiers. Meme de confiance, on ne deplie pas
    une archive sans regarder ou elle prétend ecrire : un nom commencant par
    « .. » ou par une barre oblique sortirait du dossier prevu.
    """
    for nom in zip_.namelist():
        chemin = Path(nom)
        if chemin.is_absolute() or ".." in chemin.parts:
            raise BibliothequeIntrouvable(
                "L'archive contient un chemin hors de son dossier : "
                f"« {nom} ».")


def effacer() -> None:
    shutil.rmtree(dossier_bibliotheques(), ignore_errors=True)
