# -*- coding: utf-8 -*-
"""Les modeles de reconnaissance vocale, telecharges au besoin.

Papote pese vingt-huit megaoctets. Les modeles en pesent cinquante-quatre a
eux deux, et neuf personnes sur dix ne dicteront jamais une ligne : les
embarquer ferait payer a tout le monde une fonction que peu emploieront.

Ils se telechargent donc au premier usage, une fois, et restent a cote des
reglages. Deux modeles :

    vosk-model-small-fr-0.22   41 Mo   entend le francais
    vosk-model-spk-0.4         13 Mo   distingue les voix

Le second est facultatif : sans lui, la transcription marche, mais tout le
monde parle d'une seule voix. C'est ce qu'on installe pour dicter ; le mode
reunion, lui, a besoin des deux.

**Ce qui sort de la machine :** une requete de telechargement vers
alphacephei.com, la premiere fois, et rien d'autre. Jamais de son, jamais de
texte. Une fois les modeles la, Papote n'a plus besoin d'Internet pour
transcrire — c'est tout l'interet d'un modele local.
"""

from __future__ import annotations

import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

BASE = "https://alphacephei.com/vosk/models/"


@dataclass(frozen=True)
class Modele:
    nom: str
    archive: str
    taille: int          # octets, approximatifs : sert a la barre d'avancement
    role: str

    @property
    def url(self) -> str:
        return BASE + self.archive


LANGUE = Modele("vosk-model-small-fr-0.22", "vosk-model-small-fr-0.22.zip",
                41_000_000, "entendre le français")
VOIX = Modele("vosk-model-spk-0.4", "vosk-model-spk-0.4.zip",
              13_000_000, "distinguer les voix")

TOUS = (LANGUE, VOIX)


def dossier_modeles() -> Path:
    from .config import dossier_config

    return dossier_config() / "modeles"


def chemin(modele: Modele) -> Path:
    return dossier_modeles() / modele.nom


def installe(modele: Modele) -> bool:
    """Le modele est-il deja la, et entier ?

    On verifie un fichier interne plutot que le dossier : un
    telechargement interrompu laisse un dossier a moitie rempli, et le
    moteur vocal echouerait plus loin, avec un message incomprehensible.
    """
    dossier = chemin(modele)
    return (dossier / "README").is_file() or (dossier / "am").is_dir() \
        or (dossier / "mfcc.conf").is_file()


def manquants(reunion: bool = False) -> list[Modele]:
    """Ce qu'il reste a telecharger pour que la fonction marche."""
    besoin = TOUS if reunion else (LANGUE,)
    return [m for m in besoin if not installe(m)]


def telecharger(modele: Modele,
                avancement: Callable[[int, int], None] | None = None) -> Path:
    """Telecharge et deplie un modele. Rend son dossier.

    Le telechargement se fait dans un dossier temporaire et n'est deplace
    qu'une fois complet : une coupure de reseau ne laisse jamais un modele
    a moitie installe, qui serait pire qu'un modele absent.
    """
    destination = chemin(modele)
    if installe(modele):
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as provisoire:
        archive = Path(provisoire) / modele.archive
        _recuperer(modele, archive, avancement)
        with zipfile.ZipFile(archive) as zip_:
            _verifier_les_chemins(zip_)
            zip_.extractall(provisoire)
        deplie = Path(provisoire) / modele.nom
        if not deplie.is_dir():
            candidats = [p for p in Path(provisoire).iterdir() if p.is_dir()]
            if not candidats:
                raise ModeleIntrouvable(
                    f"L'archive de {modele.nom} est vide.")
            deplie = candidats[0]
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        shutil.move(str(deplie), str(destination))
    return destination


def _recuperer(modele, archive: Path, avancement) -> None:
    try:
        requete = urllib.request.Request(
            modele.url, headers={"User-Agent": "Papote"})
        with urllib.request.urlopen(requete, timeout=30) as reponse, \
                open(archive, "wb") as sortie:
            total = int(reponse.headers.get("Content-Length") or modele.taille)
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
        raise ModeleIntrouvable(
            f"Le modèle « {modele.nom} » n'a pas pu être téléchargé : "
            f"{erreur}. Vérifiez votre connexion et réessayez."
        ) from erreur


def _verifier_les_chemins(zip_: zipfile.ZipFile) -> None:
    """Refuse une archive qui ecrirait hors de son dossier.

    Le modele vient d'un serveur tiers. Meme de confiance, on ne deplie pas
    une archive sans regarder ou elle prétend ecrire.
    """
    for nom in zip_.namelist():
        chemin_ = Path(nom)
        if chemin_.is_absolute() or ".." in chemin_.parts:
            raise ModeleIntrouvable(
                "L'archive du modèle contient un chemin suspect : elle n'a "
                "pas été installée.")


def effacer(modele: Modele) -> None:
    shutil.rmtree(chemin(modele), ignore_errors=True)


def poids_installe() -> int:
    """Ce que les modeles occupent sur le disque, en octets."""
    total = 0
    for modele in TOUS:
        dossier = chemin(modele)
        if dossier.is_dir():
            total += sum(f.stat().st_size
                         for f in dossier.rglob("*") if f.is_file())
    return total


class ModeleIntrouvable(RuntimeError):
    """Le modele n'a pas pu etre installe. Le message dit pourquoi."""
