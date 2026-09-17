# -*- coding: utf-8 -*-
"""Une seance de dictee, vue depuis la fenetre.

Ce module est la porte unique entre l'interface et tout ce qui touche au son.
La fenetre ne connait que lui, et il ne leve jamais : chaque methode rend un
dictionnaire ou l'on lit ce qui s'est passe. C'est la meme regle que pour
`passerelle.py` — une exception qui traverse le pont fige la page, et une page
figee est pire qu'un message d'erreur.

Deux modes, et la difference tient en un modele :

    dictée    une voix, la votre, transcrite au fil de la parole
    réunion   plusieurs voix, distinguees et signees, puis un compte rendu

Le mode reunion demande le modele de voix en plus ; sans lui, on le dit et on
propose la dictee simple plutot que de faire semblant.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from . import bibliotheques, modeles
from .reunion import compte_rendu
from .transcription import Transcription


@dataclass
class Dictee:
    """L'etat d'une transcription : ce qui tourne, et ce qui a ete dit.

    `fabriquer_correcteur` est appele au dernier moment : au demarrage de
    l'application, le dictionnaire n'est pas encore charge, et on ne va pas
    l'attendre pour afficher une fenetre.
    """

    fabriquer_correcteur: object = None
    journal: object = None

    transcription: Transcription | None = None
    seance: object = None
    reunion: bool = False
    erreur: str = ""
    _verrou: threading.Lock = field(default_factory=threading.Lock)

    # -- ce que la fenetre demande avant de commencer -----------------------

    def etat(self) -> dict:
        """De quoi dessiner la page, a tout moment."""
        return {
            "disponible": _bibliotheques_presentes(),
            "en_cours": bool(self.seance is not None
                             and getattr(self.seance, "en_cours", False)),
            "reunion": self.reunion,
            "erreur": self.erreur,
            # Le moteur vocal figure dans la meme liste que les modeles :
            # pour l'utilisateur, c'est un seul telechargement et un seul
            # bouton. Qu'une partie soit du code et l'autre des donnees ne
            # le regarde pas.
            "modeles": [
                {"nom": r.nom, "role": r.role, "taille": r.taille,
                 "installe": bibliotheques.installee(r)}
                for r in bibliotheques.TOUTES
            ] + [
                {"nom": m.nom, "role": m.role, "taille": m.taille,
                 "installe": modeles.installe(m)}
                for m in modeles.TOUS
            ],
            "poids_installe": (modeles.poids_installe()
                               + bibliotheques.poids_installe()),
            "tours": self.tours(),
            "participants": (self.transcription.participants
                             if self.transcription else []),
        }

    def installer(self, pour_reunion: bool = True,
                  avancement=None) -> dict:
        """Telecharge ce qui manque. Rend ce qui s'est passe.

        Le moteur vocal d'abord, les modeles ensuite : c'est l'ordre dans
        lequel ils servent, et si le premier echoue les seconds ne
        serviraient a rien.
        """
        roues = bibliotheques.manquantes()
        manquants = modeles.manquants(reunion=pour_reunion)
        if not roues and not manquants:
            return {"ok": True, "message": "Tout est déjà installé."}

        for roue in roues:
            try:
                bibliotheques.telecharger(roue, avancement)
            except bibliotheques.BibliothequeIntrouvable as erreur:
                self._noter(str(erreur))
                return {"ok": False, "erreur": str(erreur)}
            except Exception as erreur:            # noqa: BLE001
                self._noter(f"{roue.nom} : {erreur}")
                return {"ok": False, "erreur":
                        f"« {roue.nom} » n'a pas pu être installé : "
                        f"{erreur}"}

        for modele in manquants:
            try:
                modeles.telecharger(modele, avancement)
            except modeles.ModeleIntrouvable as erreur:
                self._noter(str(erreur))
                return {"ok": False, "erreur": str(erreur)}
            except Exception as erreur:            # noqa: BLE001
                self._noter(f"{modele.nom} : {erreur}")
                return {"ok": False, "erreur":
                        f"Le modèle « {modele.nom} » n'a pas pu être "
                        f"installé : {erreur}"}
        return {"ok": True, "message": "Tout est installé."}

    # -- la seance ----------------------------------------------------------

    def commencer(self, reunion: bool = False, peripherique=None,
                  capter_les_autres: bool = False) -> dict:
        """Ouvre le micro et lance la transcription."""
        with self._verrou:
            if self.seance is not None and self.seance.en_cours:
                return {"ok": False, "erreur": "Une transcription est déjà "
                                               "en cours."}
            if bibliotheques.manquantes():
                return {"ok": False,
                        "erreur": "Le moteur vocal n'est pas encore "
                                  "installé."}
            manquants = modeles.manquants(reunion=reunion)
            if manquants:
                noms = ", ".join(m.nom for m in manquants)
                return {"ok": False, "modeles_manquants": True,
                        "erreur": f"Il manque le modèle {noms}."}
            try:
                return self._ouvrir(reunion, peripherique, capter_les_autres)
            except Exception as erreur:            # noqa: BLE001
                self._noter(str(erreur))
                return {"ok": False, "erreur": str(erreur)}

    def _ouvrir(self, reunion, peripherique, capter_les_autres) -> dict:
        from .audio import Micro, MoteurVocal, Seance

        moteur = MoteurVocal(
            modeles.chemin(modeles.LANGUE),
            modeles.chemin(modeles.VOIX) if reunion else None,
        )
        micro = Micro(peripherique, boucle=capter_les_autres)
        micro.demarrer()

        self.erreur = micro.erreur
        self.reunion = reunion
        self.transcription = Transcription(correcteur=self._correcteur())
        self.seance = Seance(self.transcription, micro, moteur)
        self.seance.demarrer()
        return {"ok": True, "avertissement": micro.erreur}

    def _correcteur(self):
        """Le correcteur, s'il est la. Sans lui, le texte reste brut."""
        if self.fabriquer_correcteur is None:
            return None
        try:
            return self.fabriquer_correcteur()
        except Exception:                          # noqa: BLE001
            return None

    def arreter(self) -> dict:
        with self._verrou:
            seance, self.seance = self.seance, None
            if seance is None:
                return {"ok": True, "tours": self.tours()}
            try:
                seance.arreter()
            except Exception as erreur:            # noqa: BLE001
                self._noter(str(erreur))
        return {"ok": True, "tours": self.tours()}

    # -- ce qui a ete dit ---------------------------------------------------

    def tours(self) -> list[dict]:
        if self.transcription is None:
            return []
        return [
            {"locuteur": tour.locuteur, "debut": round(tour.debut, 1),
             "fin": round(tour.fin, 1), "texte": tour.texte}
            for tour in list(self.transcription.tours)
        ]

    def renommer(self, ancien: str, nouveau: str) -> dict:
        if self.transcription is None:
            return {"ok": False, "erreur": "Rien à renommer."}
        self.transcription.renommer(ancien, nouveau)
        return {"ok": True, "tours": self.tours()}

    def compte_rendu(self, titre: str = "", date: str = "") -> dict:
        if self.transcription is None or not self.transcription.tours:
            return {"ok": False, "erreur": "Rien n'a encore été transcrit."}
        try:
            texte = compte_rendu(self.transcription,
                                 titre or "Compte rendu", date)
        except Exception as erreur:                # noqa: BLE001
            self._noter(str(erreur))
            return {"ok": False, "erreur": f"Le compte rendu a échoué : "
                                           f"{erreur}"}
        return {"ok": True, "texte": texte}

    def oublier(self) -> dict:
        """Efface ce qui a ete transcrit. Rien n'etait ecrit sur le disque."""
        self.arreter()
        self.transcription = None
        self.erreur = ""
        return {"ok": True}

    def _noter(self, message: str) -> None:
        self.erreur = message
        if self.journal is not None:
            try:
                self.journal(f"[dictée] {message}")
            except Exception:                      # noqa: BLE001
                pass


def _bibliotheques_presentes() -> dict:
    """Ce qui manque et qu'aucun bouton ne peut reparer.

    `vosk` n'y figure pas, et c'est le coeur de l'affaire : il se telecharge
    au premier usage, donc son absence est **normale** avant. La page se
    servait pourtant de cette liste pour cacher le bouton d'installation —
    si bien qu'un moteur manquant rendait son propre telechargement
    inatteignable.

    Ne reste ici que ce qui est embarque. `sounddevice` absent, c'est qu'on
    tourne depuis les sources sans avoir installe les dependances, et aucun
    bouton n'y changera rien.
    """
    etat = {}
    for nom in ("sounddevice",):
        try:
            __import__(nom)
            etat[nom] = True
        except Exception:                          # noqa: BLE001
            etat[nom] = False
    return etat
