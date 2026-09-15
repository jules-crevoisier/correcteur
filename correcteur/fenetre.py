# -*- coding: utf-8 -*-
"""Une fenetre pour corriger un texte sans passer par le raccourci.

Le raccourci global reste la facon normale de se servir de l'outil : il
corrige le texte la ou il est ecrit, sans rien ouvrir. Cette fenetre existe
pour les deux cas ou il ne suffit pas — decouvrir l'outil au premier
lancement, et relire un texte avant de l'envoyer.

Elle n'utilise que tkinter, livre avec Python : rien a installer.
"""

from __future__ import annotations

import threading
import tkinter as tk

FOND = "#1e1f22"
FOND_CHAMP = "#2b2d31"
TEXTE = "#e6e6e6"
TEXTE_DOUX = "#9aa0a6"
ACCENT = "#2b7ade"


class Fenetre:
    """Coller, corriger, copier."""

    def __init__(self, app):
        self.app = app
        self.racine = tk.Tk()
        self.racine.title("Correcteur")
        self.racine.geometry("620x420")
        self.racine.minsize(420, 300)
        self.racine.configure(bg=FOND)
        self._construire()

    # -- construction -------------------------------------------------------

    def _construire(self) -> None:
        cadre = tk.Frame(self.racine, bg=FOND, padx=16, pady=14)
        cadre.pack(fill="both", expand=True)

        tk.Label(
            cadre,
            text="Écrivez ou collez votre texte, puis Ctrl+Entrée.",
            bg=FOND, fg=TEXTE_DOUX, anchor="w", font=("Segoe UI", 10),
        ).pack(fill="x", pady=(0, 8))

        self.champ = tk.Text(
            cadre, wrap="word", bg=FOND_CHAMP, fg=TEXTE, insertbackground=TEXTE,
            relief="flat", padx=12, pady=10, font=("Segoe UI", 11),
            undo=True, highlightthickness=1, highlightbackground="#3a3d43",
        )
        self.champ.pack(fill="both", expand=True)
        self.champ.focus_set()

        barre = tk.Frame(cadre, bg=FOND, pady=10)
        barre.pack(fill="x")

        self.bouton = tk.Button(
            barre, text="Corriger", command=self.corriger, relief="flat",
            bg=ACCENT, fg="white", activebackground="#3f8ae8",
            activeforeground="white", padx=18, pady=6, font=("Segoe UI", 10, "bold"),
            cursor="hand2", borderwidth=0,
        )
        self.bouton.pack(side="left")

        tk.Button(
            barre, text="Copier", command=self.copier, relief="flat",
            bg=FOND_CHAMP, fg=TEXTE, activebackground="#3a3d43",
            activeforeground=TEXTE, padx=18, pady=6, font=("Segoe UI", 10),
            cursor="hand2", borderwidth=0,
        ).pack(side="left", padx=(8, 0))

        self.etat = tk.Label(
            cadre, text=self._rappel_raccourci(), bg=FOND, fg=TEXTE_DOUX,
            anchor="w", justify="left", wraplength=560, font=("Segoe UI", 9),
        )
        self.etat.pack(fill="x")

        self.racine.bind("<Control-Return>", lambda _: self.corriger())
        self.racine.bind("<Escape>", lambda _: self.racine.destroy())

        # Le dictionnaire se charge pendant que l'utilisateur tape.
        threading.Thread(target=self._precharger, daemon=True).start()

    def _rappel_raccourci(self) -> str:
        raccourci = self.app.config.get("raccourci", "ctrl+alt+c").upper()
        return (f"Ailleurs sur l'ordinateur : sélectionnez votre texte "
                f"et appuyez sur {raccourci}.")

    def _precharger(self) -> None:
        try:
            self.app.correcteur  # noqa: B018
        except Exception:
            pass

    # -- actions ------------------------------------------------------------

    def corriger(self) -> None:
        texte = self.champ.get("1.0", "end-1c")
        if not texte.strip():
            return

        self.bouton.configure(text="…", state="disabled")
        self.etat.configure(text="Correction en cours…")

        def travailler():
            try:
                resultat = self.app.corriger_texte(texte)
            except Exception as e:  # dictionnaire absent, par exemple
                self.racine.after(0, self._echouer, str(e))
                return
            self.racine.after(0, self._afficher, *resultat)

        threading.Thread(target=travailler, daemon=True).start()

    def _afficher(self, corrige: str, corrections: list) -> None:
        self.bouton.configure(text="Corriger", state="normal")
        self.champ.delete("1.0", "end")
        self.champ.insert("1.0", corrige)

        if not corrections:
            self.etat.configure(text="Aucune faute trouvée. " + self._rappel_raccourci())
            return

        detail = " · ".join(str(c) for c in corrections[:6])
        if len(corrections) > 6:
            detail += f" · (+{len(corrections) - 6})"
        pluriel = "s" if len(corrections) > 1 else ""
        self.etat.configure(text=f"{len(corrections)} correction{pluriel} : {detail}")

    def _echouer(self, message: str) -> None:
        self.bouton.configure(text="Corriger", state="normal")
        self.etat.configure(text=message.split("\n")[0])

    def copier(self) -> None:
        texte = self.champ.get("1.0", "end-1c")
        self.racine.clipboard_clear()
        self.racine.clipboard_append(texte)
        self.etat.configure(text="Texte copié dans le presse-papiers.")

    # -- boucle -------------------------------------------------------------

    def lancer(self) -> None:
        self.racine.mainloop()
