# -*- coding: utf-8 -*-
"""Fabrique et mesure le modele statistique (« papote/statistique.py »).

    python outils/entrainer_modele.py entrainer corpus/*.txt
    python outils/entrainer_modele.py mesurer corpus/*.txt

Le corpus n'est pas dans le depot : seuls les comptes en sortent, dans
« donnees/modele_fr.bin.gz ». Une ligne sur vingt n'est jamais comptee : elle
sert a mesurer. On y prend chaque mot d'un ensemble d'homophones et on se
pose deux questions :

    le mot est juste    — le modele le laisse-t-il ?          (precision)
    on le remplace par  — le modele retrouve-t-il l'original ? (rappel)
    un de ses homophones

La precision compte plus que le rappel : une phrase juste abimee se voit, une
faute laissee se remarque a peine. C'est elle qui fixe la marge.

Sources du corpus et licences : voir « donnees/LICENCES.md ».
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
import zlib
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from papote import statistique as st  # noqa: E402
from papote.grammaire import decouper  # noqa: E402
from papote.morphologie import Morphologie  # noqa: E402

SORTIE = RACINE / "donnees" / "modele_fr.bin.gz"

# Au-dela, on retire les contextes vus une seule fois pour faire de la place.
TAILLE_MAXIMALE_PENDANT = 12_000_000
# Un contexte vu moins de fois que cela n'entre pas dans le modele : il ne
# pese presque rien dans un score, et il coute six octets.
COMPTE_MINIMAL = 5


def mise_de_cote(ligne: str) -> bool:
    """Une ligne sur vingt sert a mesurer, jamais a compter."""
    return zlib.crc32(ligne.encode("utf-8")) % 20 == 0


def analyser(ligne: str):
    """(suite, place, mots) d'une ligne de texte."""
    jetons = decouper(ligne)
    if len(jetons) < 2:
        return None
    textes = [j.texte for j in jetons]
    separateurs = [ligne[jetons[k].fin:jetons[k + 1].debut]
                   for k in range(len(jetons) - 1)] + [ligne[jetons[-1].fin:]]
    suite, place = st.sequence(textes, separateurs)
    return suite, place, textes


def cibles(morphologie, mot: str):
    """Ce qu'on compte a la place de ce mot : lui-meme, ou sa classe verbale."""
    normal = st.normaliser(mot)
    if normal in st.ENSEMBLE_DE:
        return normal
    classe = st.classe_verbale(morphologie, normal)
    return classe[0] if classe else None


def lignes_de(fichiers):
    for fichier in fichiers:
        with open(fichier, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                # Certaines sources ecrivent « é » en deux caracteres (e +
                # accent) : le decoupage y verrait deux mots.
                ligne = unicodedata.normalize("NFC", ligne.strip())
                if ligne:
                    yield ligne


def entrainer(fichiers, sortie: Path) -> None:
    morphologie = Morphologie()
    table: dict[int, int] = defaultdict(int)
    vues = 0
    for n, ligne in enumerate(lignes_de(fichiers)):
        if mise_de_cote(ligne):
            continue
        analyse = analyser(ligne)
        if analyse is None:
            continue
        suite, place, textes = analyse
        for k, mot in enumerate(textes):
            cible = cibles(morphologie, mot)
            if cible is None:
                continue
            vues += 1
            for sorte, cle in st.contextes(suite, place[k], cible):
                table[st.empreinte(sorte, cle)] += 1
        if len(table) > TAILLE_MAXIMALE_PENDANT:
            for cle in [c for c, v in table.items() if v < 2]:
                del table[cle]
        if n % 200_000 == 0:
            print(f"  {n:>9} lignes, {vues:>9} occurrences, {len(table):>9} contextes",
                  file=sys.stderr)
    gardes = {c: v for c, v in table.items() if v >= COMPTE_MINIMAL}
    st.Modele.ecrire(sortie, gardes)
    print(f"{len(gardes)} contextes gardes sur {len(table)} -> {sortie} "
          f"({sortie.stat().st_size / 1e6:.1f} Mo)")


def mesurer(fichiers, modele_chemin: Path, marges=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
            preuves_min=3, maximum=60_000) -> None:
    morphologie = Morphologie()
    modele = st.Modele.charger(modele_chemin)
    justes = Counter()          # (marge) -> phrases justes laissees
    abimes = Counter()
    retrouves = Counter()
    fautes = 0
    total_justes = 0
    par_ensemble = defaultdict(Counter)
    vus = 0
    for ligne in lignes_de(fichiers):
        if not mise_de_cote(ligne):
            continue
        analyse = analyser(ligne)
        if analyse is None:
            continue
        suite, place, textes = analyse
        for k, mot in enumerate(textes):
            normal = st.normaliser(mot)
            p = place[k]
            if normal in st.ENSEMBLE_DE:
                candidats = st.ENSEMBLE_DE[normal]
                nom = "/".join(sorted(candidats))
            else:
                classe = st.classe_verbale(morphologie, normal)
                if classe is None:
                    continue
                candidats = st.CLASSES_VERBALES
                normal = classe[0]
                nom = "verbes en [e]"
            vus += 1
            # Le mot juste, tel quel.
            total_justes += 1
            for marge in marges:
                choix = modele.trancher(suite, p, normal, candidats, marge, preuves_min)
                if choix is not None:
                    abimes[marge] += 1
                    par_ensemble[nom][f"abime@{marge}"] += 1
            par_ensemble[nom]["justes"] += 1
            # Le mot remplace par chacun de ses homophones.
            for faux in candidats:
                if faux == normal:
                    continue
                fautes += 1
                par_ensemble[nom]["fautes"] += 1
                for marge in marges:
                    choix = modele.trancher(suite, p, faux, candidats, marge, preuves_min)
                    if choix == normal:
                        retrouves[marge] += 1
                        par_ensemble[nom][f"retrouve@{marge}"] += 1
        if vus >= maximum:
            break
    print(f"modele : {len(modele)} contextes ; {total_justes} mots justes, {fautes} fautes fabriquees")
    print(f"  {'marge':>6} {'justes abimes':>16} {'fautes retrouvees':>20}")
    for marge in marges:
        print(f"  {marge:>6} {abimes[marge] / total_justes:>15.2%} "
              f"{retrouves[marge] / max(1, fautes):>19.1%}")
    marge = marges[len(marges) // 2]
    print(f"\n  par ensemble, marge {marge} :")
    for nom, c in sorted(par_ensemble.items(), key=lambda x: -x[1]["justes"]):
        print(f"    {nom:38s} justes {c['justes']:>6}  abimes {c[f'abime@{marge}'] / max(1, c['justes']):6.2%}"
              f"  retrouves {c[f'retrouve@{marge}'] / max(1, c['fautes']):6.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=["entrainer", "mesurer"])
    parser.add_argument("fichiers", nargs="+")
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    parser.add_argument("--preuves", type=int, default=3)
    args = parser.parse_args()
    if args.action == "entrainer":
        entrainer(args.fichiers, args.sortie)
    else:
        mesurer(args.fichiers, args.sortie, preuves_min=args.preuves)


if __name__ == "__main__":
    main()
