# -*- coding: utf-8 -*-
"""Tests de bout en bout sur des messages tels qu'on les ecrit vraiment.

test_grammaire.py juge chaque regle isolement ; ici on juge le resultat :
un message tape a la va-vite doit ressortir correct, sans avoir change de
ton.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


MESSAGES = [
    (
        "salut sa va ? jai pas compris se que tu voulais dire dsl",
        "salut ça va ? j'ai pas compris ce que tu voulais dire dsl",
    ),
    (
        "ils on mangé tout les gateaux, jai rien eu",
        "ils ont mangé tous les gâteaux, j'ai rien eu",
    ),
    (
        "cest vraiment tres interressant se truc",
        "c'est vraiment très intéressant ce truc",
    ),
    (
        "je peut pas venir ce soir, ca ma pris trop de temps",
        "je peux pas venir ce soir, ça m'a pris trop de temps",
    ),
    (
        "tas vu ou est passé mon telephone ?",
        "t'as vu où est passé mon téléphone ?",
    ),
    (
        "faut que j'aille a la gare, je suis deja en retard",
        "faut que j'aille à la gare, je suis déjà en retard",
    ),
    (
        "elles sont venu hier mes elles sont reparties tot",
        "elles sont venues hier mais elles sont reparties tôt",
    ),
    (
        "quand meme cetait un bon film",
        "quand même c'était un bon film",
    ),
]

# Des messages sans faute, ecrits comme on parle : ils doivent ressortir
# a la virgule pres.
DEJA_CORRECTS = [
    "j'ai pas eu le temps, on se voit demain ?",
    "tkt c'est bon, y a pas de souci",
    "je suis passé te voir hier soir, mais tu n'étais pas là.",
    "wsh tu fais quoi ce soir frr",
    "c'est quoi ce truc mdr",
    "faut que j'y aille, à plus",
]


@pytest.mark.parametrize("message,attendu", MESSAGES)
def test_un_message_tape_vite_ressort_correct(correcteur, message, attendu):
    assert correcteur.corriger(message)[0] == attendu


@pytest.mark.parametrize("message", DEJA_CORRECTS)
def test_un_message_correct_ressort_identique(correcteur, message):
    corrige, corrections = correcteur.corriger(message)
    assert corrige == message, f"corrections indues : {[str(c) for c in corrections]}"


def test_un_message_de_plusieurs_lignes(correcteur):
    message = "salut,\nsa va ?\nmoi jai pas le temps"
    attendu = "salut,\nça va ?\nmoi j'ai pas le temps"
    assert correcteur.corriger(message)[0] == attendu


def test_le_correcteur_est_rapide(correcteur):
    """Un message Discord doit se corriger sans qu'on le sente."""
    import time

    message = "cest vraiment tres interressant se truc, jai pas tout compris " * 5
    debut = time.time()
    correcteur.corriger(message)
    assert time.time() - debut < 1.0
