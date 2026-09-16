# -*- coding: utf-8 -*-
"""Tests de la politique : ou corriger, et sur quel ton."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote.politique import PARLE, SOUTENU, Politique, application_active  # noqa: E402


@pytest.fixture
def politique():
    return Politique(
        exclues=["cmd.exe", "Code.exe"],
        registres={"outlook.exe": SOUTENU, "thunderbird.exe": "n'importe quoi"},
    )


@pytest.mark.parametrize("application", [
    "cmd.exe", "CMD.EXE", "code.exe",
    r"C:\Program Files\Microsoft VS Code\Code.exe",
    "/usr/bin/code.exe", "code",
])
def test_les_applications_exclues_le_sont_quelle_que_soit_leur_ecriture(
        politique, application):
    assert politique.corrige_ici(application) is False


@pytest.mark.parametrize("application", ["discord.exe", "notepad.exe", "word.exe"])
def test_ailleurs_on_corrige(politique, application):
    assert politique.corrige_ici(application) is True


def test_une_application_inconnue_est_traitee_comme_les_autres(politique):
    """Hors de Windows on ne sait pas nommer la fenetre : ce n'est pas une
    raison pour cesser de corriger partout."""
    assert politique.corrige_ici(None) is True


def test_le_registre_suit_l_application(politique):
    assert politique.registre_ici("outlook.exe") == SOUTENU
    assert politique.registre_ici("discord.exe") == PARLE
    assert politique.registre_ici(None) == PARLE


def test_un_registre_inconnu_est_ignore(politique):
    """Un fichier de reglages abime ne doit pas inventer un troisieme ton."""
    assert politique.registre_ici("thunderbird.exe") == PARLE


def test_le_registre_par_defaut_peut_etre_soutenu():
    politique = Politique(registre_defaut=SOUTENU)
    assert politique.registre_ici("discord.exe") == SOUTENU
    assert politique.registre_ici(None) == SOUTENU


def test_exclure_et_reintegrer(politique):
    politique.exclure("Discord.exe")
    assert politique.corrige_ici("discord.exe") is False
    politique.reintegrer("discord")
    assert politique.corrige_ici("discord.exe") is True


def test_l_application_active_ne_leve_jamais():
    """Hors de Windows, la question n'a pas de reponse — pas d'exception."""
    assert application_active() is None or isinstance(application_active(), str)
