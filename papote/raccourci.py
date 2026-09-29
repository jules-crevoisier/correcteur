# -*- coding: utf-8 -*-
"""Raccourci clavier global, et lecture des combinaisons choisies."""

from __future__ import annotations

import os
import threading
from typing import Callable


# Ce que tkinter appelle une touche, et ce que la bibliotheque `keyboard`
# attend en retour.
TOUCHES_TKINTER = {
    "Control_L": "ctrl", "Control_R": "ctrl",
    "Alt_L": "alt", "Alt_R": "alt", "ISO_Level3_Shift": "alt",
    "Shift_L": "shift", "Shift_R": "shift",
    "Super_L": "windows", "Super_R": "windows",
    "Win_L": "windows", "Win_R": "windows",
    "space": "space", "Return": "enter", "Tab": "tab",
    "Prior": "page up", "Next": "page down",
    "Insert": "insert", "Home": "home", "End": "end",
    "Up": "up", "Down": "down", "Left": "left", "Right": "right",
}

MODIFICATEURS = ("ctrl", "alt", "shift", "windows")


def nom_de_touche(keysym: str) -> str | None:
    """Traduit la touche annoncee par tkinter. None si elle ne sert a rien."""
    if keysym in TOUCHES_TKINTER:
        return TOUCHES_TKINTER[keysym]
    if len(keysym) == 1:
        return keysym.lower()
    if keysym.lower().startswith("f") and keysym[1:].isdigit():
        return keysym.lower()
    return None


class RaccourciInvalide(ValueError):
    """La combinaison n'est pas comprise par le systeme."""


# -- RegisterHotKey ----------------------------------------------------------
#
# `keyboard.add_hotkey(..., suppress=True)` installe un crochet *bloquant* sur
# chaque touche de la combinaison. Pour « ctrl+alt+c », cela veut dire que
# chaque appui sur Ctrl, dans n'importe quelle application, attend qu'un
# programme Python ait fini de deliberer avant d'atteindre son destinataire.
# Dans un jeu — qui lit Ctrl des dizaines de fois par seconde —, c'est un
# retard perceptible sur une touche qui ne devrait jamais en avoir. Et quatre
# raccourcis, c'etait quatre crochets de ce genre.
#
# `RegisterHotKey` fait la meme chose sans rien s'interposer : le systeme
# reconnait la combinaison lui-meme, et ne previent Papote que quand elle
# est complete. Les autres touches ne passent par aucun code de Papote.

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

_MODIFICATEURS_WINDOWS = {
    "alt": MOD_ALT, "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "shift": MOD_SHIFT, "windows": MOD_WIN, "win": MOD_WIN,
}

_TOUCHES_WINDOWS = {
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "insert": 0x2D, "home": 0x24,
    "end": 0x23, "page up": 0x21, "page down": 0x22, "left": 0x25,
    "up": 0x26, "right": 0x27, "down": 0x28,
}


def analyser_combinaison(combinaison: str,
                         code_du_caractere: Callable[[str], int] | None = None
                         ) -> tuple[int, int]:
    """« ctrl+alt+c » -> (modificateurs, code de touche virtuelle).

    `code_du_caractere` traduit un caractere ponctuel (« é », « ; ») selon la
    disposition du clavier ; sans lui, seules les touches nommees passent.
    Leve `RaccourciInvalide` quand la combinaison n'a pas de sens.
    """
    parties = [p.strip().lower() for p in combinaison.split("+") if p.strip()]
    if not parties:
        raise RaccourciInvalide(f"« {combinaison} » est vide.")
    modificateurs = 0
    touche = None
    for partie in parties:
        if partie in _MODIFICATEURS_WINDOWS:
            modificateurs |= _MODIFICATEURS_WINDOWS[partie]
        elif touche is not None:
            raise RaccourciInvalide(f"« {combinaison} » a deux touches.")
        else:
            touche = partie
    if touche is None or not modificateurs:
        # Une touche seule, comme « a », volerait la frappe de tout le monde.
        raise RaccourciInvalide(
            f"« {combinaison} » n'est pas une combinaison valide.")
    if touche in _TOUCHES_WINDOWS:
        return modificateurs, _TOUCHES_WINDOWS[touche]
    if len(touche) == 1 and touche.isascii() and touche.isalnum():
        return modificateurs, ord(touche.upper())
    if touche[0] == "f" and touche[1:].isdigit() and 1 <= int(touche[1:]) <= 24:
        return modificateurs, 0x70 + int(touche[1:]) - 1
    if len(touche) == 1 and code_du_caractere is not None:
        code = code_du_caractere(touche)
        if code:
            return modificateurs, code
    raise RaccourciInvalide(f"« {combinaison} » n'est pas une combinaison valide.")


class _CrochetSysteme:
    """Une combinaison reconnue par Windows, sans crochet clavier."""

    def __init__(self, modificateurs: int, touche: int,
                 action: Callable[[], None], identifiant: int):
        self.modificateurs = modificateurs
        self.touche = touche
        self.action = action
        self.identifiant = identifiant
        self._fil: threading.Thread | None = None
        self._fil_id = 0
        self._pret = threading.Event()
        self._pose = False

    def demarrer(self) -> bool:
        """Vrai si Windows a accepte la combinaison."""
        self._fil = threading.Thread(target=self._boucle, daemon=True,
                                     name="papote-raccourci")
        self._fil.start()
        self._pret.wait(2.0)
        return self._pose

    def _boucle(self) -> None:
        import ctypes
        from ctypes import wintypes

        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        # La file de messages du fil n'existe qu'une fois interrogee : sans
        # cela, un WM_QUIT posté trop tot se perdrait.
        message = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        self._fil_id = kernel32.GetCurrentThreadId()
        self._pose = bool(user32.RegisterHotKey(
            None, self.identifiant, self.modificateurs | MOD_NOREPEAT,
            self.touche))
        self._pret.set()
        if not self._pose:
            return
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY:
                    # L'action ne doit pas retenir la boucle : elle copie
                    # une selection, ecrit, attend le presse-papiers...
                    threading.Thread(target=self._lancer, daemon=True).start()
        finally:
            user32.UnregisterHotKey(None, self.identifiant)

    def _lancer(self) -> None:
        try:
            self.action()
        except Exception:                          # noqa: BLE001
            pass

    def arreter(self) -> None:
        if self._fil is None:
            return
        try:
            import ctypes

            if self._fil_id:
                ctypes.windll.user32.PostThreadMessageW(
                    self._fil_id, WM_QUIT, 0, 0)
            self._fil.join(timeout=1.0)
        except Exception:                          # noqa: BLE001
            pass
        self._fil = None
        self._pose = False


def _code_du_caractere_windows(caractere: str) -> int:
    import ctypes

    reponse = ctypes.windll.user32.VkKeyScanW(caractere) & 0xFFFF
    return 0 if reponse == 0xFFFF else reponse & 0xFF


_identifiants = iter(range(0x5000, 0x6000))


class Raccourci:
    """Associe une combinaison de touches a une action, partout dans le systeme."""

    def __init__(self, combinaison: str, action: Callable[[], None]):
        self.combinaison = combinaison
        self.action = action
        self._enregistre = None
        self._systeme: _CrochetSysteme | None = None

    def _activer_par_le_systeme(self) -> bool:
        """Windows reconnait la combinaison lui-meme : rien ne s'interpose."""
        if os.name != "nt":
            return False
        try:
            modificateurs, touche = analyser_combinaison(
                self.combinaison, _code_du_caractere_windows)
            crochet = _CrochetSysteme(modificateurs, touche, self.action,
                                      next(_identifiants))
            if not crochet.demarrer():
                # Prise par un autre programme, ou refusee : on retombe sur
                # la bibliotheque, qui s'accommode de tout.
                crochet.arreter()
                return False
        except Exception:                          # noqa: BLE001
            return False
        self._systeme = crochet
        return True

    def activer(self) -> None:
        if self.actif or not self.combinaison:
            return
        if self._activer_par_le_systeme():
            return
        import keyboard

        try:
            # Pas de `suppress=True` : il rend le crochet bloquant sur chaque
            # touche de la combinaison — Ctrl compris. Voir plus haut.
            self._enregistre = keyboard.add_hotkey(
                self.combinaison, self.action, suppress=False
            )
        except (ValueError, KeyError) as e:
            # Une combinaison saisie a la main peut etre incomprehensible :
            # « ctrl+alt+é » sur un clavier qui n'en a pas, par exemple.
            raise RaccourciInvalide(
                f"« {self.combinaison} » n'est pas une combinaison valide."
            ) from e

    def desactiver(self) -> None:
        if self._systeme is not None:
            self._systeme.arreter()
            self._systeme = None
            return
        if self._enregistre is None:
            return
        import keyboard

        try:
            keyboard.remove_hotkey(self._enregistre)
        except (KeyError, ValueError):
            # Deja retire : rien a faire.
            pass
        self._enregistre = None

    @property
    def actif(self) -> bool:
        return self._enregistre is not None or self._systeme is not None
