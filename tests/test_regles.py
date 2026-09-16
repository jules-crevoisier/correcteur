# -*- coding: utf-8 -*-
"""Tests des listes de protection.

Une liste ecrite a la main vieillit en silence. Celles-ci sont donc
recalculees ici a partir du dictionnaire : si le jour vient ou il change, le
test le dit au lieu de laisser la liste derailler toute seule.
"""

import sys
from pathlib import Path
import pytest


RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import regles  # noqa: E402


def _trompeurs(lexique) -> set[str]:
    """Les mots anglais qui sont un mot francais courant sans son accent."""
    trompeurs = set()
    for mot in regles.LEXIQUE_ANGLAIS | regles.ANGLAIS_TROMPEURS:
        if lexique.connait(mot):
            # Le mot est aussi francais tel quel : rien ne le menace.
            continue
        jumelles = [f for f in lexique.formes(mot) if f.lower() != mot]
        if jumelles and min(lexique.rang(f) for f in jumelles) \
                <= regles.RANG_FRANCAIS_EVIDENT:
            trompeurs.add(mot)
    return trompeurs


def test_la_liste_des_trompeurs_est_celle_du_dictionnaire(lexique):
    """« president » doit pouvoir devenir « président »."""
    calcules = _trompeurs(lexique)
    assert calcules == regles.ANGLAIS_TROMPEURS, (
        f"a ajouter : {sorted(calcules - regles.ANGLAIS_TROMPEURS)}\n"
        f"a retirer : {sorted(regles.ANGLAIS_TROMPEURS - calcules)}"
    )


def test_les_trompeurs_ne_protegent_plus(correcteur):
    for fautif, attendu in [
        ("une decision importante", "une décision importante"),
        ("le president a parlé", "le président a parlé"),
        ("son role est clair", "son rôle est clair"),
        ("une belle experience", "une belle expérience"),
        ("le college est fermé", "le collège est fermé"),
        ("la difference est nette", "la différence est nette"),
    ]:
        assert correcteur.corriger(fautif)[0] == attendu


def test_l_anglais_reste_protege(correcteur):
    """La protection garde ceux dont le jumeau francais est rare ou absurde."""
    for phrase in ["the best of the best", "he said no", "i hate that",
                   "come here", "this is a great event"]:
        assert correcteur.corriger(phrase)[0] == phrase


# ---------------------------------------------------------------------------
# Les noms a capitale interieure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texte", [
    "j'ai perdu mon iPhone",
    "c'est écrit en JavaScript",
    "le dépôt est sur GitHub",
    "je suis sur macOS",
    "regarde sur YouTube",
])
def test_une_capitale_interieure_protege_le_mot(correcteur, texte):
    """« iPhone » devenait « phone » : aucun mot français n'a de capitale
    au milieu."""
    assert correcteur.corriger(texte)[0] == texte


@pytest.mark.parametrize("texte,attendu", [
    # La protection ne doit pas s'etendre aux mots ordinaires capitalises.
    ("Bonjour tout le monde", "Bonjour tout le monde"),
    ("jai pas vu", "j'ai pas vu"),
])
def test_la_capitale_ordinaire_ne_protege_rien(correcteur, texte, attendu):
    assert correcteur.corriger(texte)[0] == attendu


@pytest.mark.parametrize("texte", [
    "il faut débugger le endpoint",
    "on fait un scrum tous les matins",
    "le layout du dashboard",
    "envoie-moi un email",
    "le runner de la pipeline",
])
def test_le_vocabulaire_technique_reste_entier(correcteur, texte):
    assert correcteur.corriger(texte)[0] == texte
