# -*- coding: utf-8 -*-
"""Ou corriger, et sur quel ton.

Corriger partout de la meme facon est une mauvaise idee. Une correction
automatique dans un terminal, un editeur de code ou une console de jeu ne
rend service a personne : elle transforme une commande en prose. Et le ton
d'un message Discord n'est pas celui d'une lettre de motivation.

Ce module repond donc a deux questions, application par application :

    faut-il corriger ici ?          -> `corrige_ici`
    et dans quel registre ?         -> `registre_ici`

Il sait aussi reconnaitre l'application au premier plan sous Windows. Ailleurs
— et c'est le cas pendant les tests — il repond « je ne sais pas », et la
politique se rabat sur ses valeurs par defaut.
"""

from __future__ import annotations

import os

PARLE = "parle"
SOUTENU = "soutenu"
REGISTRES = (PARLE, SOUTENU)

# Applications ou la correction automatique fait plus de mal que de bien.
# L'utilisateur peut completer ou vider cette liste.
EXCLUES_PAR_DEFAUT = [
    # Terminaux
    "cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe",
    "wt.exe", "conhost.exe", "putty.exe", "mintty.exe", "alacritty.exe",
    # Editeurs de code
    "code.exe", "devenv.exe", "sublime_text.exe", "notepad++.exe",
    "idea64.exe", "pycharm64.exe", "webstorm64.exe", "clion64.exe",
    "rider64.exe", "atom.exe", "vim.exe", "gvim.exe", "emacs.exe",
    # Outils ou la frappe n'est pas du texte
    "regedit.exe", "mstsc.exe", "vmware.exe", "virtualbox.exe",
]


def _nom_processus_windows() -> str | None:
    """Le nom du programme dont la fenetre est au premier plan, ou None."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    fenetre = user32.GetForegroundWindow()
    if not fenetre:
        return None

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fenetre, ctypes.byref(pid))
    if not pid.value:
        return None

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    processus = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,
                                     False, pid.value)
    if not processus:
        return None
    try:
        tampon = ctypes.create_unicode_buffer(512)
        taille = wintypes.DWORD(len(tampon))
        if not kernel32.QueryFullProcessImageNameW(processus, 0, tampon,
                                                   ctypes.byref(taille)):
            return None
        return tampon.value.rsplit("\\", 1)[-1].lower()
    finally:
        kernel32.CloseHandle(processus)


def application_active() -> str | None:
    """« discord.exe », « code.exe »... None si la question n'a pas de sens ici."""
    if os.name != "nt":
        return None
    try:
        return _nom_processus_windows()
    except Exception:
        # Une application protegee peut refuser d'etre interrogee ; ce n'est
        # pas une raison pour cesser de corriger.
        return None


class Politique:
    """Ce que Papote a le droit de faire, application par application."""

    def __init__(self, exclues: list[str] | None = None,
                 registres: dict[str, str] | None = None,
                 registre_defaut: str = PARLE):
        self.exclues = {self._normaliser(nom) for nom in (exclues or []) if nom}
        self.registres = {
            self._normaliser(nom): registre
            for nom, registre in (registres or {}).items()
            if registre in REGISTRES
        }
        self.registre_defaut = (
            registre_defaut if registre_defaut in REGISTRES else PARLE
        )

    @staticmethod
    def _normaliser(nom: str) -> str:
        """« C:\\...\\Discord.exe » et « discord » designent la meme application."""
        propre = nom.strip().lower().replace("/", "\\").rsplit("\\", 1)[-1]
        return propre[:-4] if propre.endswith(".exe") else propre

    def corrige_ici(self, application: str | None) -> bool:
        """Faut-il corriger dans cette application ?

        Une application inconnue — parce qu'on ne sait pas la nommer, ou qu'on
        n'est pas sous Windows — est traitee comme n'importe quelle autre :
        ne rien corriger du tout serait pire que de corriger a tort.
        """
        if application is None:
            return True
        return self._normaliser(application) not in self.exclues

    def registre_ici(self, application: str | None) -> str:
        if application is None:
            return self.registre_defaut
        return self.registres.get(self._normaliser(application),
                                  self.registre_defaut)

    # -- modifications ------------------------------------------------------

    def exclure(self, application: str) -> None:
        self.exclues.add(self._normaliser(application))

    def reintegrer(self, application: str) -> None:
        self.exclues.discard(self._normaliser(application))


def depuis_config(config: dict) -> Politique:
    return Politique(
        exclues=config.get("applications_exclues"),
        registres=config.get("registre_par_application"),
        registre_defaut=config.get("registre", PARLE),
    )
