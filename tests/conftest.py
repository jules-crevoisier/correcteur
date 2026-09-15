# -*- coding: utf-8 -*-
"""Fixtures partagees.

Le dictionnaire reel se charge en un dixieme de seconde : les tests s'en
servent directement plutot que de simuler un moteur qui ne ressemblerait a
rien. Il est charge une fois pour toute la session.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote.lexique import Lexique, LexiqueIntrouvable  # noqa: E402
from papote.moteur import Correcteur  # noqa: E402


@pytest.fixture(scope="session")
def lexique():
    lex = Lexique()
    try:
        lex.charger()
    except LexiqueIntrouvable as e:
        pytest.skip(f"dictionnaire absent : {e}")
    return lex


@pytest.fixture(scope="session")
def correcteur(lexique):
    return Correcteur(lexique)
