# -*- coding: utf-8 -*-
"""Mise a jour automatique de l'executable.

Une application qu'il faut aller retelecharger a la main reste a la version
du jour de son installation. Ce module va chercher la derniere version
publiee, la telecharge a cote de l'executable, et la met en place au
lancement suivant — jamais pendant que l'on ecrit.

Le remplacement suit le detour habituel sous Windows : on ne peut pas
ecraser un fichier en cours d'execution, mais on peut le *renommer*. La mise
a jour se fait donc en trois temps, au tout debut du demarrage :

    Papote.exe        -> Papote.ancien.exe
    Papote.nouveau.exe -> Papote.exe
    on relance, et on rend la main

Rien de tout cela ne concerne l'execution depuis les sources : `git pull`
fait deja le travail.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import __version__

# On ne telecharge que d'ici, et que ce fichier-la.
DEPOT = "jules-crevoisier/correcteur"
ADRESSE = f"https://api.github.com/repos/{DEPOT}/releases/latest"
NOM_ATTENDU = "Papote.exe"

DELAI = 15  # secondes

NOUVEAU = "Papote.nouveau.exe"
ANCIEN = "Papote.ancien.exe"

# Le numero de la version telechargee, note a cote d'elle. L'icone et la
# fenetre vivent dans deux processus : celui qui n'a pas fait le
# telechargement doit quand meme pouvoir dire « redemarrer pour installer
# la 1.0.28 » plutot qu'un vague « la mise a jour ».
NUMERO = "Papote.nouveau.txt"


class MiseAJourImpossible(RuntimeError):
    """Le serveur n'a pas repondu, ou sa reponse est inexploitable."""


@dataclass(frozen=True)
class Version:
    """Une version publiee, et ou la telecharger."""

    numero: str
    adresse: str
    empreinte: str | None = None

    def __str__(self) -> str:
        return self.numero


def _nombres(version: str) -> tuple[int, ...]:
    """« v1.2.10 » -> (1, 2, 10). Ce qui n'est pas un nombre est ignore."""
    propre = version.strip().lstrip("vV").split("+")[0].split("-")[0]
    nombres = []
    for morceau in propre.split("."):
        if not morceau.isdigit():
            break
        nombres.append(int(morceau))
    return tuple(nombres)


def plus_recente(candidate: str, reference: str) -> bool:
    """`candidate` est-elle posterieure a `reference` ?"""
    gauche, droite = _nombres(candidate), _nombres(reference)
    if not gauche:
        return False
    # Une version lancee depuis les sources n'a pas de numero de compilation :
    # elle ne se met pas a jour toute seule.
    return gauche > droite


def compilee() -> bool:
    """Tourne-t-on depuis Papote.exe, ou depuis les sources ?"""
    return bool(getattr(sys, "frozen", False))


def dossier() -> Path:
    return Path(sys.executable).parent


# ---------------------------------------------------------------------------
# Interroger GitHub
# ---------------------------------------------------------------------------

def derniere_version() -> Version:
    """La derniere version publiee. Leve MiseAJourImpossible si on ne sait pas."""
    requete = urllib.request.Request(
        ADRESSE,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Papote/{__version__}",
        },
    )
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise MiseAJourImpossible(f"serveur injoignable : {e}") from e

    numero = str(donnees.get("tag_name") or "").strip()
    if not numero:
        raise MiseAJourImpossible("la derniere version n'a pas de numero")

    for piece in donnees.get("assets") or []:
        if piece.get("name") != NOM_ATTENDU:
            continue
        adresse = str(piece.get("browser_download_url") or "")
        if not adresse.startswith("https://"):
            raise MiseAJourImpossible("adresse de telechargement inattendue")
        empreinte = str(piece.get("digest") or "") or None
        return Version(numero, adresse, empreinte)

    raise MiseAJourImpossible(f"aucun {NOM_ATTENDU} dans la version {numero}")


def disponible() -> Version | None:
    """La version publiee, si elle est plus recente que celle qui tourne."""
    if not compilee():
        return None
    version = derniere_version()
    return version if plus_recente(version.numero, __version__) else None


# ---------------------------------------------------------------------------
# Telecharger
# ---------------------------------------------------------------------------

def _verifier_empreinte(chemin: Path, empreinte: str | None) -> None:
    """Controle la somme de controle annoncee par GitHub, quand il y en a une."""
    if not empreinte or ":" not in empreinte:
        return
    algorithme, attendu = empreinte.split(":", 1)
    if algorithme != "sha256":
        return

    calcul = hashlib.sha256()
    with chemin.open("rb") as f:
        for morceau in iter(lambda: f.read(1 << 20), b""):
            calcul.update(morceau)
    if calcul.hexdigest() != attendu.lower():
        chemin.unlink(missing_ok=True)
        raise MiseAJourImpossible(
            "le fichier telecharge ne correspond pas a son empreinte"
        )


def telecharger(version: Version, destination: Path | None = None) -> Path:
    """Depose la nouvelle version a cote de l'executable, sans rien remplacer."""
    cible = destination if destination is not None else dossier() / NOUVEAU
    provisoire = cible.with_suffix(".partiel")

    requete = urllib.request.Request(
        version.adresse, headers={"User-Agent": f"Papote/{__version__}"}
    )
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse, \
                provisoire.open("wb") as f:
            while morceau := reponse.read(1 << 20):
                f.write(morceau)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        provisoire.unlink(missing_ok=True)
        raise MiseAJourImpossible(f"telechargement interrompu : {e}") from e

    _verifier_empreinte(provisoire, version.empreinte)
    provisoire.replace(cible)
    _noter_numero(version.numero, cible)
    return cible


def _noter_numero(numero: str, cible: Path) -> None:
    """Note le numero a cote du fichier telecharge, pour qui voudra le lire."""
    try:
        (cible.parent / NUMERO).write_text(numero, encoding="utf-8")
    except OSError:
        # Le numero n'est qu'un confort d'affichage : son absence ne doit
        # jamais faire echouer une mise a jour deja telechargee.
        pass


# Marqueur pose par la fenetre pour demander a l'icone de se relancer. Les
# deux vivent dans des processus differents : un fichier est le canal le plus
# simple, et le seul qui survive a l'absence de l'un des deux.
MARQUEUR = "redemarrage.demande"


def _chemin_marqueur() -> Path:
    from .config import dossier_config

    return dossier_config() / MARQUEUR


def demander_redemarrage() -> None:
    """Demande a l'application qui tourne de se relancer."""
    chemin = _chemin_marqueur()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("", encoding="utf-8")


def redemarrage_demande() -> bool:
    """Le relancement a-t-il ete demande ? La reponse efface la demande."""
    chemin = _chemin_marqueur()
    if not chemin.is_file():
        return False
    try:
        chemin.unlink()
    except OSError:
        pass
    return True


def en_attente() -> Path | None:
    """La version deja telechargee qui n'attend que le prochain demarrage."""
    if not compilee():
        return None
    candidat = dossier() / NOUVEAU
    return candidat if candidat.is_file() else None


def numero_en_attente() -> str | None:
    """Le numero de la version telechargee, s'il a pu etre note."""
    if en_attente() is None:
        return None
    try:
        numero = (dossier() / NUMERO).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return numero or None


# ---------------------------------------------------------------------------
# Mettre en place
# ---------------------------------------------------------------------------

def nettoyer() -> None:
    """Efface la version precedente, gardee le temps du remplacement."""
    if not compilee():
        return
    ancien = dossier() / ANCIEN
    try:
        ancien.unlink(missing_ok=True)
    except OSError:
        # Toujours verrouillee ? Elle partira au prochain demarrage.
        pass
    try:
        (dossier() / NUMERO).unlink(missing_ok=True)
    except OSError:
        pass


def appliquer() -> bool:
    """Met en place la version telechargee et relance. Renvoie True si c'est fait.

    A appeler tout au debut du demarrage, avant que quoi que ce soit d'autre
    ne s'installe : le processus courant est remplace par le nouveau.
    """
    nouveau = en_attente()
    if nouveau is None:
        return False

    courant = Path(sys.executable)
    ancien = dossier() / ANCIEN

    try:
        ancien.unlink(missing_ok=True)
        # Windows refuse d'ecraser un executable en cours, mais accepte de le
        # renommer : c'est tout ce dont on a besoin.
        courant.rename(ancien)
        nouveau.rename(courant)
    except OSError:
        # Remettre les choses en place plutot que de laisser un dossier casse.
        if not courant.exists() and ancien.exists():
            try:
                ancien.rename(courant)
            except OSError:
                pass
        return False

    try:
        subprocess.Popen([str(courant)] + sys.argv[1:], close_fds=True)
    except OSError:
        return False
    return True


def installer_maintenant(version: Version) -> Path:
    """Telecharge tout de suite ; la mise en place attend le redemarrage."""
    if not compilee():
        raise MiseAJourImpossible(
            "la mise a jour automatique ne concerne que Papote.exe ; "
            "depuis les sources, un « git pull » suffit."
        )
    return telecharger(version)
