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

# La derniere reponse de GitHub, avec son ETag. Elle ne contient qu'un
# numero de version et une adresse de telechargement — rien qui vienne de
# l'utilisateur.
CACHE = "derniere_version.json"


def _chemin_cache() -> Path:
    from .config import dossier_config

    return dossier_config() / CACHE


def _cache_lu() -> dict:
    """La reponse mise de cote, ou rien. Ne leve jamais."""
    try:
        with _chemin_cache().open(encoding="utf-8") as f:
            donnees = json.load(f)
    except (OSError, ValueError):
        return {}
    return donnees if isinstance(donnees, dict) else {}


def _cache_ecrit(etag: str, corps: str) -> None:
    """Met la reponse de cote. Un echec d'ecriture ne coute qu'une demande."""
    if not etag:
        return
    try:
        chemin = _chemin_cache()
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with chemin.open("w", encoding="utf-8") as f:
            json.dump({"etag": etag, "corps": corps}, f)
    except OSError:
        pass


def _attente_avant_nouvel_essai(entetes) -> str:
    """« dans 12 minutes », lu dans l'en-tete que GitHub renvoie avec le 403.

    Dire « reessayez plus tard » sans dire quand, c'est faire recliquer —
    et chaque clic creuse un peu plus le trou.
    """
    import time

    try:
        reprise = int(entetes.get("X-RateLimit-Reset") or 0)
    except (TypeError, ValueError):
        return ""
    minutes = max(0, round((reprise - time.time()) / 60))
    if reprise <= 0 or minutes > 120:
        return ""
    if minutes < 1:
        return " Réessayez dans une minute."
    if minutes == 1:
        return " Réessayez dans une minute."
    return f" Réessayez dans {minutes} minutes."


def _expliquer(erreur: urllib.error.HTTPError) -> str:
    """Ce que le serveur a refusé, dit en francais.

    Le message brut partait tel quel dans une notification :

        Vérification impossible : serveur injoignable :
        HTTP Error 403: rate limit exceeded

    Trois choses fausses a la fois. Le serveur n'etait pas injoignable — il
    a repondu, et vite. « rate limit exceeded » est de l'anglais dans un
    produit qui n'en dit pas un mot ailleurs. Et rien n'indiquait quoi
    faire, alors que la reponse le disait.
    """
    if erreur.code in (403, 429):
        entetes = getattr(erreur, "headers", None) or {}
        if str(entetes.get("X-RateLimit-Remaining")) == "0" \
                or "rate limit" in str(erreur.reason).lower():
            return ("GitHub limite le nombre de vérifications par heure, et "
                    "la limite est atteinte."
                    + _attente_avant_nouvel_essai(entetes))
        return "GitHub a refusé la demande."
    if erreur.code == 404:
        return "Aucune version publiée n'a été trouvée."
    if erreur.code >= 500:
        return "GitHub est en panne, et ce n'est pas de votre côté."
    return f"GitHub a répondu {erreur.code}."


def derniere_version() -> Version:
    """La derniere version publiee. Leve MiseAJourImpossible si on ne sait pas.

    La reponse est mise de cote avec son ETag. GitHub n'accorde que soixante
    demandes par heure a qui ne s'annonce pas, et Papote n'a pas de compte a
    lui donner ; mais une demande conditionnelle a laquelle il repond « rien
    n'a change » ne compte pas dans ce quota. Verifier dix fois de suite ne
    coute donc qu'une seule demande.
    """
    entetes = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"Papote/{__version__}",
    }
    cache = _cache_lu()
    if cache.get("etag"):
        entetes["If-None-Match"] = cache["etag"]

    requete = urllib.request.Request(ADRESSE, headers=entetes)
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            corps = reponse.read().decode("utf-8")
            etag = reponse.headers.get("ETag") or ""
        donnees = json.loads(corps)
        _cache_ecrit(etag, corps)
    except urllib.error.HTTPError as e:
        if e.code == 304 and cache.get("corps"):
            # « Rien n'a change » : la reponse d'hier fait l'affaire, et
            # celle-ci n'a rien coute.
            donnees = json.loads(cache["corps"])
        else:
            raise MiseAJourImpossible(_expliquer(e)) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise MiseAJourImpossible(
            "Impossible de joindre GitHub. Vérifiez votre connexion.") from e
    except ValueError as e:
        raise MiseAJourImpossible("La réponse de GitHub est illisible.") from e

    numero = str(donnees.get("tag_name") or "").strip()
    if not numero:
        raise MiseAJourImpossible("La dernière version publiée n'a pas de "
                                  "numéro.")

    for piece in donnees.get("assets") or []:
        if piece.get("name") != NOM_ATTENDU:
            continue
        adresse = str(piece.get("browser_download_url") or "")
        if not adresse.startswith("https://"):
            raise MiseAJourImpossible("L'adresse de téléchargement n'est "
                                      "pas celle attendue.")
        empreinte = str(piece.get("digest") or "") or None
        return Version(numero, adresse, empreinte)

    raise MiseAJourImpossible(f"La version {numero} ne contient pas de "
                              f"{NOM_ATTENDU}.")


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


# ---------------------------------------------------------------------------
# Relancer Papote
# ---------------------------------------------------------------------------

# Le lanceur de PyInstaller se parle a lui-meme par l'environnement : il
# deballe l'executable dans un dossier temporaire, y note le chemin, puis
# relance le meme fichier pour que le second etage y trouve ses affaires.
#
# Un programme fige qui en lance un autre lui transmet ces variables sans le
# vouloir. Le nouveau se croit alors ce second etage, cherche ses fichiers
# dans le dossier temporaire de l'ancien, et s'arrete sur :
#
#     Failed to start embedded python interpreter!
#     Failed to remove temporary directory: ...\Temp\_MEI00002a102
#
# Le premier message est le nouveau Papote qui echoue ; le second est
# l'ancien qui ne peut plus faire le menage, puisqu'un processus tient
# encore son dossier. C'est exactement ce qui se passait en installant une
# mise a jour.
VARIABLES_LANCEUR = ("_MEIPASS2", "_MEIPASS")


def environnement_de_relance() -> dict[str, str]:
    """L'environnement a passer a un Papote qu'on relance : le notre, deballe.

    A utiliser partout ou l'on demarre un second Papote — la fenetre, le
    redemarrage, la mise a jour. Depuis les sources il n'y a rien a retirer,
    et la fonction se contente de rendre l'environnement courant.
    """
    propre = dict(os.environ)
    for nom in list(propre):
        if nom in VARIABLES_LANCEUR or nom.startswith("_PYI"):
            del propre[nom]
    return propre


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
        subprocess.Popen([str(courant)] + sys.argv[1:], close_fds=True,
                         env=environnement_de_relance())
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
