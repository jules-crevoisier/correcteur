# -*- coding: utf-8 -*-
"""Reconnaitre un jeu au premier plan, pour s'effacer devant lui.

Papote ecoute le clavier par un crochet global : toutes les touches de la
machine y passent, pas seulement celles d'un traitement de texte. Dans un
jeu, ce detour se paie en retard sur les touches — et l'on n'ecrit pas de
prose au milieu d'une partie. Tant qu'un jeu est au premier plan, Papote
decroche donc ses crochets, et les remet quand on revient a autre chose.

Comment reconnait-on un jeu ? Il n'y a pas de signe infaillible, mais deux
indices se recoupent :

    - une fenetre qui couvre tout l'ecran et n'a ni barre de titre ni
      bordure — c'est ce que font le plein ecran et le « fenetre sans
      bordure » de presque tous les jeux ;
    - un programme que l'utilisateur a lui-meme designe.

Un navigateur en plein ecran (F11, une video) remplit les memes conditions
mais on y ecrit parfois : ces programmes-la ne comptent jamais comme des jeux.
"""

from __future__ import annotations

import os

from .politique import Politique, _nom_processus_windows

# Des programmes qui passent en plein ecran sans etre des jeux, et ou l'on
# peut avoir envie d'ecrire.
PAS_DES_JEUX = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
    "vivaldi.exe", "iexplore.exe", "explorer.exe", "winword.exe",
    "excel.exe", "powerpnt.exe", "onenote.exe", "outlook.exe", "acrobat.exe",
    "acrord32.exe", "discord.exe", "teams.exe", "slack.exe", "zoom.exe",
    "vlc.exe", "mpv.exe", "obs64.exe", "obs32.exe", "code.exe",
}

_CLASSES_DU_BUREAU = {"progman", "workerw", "shell_traywnd", "shellexperiencehost"}

_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_GWL_STYLE = -16
_MONITOR_DEFAULTTONEAREST = 2


def _fenetre_plein_ecran() -> bool:
    """La fenetre au premier plan couvre-t-elle tout l'ecran, sans cadre ?"""
    import ctypes
    from ctypes import wintypes

    # Une instance a part : declarer les types des arguments sur la
    # bibliotheque partagee changerait le comportement des autres modules.
    user32 = ctypes.WinDLL("user32")
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    fenetre = user32.GetForegroundWindow()
    if not fenetre:
        return False

    classe = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(fenetre, classe, len(classe))
    if classe.value.lower() in _CLASSES_DU_BUREAU:
        return False

    style = user32.GetWindowLongW(fenetre, _GWL_STYLE)
    if style & _WS_CAPTION == _WS_CAPTION or style & _WS_THICKFRAME:
        # Une barre de titre ou une bordure qu'on peut tirer : une fenetre
        # ordinaire, meme agrandie au maximum.
        return False

    rectangle = wintypes.RECT()
    if not user32.GetWindowRect(fenetre, ctypes.byref(rectangle)):
        return False

    class InfosEcran(ctypes.Structure):
        _fields_ = [("taille", wintypes.DWORD), ("ecran", wintypes.RECT),
                    ("travail", wintypes.RECT), ("drapeaux", wintypes.DWORD)]

    ecran = user32.MonitorFromWindow(fenetre, _MONITOR_DEFAULTTONEAREST)
    infos = InfosEcran()
    infos.taille = ctypes.sizeof(InfosEcran)
    if not ecran or not user32.GetMonitorInfoW(ecran, ctypes.addressof(infos)):
        return False

    e = infos.ecran
    return (rectangle.left <= e.left and rectangle.top <= e.top
            and rectangle.right >= e.right and rectangle.bottom >= e.bottom)


def jeu_au_premier_plan(designes: list[str] | None = None,
                        application: str | None = None) -> bool:
    """Un jeu est-il au premier plan ? Faux quand on ne sait pas."""
    if os.name != "nt":
        return False
    try:
        nom = application if application is not None else _nom_processus_windows()
        if nom is None:
            return False
        nom = nom.lower()
        normalise = Politique._normaliser
        if designes and normalise(nom) in {normalise(d) for d in designes if d}:
            return True
        if nom in PAS_DES_JEUX:
            return False
        return _fenetre_plein_ecran()
    except Exception:                              # noqa: BLE001
        # Le doute ne doit pas faire taire Papote.
        return False
