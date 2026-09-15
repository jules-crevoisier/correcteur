# -*- coding: utf-8 -*-
"""Transforme le dictionnaire Hunspell francais en liste de formes flechies.

Hunspell stocke des radicaux (« chat ») accompagnes de drapeaux qui decrivent
les terminaisons possibles (« chats », « chatte », « chattes »). Lire ce format
a l'execution demande une bibliotheque et coute ~700 us par mot inconnu : bien
trop lent pour tester le millier de candidats qu'exige une correction.

Ce script fait le travail une bonne fois pour toutes et produit deux fichiers
que l'application se contente de lire ligne a ligne :

    donnees/lexique_fr.txt.gz      toutes les formes, groupees par squelette
    donnees/frequences_fr.txt.gz   les plus courantes, de la plus a la moins

Le lexique est groupe par *squelette* — la graphie privee de ses accents — et
trie, ce qui permet a l'application de le consulter par dichotomie sans
construire le moindre index au demarrage :

    gateaux\tgâteaux
    pres\tprès prés prêts
    bonjour

A relancer uniquement si le dictionnaire (donnees/fr.dic) change :

    pip install spylls wordfreq
    python outils/construire_lexique.py
"""

from __future__ import annotations

import gzip
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "donnees"
sys.path.insert(0, str(RACINE))

# Les elisions (« l'arbre », « qu'il ») ne sont pas developpees : le decoupage
# en mots isole deja « l' » et « qu' ». Les developper doublerait le fichier.
# Les prefixes d'unites, eux, forment de vrais mots (« km », « centimetres »).
PREFIXES_DEVELOPPES = {"Um", "Ui", "U."}

# Nombre de mots courants retenus pour le classement des suggestions.
MOTS_COURANTS = 60_000


def _appliquer(forme: str, affixe, prefixe: bool = False) -> str | None:
    """Applique un affixe a une forme, ou None si la condition n'est pas remplie."""
    if prefixe:
        if affixe.strip and not forme.startswith(affixe.strip):
            return None
        if not affixe.cond_regexp.search(forme):
            return None
        return affixe.add + forme[len(affixe.strip):]

    if affixe.strip and not forme.endswith(affixe.strip):
        return None
    if not affixe.cond_regexp.search(forme):
        return None
    base = forme[: len(forme) - len(affixe.strip)] if affixe.strip else forme
    return base + affixe.add


def developper() -> set[str]:
    from spylls.hunspell import Dictionary

    dictionnaire = Dictionary.from_files(str(DONNEES / "fr"))
    aff = dictionnaire.aff

    formes: set[str] = set()
    for mot in dictionnaire.dic.words:
        if not mot.stem:
            continue
        formes.add(mot.stem)

        # Les suffixes peuvent en appeler d'autres (« -eur » puis « -euse ») :
        # on suit ces chainages sur deux niveaux, comme le fait Hunspell.
        a_traiter = [(mot.stem, mot.flags, 0)]
        while a_traiter:
            forme, drapeaux, profondeur = a_traiter.pop()
            if profondeur >= 2:
                continue
            for drapeau in drapeaux:
                for suffixe in aff.SFX.get(drapeau, ()):
                    nouvelle = _appliquer(forme, suffixe)
                    if not nouvelle:
                        continue
                    formes.add(nouvelle)
                    if suffixe.flags:
                        a_traiter.append((nouvelle, suffixe.flags, profondeur + 1))

        for drapeau in mot.flags & PREFIXES_DEVELOPPES:
            for prefixe in aff.PFX.get(drapeau, ()):
                nouvelle = _appliquer(mot.stem, prefixe, prefixe=True)
                if nouvelle:
                    formes.add(nouvelle)

    return formes


def grouper(formes: set[str]) -> list[str]:
    """Regroupe les formes par squelette, dans le format lu par l'application.

    Une ligne par squelette : le squelette, puis les graphies reelles quand
    elles en different. « bonjour » s'ecrit sans accent et occupe donc une
    ligne a lui seul.
    """
    from papote.lexique import squelette

    groupes: dict[str, list[str]] = {}
    for forme in formes:
        groupes.setdefault(squelette(forme), []).append(forme)

    lignes = []
    for nu in sorted(groupes):
        graphies = sorted(set(groupes[nu]))
        if graphies == [nu]:
            lignes.append(nu)
        else:
            lignes.append(nu + "\t" + " ".join(graphies))
    return lignes


def frequences(lexique: set[str]) -> list[str]:
    """Mots francais les plus employes, dans l'ordre, filtres par le lexique."""
    import wordfreq

    return [
        mot
        for mot in wordfreq.top_n_list("fr", MOTS_COURANTS)
        if len(mot) > 1 and (mot in lexique or mot.capitalize() in lexique)
    ]


def _ecrire(chemin: Path, lignes: list[str]) -> None:
    contenu = "\n".join(lignes)
    with gzip.open(chemin, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(contenu)
    print(f"  {chemin.name} : {len(lignes)} entrees, "
          f"{chemin.stat().st_size / 1024:.0f} Ko")


def main() -> int:
    if not (DONNEES / "fr.dic").exists():
        print(f"[X] {DONNEES / 'fr.dic'} est introuvable.", file=sys.stderr)
        return 1

    print("Developpement du dictionnaire Hunspell...")
    lexique = developper()
    _ecrire(DONNEES / "lexique_fr.txt.gz", grouper(lexique))

    print("Extraction des frequences...")
    _ecrire(DONNEES / "frequences_fr.txt.gz", frequences(lexique))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
