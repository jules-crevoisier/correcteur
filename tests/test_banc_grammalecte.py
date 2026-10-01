# -*- coding: utf-8 -*-
"""Le banc Grammalecte, en garde-fou.

Il est long (une minute) et demande le fichier de regles de Grammalecte,
telecharge une fois dans « outils/cache ». Il ne tourne donc que sur
demande :

    PAPOTE_BANC=1 python -m pytest tests/test_banc_grammalecte.py

Les seuils sont ceux d'aujourd'hui, arrondis : ils disent « on n'a rien
casse », pas « c'est assez bien ».
"""

import os
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "outils"))

pytestmark = pytest.mark.skipif(
    not os.environ.get("PAPOTE_BANC"),
    reason="banc Grammalecte : PAPOTE_BANC=1 pour le lancer",
)


def test_la_lecture_des_tests_suit_le_format_de_grammalecte(tmp_path):
    import banc_grammalecte as banc

    regles = tmp_path / "rules.grx"
    regles.write_text(
        "__conf_moi_mois__\n"
        "    *NUM moi\n"
        "        <<- /conf/ --1>> mois     && Confusion.\n"
        "\n"
        "TEST: au {{moi}} d’avril                 ->> mois\n"
        "TEST: Qui {{on}} {{tant}} de malheurs !  ->> ont|||tend\n"
        "TEST: __ocr__ un {{mot}}                 ->> mot\n"
        "TEST: Le mois d’avril.\n"
        "__<s>/typo(typo_points)__  [.][.]  <<- ->> .   && Points.\n"
        "TEST: fin{{..}}                          ->> .\n",
        encoding="utf-8")
    fautes, justes, laisses = banc.extraire(regles)
    assert [(f.marquee(), f.suggestions) for f in fautes] == [
        ("au [moi] d’avril", ("mois",)),
        ("Qui [on] tant de malheurs !", ("ont",)),
        ("Qui on [tant] de malheurs !", ("tend",)),
    ]
    assert [j.fautif for j in justes] == ["Le mois d’avril."]
    assert laisses["option coupee par defaut"] == 1
    assert laisses["option ou section ecartee"] == 1


def test_une_faute_est_jugee_a_sa_place():
    import banc_grammalecte as banc

    phrase = "Qui on tant de malheurs !"
    places = ((4, 6), (7, 11))
    on = banc.Faute("r", "conf", phrase, 4, 6, ("ont",), places)
    tant = banc.Faute("r", "conf", phrase, 7, 11, ("tend",), places)
    assert banc.juger(on, "Qui ont tant de malheurs !") == "corrigee"
    assert banc.juger(tant, "Qui ont tant de malheurs !") == "laissee"
    assert banc.juger(on, "Qui sont tant de malheurs !") == "fausse"
    assert banc.juger(on, "Qui ont tant de malheur !") == "ailleurs"


@pytest.fixture(scope="module")
def mesures(correcteur):
    import banc_grammalecte as banc

    resultats = {}
    for moitie in ("dev", "ecart"):
        fautes, justes = banc.charger(moitie)
        r = banc.evaluer(correcteur, fautes, justes)
        resultats[moitie] = {
            "rappel": len(r["corrigees"]) / len(fautes),
            "abimees": len(r["abimees"]) / len(justes),
        }
    return resultats


@pytest.mark.parametrize("moitie,rappel_minimal,abimees_maximum", [
    ("dev", 0.05, 0.065),
    ("ecart", 0.07, 0.045),
])
def test_le_banc_ne_recule_pas(mesures, moitie, rappel_minimal, abimees_maximum):
    m = mesures[moitie]
    assert m["rappel"] >= rappel_minimal, m
    assert m["abimees"] <= abimees_maximum, m
