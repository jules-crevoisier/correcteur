# -*- coding: utf-8 -*-
"""Le banc LanguageTool, en garde-fou.

Il est long (une minute) et demande le fichier de LanguageTool, telecharge
une fois dans « outils/cache ». Il ne tourne donc que sur demande :

    PAPOTE_BANC=1 python -m pytest tests/test_banc_languagetool.py

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
    reason="banc LanguageTool : PAPOTE_BANC=1 pour le lancer",
)


@pytest.fixture(scope="module")
def mesures(correcteur):
    import banc_languagetool as banc

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
    ("dev", 0.09, 0.085),
    ("ecart", 0.11, 0.135),
])
def test_le_banc_ne_recule_pas(mesures, moitie, rappel_minimal, abimees_maximum):
    m = mesures[moitie]
    assert m["rappel"] >= rappel_minimal, m
    assert m["abimees"] <= abimees_maximum, m
