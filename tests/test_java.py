# -*- coding: utf-8 -*-
"""Tests de la localisation du moteur Java."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from correcteur import chemins, java  # noqa: E402


class FauxResultat:
    def __init__(self, stderr="", stdout=""):
        self.stderr = stderr
        self.stdout = stdout


@pytest.mark.parametrize("sortie,attendu", [
    # `java -version` ecrit sur la sortie d'erreur, dans des formats varies.
    ('openjdk version "21.0.10" 2026-01-20', 21),
    ('openjdk version "17.0.9" 2023-10-17', 17),
    ('java version "1.8.0_381"', 8),
    ('openjdk version "11.0.21" 2023-10-17', 11),
])
def test_lecture_de_la_version(monkeypatch, sortie, attendu):
    monkeypatch.setattr(java.subprocess, "run",
                        lambda *a, **k: FauxResultat(stderr=sortie))
    assert java.version(Path("java")) == attendu


def test_version_illisible(monkeypatch):
    monkeypatch.setattr(java.subprocess, "run",
                        lambda *a, **k: FauxResultat(stderr="rien de parlant"))
    assert java.version(Path("java")) is None


def test_executable_absent(monkeypatch):
    def echec(*a, **k):
        raise OSError("introuvable")
    monkeypatch.setattr(java.subprocess, "run", echec)
    assert java.version(Path("java")) is None


def test_le_jre_portable_est_prioritaire(monkeypatch, tmp_path):
    """Un Java livre avec l'application prime sur celui du systeme."""
    portable = tmp_path / "jre" / "bin" / "java"
    portable.parent.mkdir(parents=True)
    portable.write_text("")
    systeme = tmp_path / "systeme" / "java"
    systeme.parent.mkdir(parents=True)
    systeme.write_text("")

    monkeypatch.setattr(java, "dossiers_jre", lambda: [tmp_path / "jre"])
    monkeypatch.setattr(java.shutil, "which", lambda _: str(systeme))
    monkeypatch.setattr(java, "version", lambda _: 21)

    assert java.trouver() == portable


def test_un_java_trop_ancien_est_refuse(monkeypatch, tmp_path):
    ancien = tmp_path / "java"
    ancien.write_text("")
    monkeypatch.setattr(java, "dossiers_jre", lambda: [])
    monkeypatch.setattr(java.shutil, "which", lambda _: str(ancien))
    monkeypatch.setattr(java, "version", lambda _: 8)

    with pytest.raises(java.JavaIntrouvable, match="Java 8"):
        java.trouver()


def test_message_clair_quand_java_manque(monkeypatch):
    monkeypatch.setattr(java, "dossiers_jre", lambda: [])
    monkeypatch.setattr(java.shutil, "which", lambda _: None)
    monkeypatch.setattr(java.os, "environ", {})
    monkeypatch.setattr(java.os, "name", "posix")

    with pytest.raises(java.JavaIntrouvable, match="introuvable"):
        java.trouver()


def test_preparer_met_java_en_tete_du_path(monkeypatch, tmp_path):
    executable = tmp_path / "bin" / "java"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    environnement = {"PATH": "/usr/bin"}

    monkeypatch.setattr(java, "trouver", lambda: executable)
    monkeypatch.setattr(java.os, "environ", environnement)

    assert java.preparer() == executable
    assert environnement["PATH"].split(":")[0] == str(executable.parent)
    assert environnement["JAVA_HOME"] == str(tmp_path)


def test_le_path_nest_pas_duplique(monkeypatch, tmp_path):
    executable = tmp_path / "bin" / "java"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    environnement = {"PATH": str(executable.parent) + ":/usr/bin"}

    monkeypatch.setattr(java, "trouver", lambda: executable)
    monkeypatch.setattr(java.os, "environ", environnement)

    java.preparer()
    assert environnement["PATH"].count(str(executable.parent)) == 1


def test_moteur_local_detecte(monkeypatch, tmp_path):
    (tmp_path / "moteur").mkdir()
    monkeypatch.setattr(chemins, "racine_application", lambda: tmp_path)
    assert chemins.dossier_moteur() == tmp_path / "moteur"


def test_pas_de_moteur_local(monkeypatch, tmp_path):
    monkeypatch.setattr(chemins, "racine_application", lambda: tmp_path)
    assert chemins.dossier_moteur() is None
