# -*- coding: utf-8 -*-
"""Mesure la qualite du correcteur sur deux corpus.

Deux chiffres comptent :

    RAPPEL      la part des fautes qu'il attrape ;
    PRECISION   la part des phrases correctes qu'il laisse tranquilles.

Le second compte plus que le premier. Une faute laissee passe se remarque a
peine ; une phrase juste abimee se voit tout de suite, et fait desinstaller
l'outil.

Et deux corpus, parce qu'un seul ne mesure rien :

    developpement   celles qui ont servi a ecrire les regles. On peut les
                    regarder, les corriger, en ajouter. Leur score dit
                    « je n'ai rien casse », pas « je suis bon ».

    tenu a l'ecart  celles qui n'ont jamais servi a rien d'autre qu'a noter.
                    On lit leur score, jamais leur detail : les ouvrir, c'est
                    les perdre.

    python outils/evaluer.py                  les deux tableaux de bord
    python outils/evaluer.py --detail         le detail du corpus de dev
    python outils/evaluer.py --dev            le corpus de dev seul, plus vite
    python outils/evaluer.py --ouvrir-l-enveloppe
                                              le detail du corpus tenu a
                                              l'ecart. A n'utiliser qu'en
                                              sachant qu'on le brule.
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "outils"))

from corpus import developpement, tenu_a_lecart  # noqa: E402


def evaluer(correcteur, fautes, intouchables) -> dict:
    """Passe les deux listes au correcteur et range ce qui en sort."""
    reussites, echecs = [], []
    for fautif, attendu, categorie in fautes:
        obtenu = correcteur.corriger(fautif)[0]
        (reussites if obtenu == attendu else echecs).append(
            (categorie, fautif, attendu, obtenu)
        )

    intacts, abimees = [], []
    for phrase in intouchables:
        obtenu = correcteur.corriger(phrase)[0]
        (intacts if obtenu == phrase else abimees).append((phrase, obtenu))

    return {"reussites": reussites, "echecs": echecs,
            "intacts": intacts, "abimees": abimees}


def detailler(resultats: dict) -> None:
    if resultats["echecs"]:
        print("\n--- fautes non corrigees " + "-" * 45)
        for categorie, fautif, attendu, obtenu in resultats["echecs"]:
            print(f"  [{categorie}] {fautif}")
            print(f"      attendu : {attendu}")
            print(f"      obtenu  : {obtenu}")
    if resultats["abimees"]:
        print("\n--- phrases abimees " + "-" * 50)
        for phrase, obtenu in resultats["abimees"]:
            print(f"  {phrase}")
            print(f"      -> {obtenu}")


def par_categorie(resultats: dict) -> None:
    categories: dict[str, list[int]] = {}
    for liste, indice in ((resultats["reussites"], 0), (resultats["echecs"], 1)):
        for categorie, *_ in liste:
            compte = categories.setdefault(categorie, [0, 0])
            compte[indice] += 1

    largeur = max((len(c) for c in categories), default=10)
    print("\n  categorie        corrigees")
    for categorie in sorted(categories):
        bon, rate = categories[categorie]
        total = bon + rate
        print(f"  {categorie:{largeur}}  {bon:2}/{total:<3} "
              f"{'█' * bon}{'░' * rate}")


def tableau(titre: str, resultats: dict, fautes, intouchables) -> None:
    rappel = len(resultats["reussites"]) / len(fautes) * 100 if fautes else 0
    precision = (len(resultats["intacts"]) / len(intouchables) * 100
                 if intouchables else 0)
    print(f"\n{'=' * 62}\n  {titre}\n{'=' * 62}")
    par_categorie(resultats)
    print(f"\n  RAPPEL     {len(resultats['reussites']):3}/{len(fautes)}  "
          f"({rappel:.0f} %)   fautes attrapees")
    print(f"  PRECISION  {len(resultats['intacts']):3}/{len(intouchables)}  "
          f"({precision:.0f} %)   phrases correctes laissees tranquilles")


def main() -> int:
    from papote.moteur import construire

    correcteur = construire()

    resultats = evaluer(correcteur, developpement.FAUTES,
                        developpement.INTOUCHABLES)
    tableau("CORPUS DE DEVELOPPEMENT — dit seulement qu'on n'a rien casse",
            resultats, developpement.FAUTES, developpement.INTOUCHABLES)
    if "--detail" in sys.argv:
        detailler(resultats)
    elif resultats["echecs"] or resultats["abimees"]:
        print("\n  relancez avec --detail pour voir ce qui a rate")

    if "--dev" in sys.argv:
        return 0

    a_part = evaluer(correcteur, tenu_a_lecart.FAUTES,
                     tenu_a_lecart.INTOUCHABLES)
    tableau("CORPUS TENU A L'ECART — la seule mesure qui vaille",
            a_part, tenu_a_lecart.FAUTES, tenu_a_lecart.INTOUCHABLES)

    if "--ouvrir-l-enveloppe" in sys.argv:
        print("\n  /!\\ Vous venez d'ouvrir l'enveloppe. Ces phrases ont servi\n"
              "      a voir ce qui rate : elles ne peuvent plus servir a noter.\n"
              "      Ecrivez-en d'autres avant de vous fier a ce score.")
        detailler(a_part)
    else:
        print("\n  Le detail reste sous enveloppe : le lire, c'est le perdre.\n"
              "  Pour progresser, ecrivez de nouvelles phrases dans le corpus\n"
              "  de developpement — pas dans celui-ci.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
