# -*- coding: utf-8 -*-
"""Le micro, et le moteur qui transforme le son en mots.

C'est la couche systeme de la transcription : tout ce qui depend d'une
bibliotheque, d'un peripherique ou d'un pilote est ici, et rien d'autre.
`transcription.py` et `reunion.py`, au-dessus, ne connaissent que des mots et
des empreintes — c'est ce qui les rend testables sans micro.

Deux sources de son, selon ce qu'on veut :

    le micro          ce que vous dites            pour dicter
    + la sortie       ce que les autres disent     pour une reunion en ligne

La seconde passe par le mode « boucle » de Windows, qui reecoute ce que la
carte son joue. Elle n'existe pas partout, et son absence ne doit rien
empecher : sans elle, une reunion en ligne ne garde que votre voix, ce qui
reste utile, et Papote le dit au lieu de faire semblant.

**Rien ne sort de la machine.** Le son n'est jamais ecrit sur le disque : il
traverse la memoire par blocs d'un quart de seconde, et le moteur n'en garde
que des mots. Le modele, lui, tourne en local — c'est toute la raison de le
telecharger plutot que d'appeler un service.
"""

from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from typing import Callable, Iterator

from .transcription import Mot, Segment

# Ce que le modele attend : 16 kHz, mono, entiers 16 bits. Lui donner autre
# chose ne provoque pas d'erreur — cela donne des mots faux, ce qui est pire.
FREQUENCE = 16_000
CANAUX = 1

# Un bloc d'un quart de seconde : assez court pour que la transcription
# suive la parole, assez long pour ne pas reveiller le processeur cent fois
# par seconde.
BLOC = FREQUENCE // 4

# Au-dela, on jette les blocs les plus anciens plutot que de gonfler la
# memoire : si le moteur a pris dix secondes de retard, il ne les rattrapera
# pas, et garder le son n'aide personne.
BLOCS_EN_ATTENTE = 200


class AudioIndisponible(RuntimeError):
    """Pas de micro, pas de pilote, ou la bibliotheque n'est pas la."""


# ---------------------------------------------------------------------------
# Le micro
# ---------------------------------------------------------------------------

class Micro:
    """Le son du micro, par blocs, dans une file.

    L'objet ne leve jamais pendant l'ecoute : une erreur de peripherique en
    plein milieu arrete la capture et se lit dans `erreur`. Une reunion qui
    s'arrete en silence serait le pire des cas ; celle-ci s'arrete en le
    disant.
    """

    def __init__(self, peripherique=None, boucle: bool = False):
        self.peripherique = peripherique
        self.boucle = boucle
        self.blocs: queue.Queue[bytes] = queue.Queue(BLOCS_EN_ATTENTE)
        self.erreur: str = ""
        self._flux = None
        self._perdus = 0

    def demarrer(self) -> None:
        sd = _sounddevice()
        reglages = None
        if self.boucle:
            reglages = _reglages_de_boucle(sd)
            if reglages is None:
                # Pas de mode boucle ici : on garde le micro seul plutot
                # que de ne rien enregistrer.
                self.erreur = ("Le son des autres participants n'a pas pu "
                               "être capté sur cette machine : seule votre "
                               "voix sera transcrite.")
                self.boucle = False
        try:
            self._flux = sd.RawInputStream(
                samplerate=FREQUENCE, blocksize=BLOC, dtype="int16",
                channels=CANAUX, device=self.peripherique,
                extra_settings=reglages, callback=self._recevoir,
            )
            self._flux.start()
        except Exception as erreur:            # noqa: BLE001
            raise AudioIndisponible(
                f"Le micro n'a pas pu être ouvert : {erreur}") from erreur

    def _recevoir(self, donnees, _cadres, _horloge, etat) -> None:
        if etat:
            # Un depassement de tampon : du son a ete perdu. Ce n'est pas
            # une raison d'arreter, mais cela se compte.
            self._perdus += 1
        try:
            self.blocs.put_nowait(bytes(donnees))
        except queue.Full:
            try:
                self.blocs.get_nowait()
                self.blocs.put_nowait(bytes(donnees))
            except (queue.Empty, queue.Full):
                pass

    def arreter(self) -> None:
        flux, self._flux = self._flux, None
        if flux is None:
            return
        try:
            flux.stop()
            flux.close()
        except Exception:                      # noqa: BLE001
            pass

    def __enter__(self) -> "Micro":
        self.demarrer()
        return self

    def __exit__(self, *_) -> None:
        self.arreter()

    @property
    def blocs_perdus(self) -> int:
        return self._perdus


def _sounddevice():
    try:
        import sounddevice
    except Exception as erreur:                # noqa: BLE001
        raise AudioIndisponible(
            "La capture audio n'est pas disponible dans cette installation "
            f"de Papote ({erreur})."
        ) from erreur
    return sounddevice


def _reglages_de_boucle(sd):
    """Les reglages qui font reecouter la sortie, quand Windows le permet."""
    try:
        return sd.WasapiSettings(loopback=True)
    except Exception:                          # noqa: BLE001
        return None


def peripheriques() -> list[dict]:
    """Les entrees audio disponibles, pour que l'utilisateur choisisse."""
    try:
        sd = _sounddevice()
        defaut = sd.default.device[0]
        return [
            {"indice": i, "nom": info["name"],
             "defaut": i == defaut}
            for i, info in enumerate(sd.query_devices())
            if info.get("max_input_channels", 0) > 0
        ]
    except Exception:                          # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Le moteur
# ---------------------------------------------------------------------------

class MoteurVocal:
    """Vosk, enveloppe de facon a ne rendre que des `Segment`.

    Le modele de voix est facultatif : sans lui, les segments n'ont pas
    d'empreinte et tout le monde parle d'une seule voix.
    """

    def __init__(self, modele_langue, modele_voix=None):
        vosk = _vosk()
        vosk.SetLogLevel(-1)
        self._reconnaisseur = vosk.KaldiRecognizer(
            vosk.Model(str(modele_langue)), FREQUENCE)
        self._reconnaisseur.SetWords(True)
        if modele_voix is not None:
            self._reconnaisseur.SetSpkModel(vosk.SpkModel(str(modele_voix)))

    def entendre(self, bloc: bytes) -> Segment | None:
        """Donne un bloc au moteur. Rend un segment quand il en a fini un."""
        if self._reconnaisseur.AcceptWaveform(bloc):
            return _segment(self._reconnaisseur.Result())
        return None

    def reste(self) -> Segment | None:
        """Ce que le moteur avait sur le coeur quand on l'a arrete."""
        return _segment(self._reconnaisseur.FinalResult())


def _vosk():
    try:
        # Le moteur est deplie a cote des reglages, pas embarque : le
        # dossier doit etre sur le chemin des imports avant qu'on essaie.
        from . import bibliotheques

        bibliotheques.rendre_importable()
        import vosk
    except Exception as erreur:                # noqa: BLE001
        raise AudioIndisponible(
            "Le moteur de reconnaissance vocale n'est pas installé. "
            f"Ouvrez « Dicter » et lancez l'installation ({erreur})."
        ) from erreur
    return vosk


def _segment(brut: str) -> Segment | None:
    """Traduit la reponse du moteur, qui est du JSON, en `Segment`."""
    try:
        reponse = json.loads(brut)
    except (TypeError, ValueError):
        return None
    mots = tuple(
        Mot(m["word"], float(m["start"]), float(m["end"]))
        for m in reponse.get("result", ())
        if m.get("word")
    )
    if not mots:
        return None
    empreinte = tuple(float(x) for x in reponse.get("spk", ()))
    return Segment(mots, empreinte)


# ---------------------------------------------------------------------------
# La boucle
# ---------------------------------------------------------------------------

@dataclass
class Seance:
    """Une transcription en cours : le micro, le moteur, et le fil qui tourne.

    `sur_tour` est appele a chaque prise de parole terminee — c'est ce qui
    fait avancer l'affichage. Il est appele depuis le fil de transcription :
    ce qu'on en fait doit etre bref.
    """

    transcription: object
    micro: object
    moteur: object
    sur_tour: Callable[[object], None] | None = None

    def __post_init__(self) -> None:
        self._fil: threading.Thread | None = None
        self._arret = threading.Event()

    def demarrer(self) -> None:
        self._arret.clear()
        self._fil = threading.Thread(target=self._tourner, daemon=True,
                                     name="papote-transcription")
        self._fil.start()

    def _tourner(self) -> None:
        while not self._arret.is_set():
            try:
                bloc = self.micro.blocs.get(timeout=0.2)
            except queue.Empty:
                continue
            self._traiter(self.moteur.entendre(bloc))
        self._traiter(self.moteur.reste())

    def _traiter(self, segment) -> None:
        if segment is None:
            return
        try:
            tour = self.transcription.ajouter(segment)
        except Exception:                      # noqa: BLE001
            return
        if tour is not None and self.sur_tour is not None:
            try:
                self.sur_tour(tour)
            except Exception:                  # noqa: BLE001
                pass

    def arreter(self, attente: float = 3.0) -> None:
        self._arret.set()
        self.micro.arreter()
        if self._fil is not None:
            self._fil.join(timeout=attente)
            self._fil = None

    @property
    def en_cours(self) -> bool:
        return self._fil is not None and self._fil.is_alive()


def blocs_depuis(source: Iterator[bytes]) -> "FauxMicro":
    """Un micro de test, qui rejoue une suite de blocs."""
    return FauxMicro(source)


class FauxMicro:
    """Un micro qui ne tient pas a un peripherique. Pour les tests."""

    def __init__(self, source: Iterator[bytes]):
        self.blocs: queue.Queue[bytes] = queue.Queue()
        for bloc in source:
            self.blocs.put(bloc)
        self.erreur = ""
        self.blocs_perdus = 0

    def demarrer(self) -> None:
        pass

    def arreter(self) -> None:
        pass
