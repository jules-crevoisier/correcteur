# -*- coding: utf-8 -*-
"""Ce que Papote retient de votre facon d'ecrire, pour mieux deviner.

La prediction seule classe les mots par leur frequence dans le francais en
general. Cela donne « déso » -> « désormais », alors que personne n'ecrit
« désormais » dans un message : on ecrit « désolé ».

Le contexte corrige cela, et il n'y a qu'une source de contexte disponible
hors ligne : **vous**. Deux comptes suffisent.

    les mots que vous employez      « désolé » passe devant « désormais » ;
    les mots qui en suivent d'autres  apres « bonne », vous ecrivez
                                      « journée », pas « bonne humeur ».

C'est le fonctionnement d'un clavier de telephone, et il a l'avantage de
s'ameliorer tout seul : plus on ecrit, mieux il devine.

**Ce qui sort d'ici : rien.** Le fichier vit a cote des reglages, sur votre
machine, et se vide d'un bouton. Il contient des mots que vous avez ecrits —
c'est le prix du contexte, et c'est pourquoi il s'efface aussi facilement.

Deux precautions de fond :

- seuls les mots que le dictionnaire connait sont retenus. Un mot de passe
  tape dans la mauvaise fenetre, un numero, un nom propre : rien de tout cela
  n'entre ;
- le fichier ne grandit pas indefiniment. Passe un certain nombre de paires,
  les moins vues sont oubliees.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

NOM_FICHIER = "habitudes_frappe.json"

# Nombre de paires conservees. Au-dela, les moins vues partent. Quelques
# milliers suffisent a couvrir ce qu'une personne ecrit vraiment.
PAIRES_MAXIMUM = 4_000
MOTS_MAXIMUM = 4_000

# Un mot vu une seule fois ne dit rien : ce peut etre une faute de frappe qui
# est passee entre les mailles. Il faut l'avoir ecrit deux fois.
VUES_MINIMALES = 2

# De combien un mot deja ecrit remonte dans le classement. La valeur est un
# diviseur applique au rang : vu cinq fois apres le meme mot, un candidat
# voit son rang divise par cinq — largement de quoi passer devant.
FORCE_SUITE = 40
FORCE_MOT = 6


class Memoire:
    """Les mots que vous employez, et ceux qui en suivent d'autres."""

    def __init__(self, mots: Counter | None = None,
                 paires: Counter | None = None):
        self.mots: Counter = mots if mots is not None else Counter()
        self.paires: Counter = paires if paires is not None else Counter()

    # -- apprentissage -------------------------------------------------------

    def noter(self, precedent: str, mot: str) -> None:
        """Retient un mot, et le lien avec celui qui le precede."""
        mot = (mot or "").lower()
        if not mot:
            return
        self.mots[mot] += 1
        precedent = (precedent or "").lower()
        if precedent:
            self.paires[(precedent, mot)] += 1
        self._elaguer()

    def _elaguer(self) -> None:
        """Ne garde que ce qui sert. Un fichier qui enfle finit par peser."""
        if len(self.mots) > MOTS_MAXIMUM:
            self.mots = Counter(dict(self.mots.most_common(MOTS_MAXIMUM // 2)))
        if len(self.paires) > PAIRES_MAXIMUM:
            self.paires = Counter(
                dict(self.paires.most_common(PAIRES_MAXIMUM // 2)))

    # -- consultation --------------------------------------------------------

    def avantage(self, mot: str, precedent: str = "") -> float:
        """De combien diviser le rang de ce candidat, vu vos habitudes.

        1.0 veut dire « rien de particulier ». Plus le nombre est grand, plus
        le candidat remonte.
        """
        mot = (mot or "").lower()
        gain = 1.0

        vues = self.mots.get(mot, 0)
        if vues >= VUES_MINIMALES:
            gain *= 1 + min(vues, 20) / 20 * FORCE_MOT

        if precedent:
            ensemble = self.paires.get((precedent.lower(), mot), 0)
            if ensemble >= VUES_MINIMALES:
                gain *= 1 + min(ensemble, 10) / 10 * FORCE_SUITE

        return gain

    def vide(self) -> None:
        self.mots.clear()
        self.paires.clear()

    # -- fichier -------------------------------------------------------------

    def en_dictionnaire(self) -> dict:
        return {
            "mots": dict(self.mots),
            # JSON n'a pas de cle composee : on joint les deux mots par une
            # tabulation, qu'aucun mot ne contient.
            "paires": {f"{a}\t{b}": n for (a, b), n in self.paires.items()},
        }

    @classmethod
    def depuis_dictionnaire(cls, donnees: dict) -> "Memoire":
        mots = Counter({str(m): int(n)
                        for m, n in (donnees.get("mots") or {}).items()})
        paires: Counter = Counter()
        for cle, n in (donnees.get("paires") or {}).items():
            morceaux = str(cle).split("\t")
            if len(morceaux) == 2:
                paires[(morceaux[0], morceaux[1])] = int(n)
        return cls(mots, paires)

    def enregistrer(self, chemin: Path) -> None:
        try:
            chemin.parent.mkdir(parents=True, exist_ok=True)
            provisoire = chemin.with_suffix(".partiel")
            provisoire.write_text(
                json.dumps(self.en_dictionnaire(), ensure_ascii=False),
                encoding="utf-8")
            provisoire.replace(chemin)
        except OSError:
            # Perdre ses habitudes n'est pas grave ; interrompre la frappe
            # pour si peu le serait.
            pass


def chemin_memoire() -> Path:
    from .config import dossier_config

    return dossier_config() / NOM_FICHIER


def charger(chemin: Path | None = None) -> Memoire:
    chemin = chemin or chemin_memoire()
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Memoire()
    try:
        return Memoire.depuis_dictionnaire(donnees)
    except (AttributeError, TypeError, ValueError):
        return Memoire()
