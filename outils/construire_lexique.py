# -*- coding: utf-8 -*-
"""Transforme le dictionnaire Hunspell francais en liste de formes flechies.

Hunspell stocke des radicaux (« chat ») accompagnes de drapeaux qui decrivent
les terminaisons possibles (« chats », « chatte », « chattes »). Lire ce format
a l'execution demande une bibliotheque et coute ~700 us par mot inconnu : bien
trop lent pour tester le millier de candidats qu'exige une correction.

Ce script fait le travail une bonne fois pour toutes et produit quatre
fichiers que l'application se contente de lire ligne a ligne :

    donnees/lexique_fr.txt.gz      toutes les formes, groupees par squelette
    donnees/frequences_fr.txt.gz   les plus courantes, de la plus a la moins
    donnees/analyses_fr.txt.gz     ce qu'est chaque forme, triee par forme
    donnees/flexions_fr.txt.gz     les paradigmes, tries par lemme

Le lexique est groupe par *squelette* — la graphie privee de ses accents — et
trie, ce qui permet a l'application de le consulter par dichotomie sans
construire le moindre index au demarrage :

    gateaux\tgâteaux
    pres\tprès prés prêts
    bonjour

Les deux derniers portent la grammaire que Hunspell garde sous ses drapeaux
— personne, nombre, genre. Leur lecture est expliquee dans
`outils/morphologie_hunspell.py` ; ici on se contente de l'ecrire.

    affichons\t1p\tafficher
    affiche\t1s,3s,i2s,xs\taffiche afficher

Ils ne couvrent que les paradigmes dont au moins une forme figure parmi les
mots courants. Le reste, personne ne l'ecrit, et la grammaire n'a aucune
raison de s'en meler.

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


def morphologie(courants: set[str]) -> tuple[list[str], list[str]]:
    """Les deux tables de grammaire, dans l'ordre ou l'application les lit.

    On ne retient que les paradigmes dont une forme au moins est employee.
    Les autres pesent la moitie du fichier pour des mots que personne n'ecrit,
    et une regle d'accord qui ne se declenche jamais ne sert a rien.

    Le paradigme retenu l'est en entier : « pensassent » n'est pas un mot
    courant, mais c'est la forme qu'il faut savoir ecrire le jour ou
    quelqu'un tape « il fallait qu'ils pensasse ».
    """
    from spylls.hunspell import Dictionary

    from morphologie_hunspell import paradigmes

    dictionnaire = Dictionary.from_files(str(DONNEES / "fr"))
    def employe(groupes):
        return any(f in courants or f.lower() in courants
                   for groupe in groupes for f in groupe)

    retenus = [
        (lemme, categorie, groupes)
        for lemme, categorie, groupes in paradigmes(dictionnaire)
        if lemme in courants or employe(groupes)
    ]

    flexions = sorted(
        "{}\t{}\t{}".format(
            lemme, categorie,
            ";".join(" ".join(f"{forme}:{','.join(sorted(traits))}"
                              for forme, traits in sorted(groupe.items()))
                     for groupe in groupes),
        )
        for lemme, categorie, groupes in retenus
    )

    analyses: dict[str, tuple[set[str], set[str]]] = {}
    for lemme, _categorie, groupes in retenus:
        for groupe in groupes:
            for forme, traits in groupe.items():
                connus, lemmes = analyses.setdefault(forme, (set(), set()))
                connus |= traits
                lemmes.add(lemme)
    tables = sorted(
        "{}\t{}\t{}".format(forme, ",".join(sorted(traits)),
                             " ".join(sorted(lemmes)))
        for forme, (traits, lemmes) in analyses.items()
    )
    return tables, flexions


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
    courants = frequences(lexique)
    _ecrire(DONNEES / "frequences_fr.txt.gz", courants)

    print("Lecture de la grammaire cachee dans les drapeaux...")
    analyses, flexions = morphologie(set(courants))
    _ecrire(DONNEES / "analyses_fr.txt.gz", analyses)
    _ecrire(DONNEES / "flexions_fr.txt.gz", flexions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
