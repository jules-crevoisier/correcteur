# -*- coding: utf-8 -*-
"""La fenetre : corriger, apprendre, regler.

Le correcteur travaille normalement sans se montrer — il corrige pendant
qu'on ecrit. Cette fenetre sert aux trois choses qu'il ne peut pas faire tout
seul :

    Corriger          relire un texte avant de l'envoyer ;
    Mon dictionnaire  lui apprendre un mot ou une abreviation ;
    Reglages          changer ce qu'il fait, sans editer de fichier.

Elle n'utilise que tkinter, livre avec Python : rien a installer. Les onglets
sont faits maison plutot qu'avec `ttk.Notebook`, qui suit le theme du systeme
et jurerait au milieu du reste.
"""

from __future__ import annotations

import threading
import tkinter as tk

from . import config as config_mod
from . import demarrage, regles
from .lexique import LexiqueIntrouvable
from .moteur import _normaliser_mot

FOND = "#1e1f22"
FOND_CHAMP = "#2b2d31"
FOND_SURVOL = "#3a3d43"
TEXTE = "#e6e6e6"
TEXTE_DOUX = "#9aa0a6"
ACCENT = "#2b7ade"
POLICE = "Segoe UI"


def _bouton(parent, texte, commande, principal=False, petit=False):
    return tk.Button(
        parent, text=texte, command=commande, relief="flat", borderwidth=0,
        cursor="hand2",
        bg=ACCENT if principal else FOND_CHAMP,
        fg="white" if principal else TEXTE,
        activebackground="#3f8ae8" if principal else FOND_SURVOL,
        activeforeground="white" if principal else TEXTE,
        padx=10 if petit else 18, pady=2 if petit else 6,
        font=(POLICE, 9 if petit else 10, "bold" if principal else "normal"),
    )


def _liste(parent, hauteur=6):
    return tk.Listbox(
        parent, bg=FOND_CHAMP, fg=TEXTE, relief="flat", borderwidth=0,
        height=hauteur, font=(POLICE, 10), selectbackground=ACCENT,
        selectforeground="white", highlightthickness=1,
        highlightbackground="#3a3d43", activestyle="none",
    )


def _champ(parent, largeur=22):
    return tk.Entry(
        parent, bg=FOND_CHAMP, fg=TEXTE, relief="flat", width=largeur,
        insertbackground=TEXTE, font=(POLICE, 10), highlightthickness=1,
        highlightbackground="#3a3d43", highlightcolor=ACCENT,
    )


def _titre(parent, texte):
    return tk.Label(parent, text=texte, bg=FOND, fg=TEXTE, anchor="w",
                    font=(POLICE, 10, "bold"))


def _note(parent, texte, **kw):
    return tk.Label(parent, text=texte, bg=FOND, fg=TEXTE_DOUX, anchor="w",
                    justify="left", font=(POLICE, 9), **kw)


class Fenetre:
    """Coller, corriger, apprendre, regler."""

    def __init__(self, app):
        self.app = app
        self.config = dict(app.config)
        self.racine = tk.Tk()
        self.racine.title("Correcteur")
        self.racine.geometry("680x520")
        self.racine.minsize(520, 420)
        self.racine.configure(bg=FOND)

        self.pages: dict[str, tk.Frame] = {}
        self.onglets: dict[str, tk.Button] = {}

        self._construire()
        self._afficher("Corriger")

        threading.Thread(target=self._precharger, daemon=True).start()

    # -- ossature -----------------------------------------------------------

    def _construire(self) -> None:
        barre = tk.Frame(self.racine, bg=FOND, padx=14, pady=10)
        barre.pack(fill="x")

        contenu = tk.Frame(self.racine, bg=FOND, padx=14, pady=0)
        contenu.pack(fill="both", expand=True)

        for nom, constructeur in (
            ("Corriger", self._page_corriger),
            ("Mon dictionnaire", self._page_dictionnaire),
            ("Réglages", self._page_reglages),
        ):
            bouton = _bouton(barre, nom, lambda n=nom: self._afficher(n))
            bouton.pack(side="left", padx=(0, 6))
            self.onglets[nom] = bouton

            page = tk.Frame(contenu, bg=FOND, pady=4)
            constructeur(page)
            self.pages[nom] = page

        self.etat = _note(self.racine, "", wraplength=640)
        self.etat.pack(fill="x", padx=14, pady=(4, 12))

        self.racine.bind("<Escape>", lambda _: self.racine.destroy())

    def _afficher(self, nom: str) -> None:
        for autre, page in self.pages.items():
            page.pack_forget()
            self.onglets[autre].configure(
                bg=FOND_CHAMP, fg=TEXTE, font=(POLICE, 10)
            )
        self.pages[nom].pack(fill="both", expand=True)
        self.onglets[nom].configure(bg=ACCENT, fg="white",
                                    font=(POLICE, 10, "bold"))
        if nom == "Mon dictionnaire":
            self._rafraichir_dictionnaire()

    def _dire(self, message: str) -> None:
        self.etat.configure(text=message)

    def _precharger(self) -> None:
        try:
            self.app.correcteur  # noqa: B018
        except Exception:
            pass

    # -- page « Corriger » --------------------------------------------------

    def _page_corriger(self, page: tk.Frame) -> None:
        _note(page, "Écrivez ou collez votre texte, puis Ctrl+Entrée."
              ).pack(fill="x", pady=(0, 8))

        self.champ = tk.Text(
            page, wrap="word", bg=FOND_CHAMP, fg=TEXTE, insertbackground=TEXTE,
            relief="flat", padx=12, pady=10, font=(POLICE, 11), undo=True,
            highlightthickness=1, highlightbackground="#3a3d43",
        )
        self.champ.pack(fill="both", expand=True)
        self.champ.focus_set()

        barre = tk.Frame(page, bg=FOND, pady=10)
        barre.pack(fill="x")

        self.bouton_corriger = _bouton(barre, "Corriger", self.corriger,
                                       principal=True)
        self.bouton_corriger.pack(side="left")
        _bouton(barre, "Copier", self.copier).pack(side="left", padx=(8, 0))

        # Les mots que le dictionnaire ne connait pas s'affichent ici, chacun
        # avec son bouton : un clic et ils n'y reviendront plus.
        self.inconnus = tk.Frame(page, bg=FOND)
        self.inconnus.pack(fill="x")

        self.racine.bind("<Control-Return>", lambda _: self.corriger())

    def corriger(self) -> None:
        texte = self.champ.get("1.0", "end-1c")
        if not texte.strip():
            return

        self.bouton_corriger.configure(text="…", state="disabled")
        self._dire("Correction en cours…")

        def travailler():
            try:
                resultat = self.app.corriger_texte(texte)
            except LexiqueIntrouvable as e:
                self.racine.after(0, self._echouer, str(e))
            except Exception as e:
                self.racine.after(0, self._echouer, f"La correction a échoué : {e}")
            else:
                self.racine.after(0, self._afficher_resultat, *resultat)

        threading.Thread(target=travailler, daemon=True).start()

    def _afficher_resultat(self, corrige: str, corrections: list) -> None:
        self.bouton_corriger.configure(text="Corriger", state="normal")
        self.champ.delete("1.0", "end")
        self.champ.insert("1.0", corrige)

        if corrections:
            detail = " · ".join(str(c) for c in corrections[:6])
            if len(corrections) > 6:
                detail += f" · (+{len(corrections) - 6})"
            pluriel = "s" if len(corrections) > 1 else ""
            self._dire(f"{len(corrections)} correction{pluriel} : {detail}")
        else:
            self._dire("Aucune faute trouvée.")

        self._proposer_inconnus(corrige)

    def _proposer_inconnus(self, texte: str) -> None:
        for enfant in self.inconnus.winfo_children():
            enfant.destroy()

        try:
            mots = self._mots_inconnus(texte)
        except Exception:
            return
        if not mots:
            return

        _note(self.inconnus, "Mots inconnus — cliquez pour les garder tels quels :"
              ).pack(fill="x", pady=(2, 4))
        ligne = tk.Frame(self.inconnus, bg=FOND)
        ligne.pack(fill="x")
        for mot in mots[:10]:
            _bouton(ligne, f"+ {mot}", lambda m=mot: self._apprendre_mot(m),
                    petit=True).pack(side="left", padx=(0, 6), pady=2)

    def _mots_inconnus(self, texte: str) -> list[str]:
        """Les mots que ni le dictionnaire ni vos listes ne connaissent."""
        from . import grammaire

        correcteur = self.app.correcteur
        vus, inconnus = set(), []
        for jeton in grammaire.decouper(texte):
            mot = jeton.texte
            cle = mot.lower()
            if cle in vus or len(mot) < 2 or any(c.isdigit() for c in mot):
                continue
            vus.add(cle)
            if correcteur._connu(mot) or correcteur._protege(mot):
                continue
            if _normaliser_mot(mot) in {_normaliser_mot(m)
                                        for m in self.config.get("mots_perso", [])}:
                continue
            inconnus.append(mot)
        return inconnus

    def _apprendre_mot(self, mot: str) -> None:
        mots = list(self.config.get("mots_perso", []))
        if mot not in mots:
            mots.append(mot)
        self.config["mots_perso"] = mots
        self._enregistrer(f"« {mot} » ne sera plus corrigé.")
        self._proposer_inconnus(self.champ.get("1.0", "end-1c"))

    def copier(self) -> None:
        self.racine.clipboard_clear()
        self.racine.clipboard_append(self.champ.get("1.0", "end-1c"))
        self._dire("Texte copié dans le presse-papiers.")

    def _echouer(self, message: str) -> None:
        self.bouton_corriger.configure(text="Corriger", state="normal")
        self._dire(message.split("\n")[0])

    # -- page « Mon dictionnaire » ------------------------------------------

    def _page_dictionnaire(self, page: tk.Frame) -> None:
        gauche = tk.Frame(page, bg=FOND)
        gauche.pack(side="left", fill="both", expand=True, padx=(0, 8))
        droite = tk.Frame(page, bg=FOND)
        droite.pack(side="left", fill="both", expand=True, padx=(8, 0))

        # -- mots a ne jamais corriger
        _titre(gauche, "Mots à ne pas corriger").pack(fill="x")
        _note(gauche, "Pseudos, jargon, noms de jeux.").pack(fill="x", pady=(0, 6))

        self.liste_mots = _liste(gauche, hauteur=9)
        self.liste_mots.pack(fill="both", expand=True)

        saisie = tk.Frame(gauche, bg=FOND, pady=6)
        saisie.pack(fill="x")
        self.saisie_mot = _champ(saisie, largeur=16)
        self.saisie_mot.pack(side="left", fill="x", expand=True, ipady=4)
        self.saisie_mot.bind("<Return>", lambda _: self._ajouter_mot())
        _bouton(saisie, "Ajouter", self._ajouter_mot, petit=True).pack(
            side="left", padx=(6, 0))
        _bouton(saisie, "Retirer", self._retirer_mot, petit=True).pack(
            side="left", padx=(6, 0))

        self.retablis = tk.Frame(gauche, bg=FOND)
        self.retablis.pack(fill="x")

        # -- remplacements maison
        _titre(droite, "Mes remplacements").pack(fill="x")
        _note(droite, "« ptetre » → « peut-être ». Passent avant tout le reste, "
                      "et servent aussi d'abréviations."
              ).pack(fill="x", pady=(0, 6))

        self.liste_remplacements = _liste(droite, hauteur=9)
        self.liste_remplacements.pack(fill="both", expand=True)

        saisie = tk.Frame(droite, bg=FOND, pady=6)
        saisie.pack(fill="x")
        self.saisie_de = _champ(saisie, largeur=10)
        self.saisie_de.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Label(saisie, text="→", bg=FOND, fg=TEXTE_DOUX).pack(side="left", padx=4)
        self.saisie_vers = _champ(saisie, largeur=10)
        self.saisie_vers.pack(side="left", fill="x", expand=True, ipady=4)
        self.saisie_vers.bind("<Return>", lambda _: self._ajouter_remplacement())

        boutons = tk.Frame(droite, bg=FOND)
        boutons.pack(fill="x")
        _bouton(boutons, "Ajouter", self._ajouter_remplacement, petit=True).pack(
            side="left")
        _bouton(boutons, "Retirer", self._retirer_remplacement, petit=True).pack(
            side="left", padx=(6, 0))

    def _rafraichir_dictionnaire(self) -> None:
        self.liste_mots.delete(0, "end")
        for mot in sorted(self.config.get("mots_perso", []), key=str.lower):
            self.liste_mots.insert("end", mot)

        self.liste_remplacements.delete(0, "end")
        for de, vers in sorted(self.config.get("remplacements_perso", {}).items()):
            self.liste_remplacements.insert("end", f"{de}  →  {vers}")

        for enfant in self.retablis.winfo_children():
            enfant.destroy()
        connus = {m.lower() for m in self.config.get("mots_perso", [])}
        propositions = [m for m in getattr(self.app, "mots_retablis", [])
                        if m.lower() not in connus]
        if not propositions:
            return
        _note(self.retablis, "Vous avez rétabli ces mots à la main :"
              ).pack(fill="x", pady=(6, 4))
        ligne = tk.Frame(self.retablis, bg=FOND)
        ligne.pack(fill="x")
        for mot in propositions[-8:]:
            _bouton(ligne, f"+ {mot}", lambda m=mot: self._ajouter_mot(m),
                    petit=True).pack(side="left", padx=(0, 6), pady=2)

    def _ajouter_mot(self, mot: str | None = None) -> None:
        mot = (mot if mot is not None else self.saisie_mot.get()).strip()
        if not mot:
            return
        mots = list(self.config.get("mots_perso", []))
        if mot in mots:
            self._dire(f"« {mot} » y est déjà.")
            return
        mots.append(mot)
        self.config["mots_perso"] = mots
        self.saisie_mot.delete(0, "end")
        self._enregistrer(f"« {mot} » ne sera plus corrigé.")
        self._rafraichir_dictionnaire()

    def _retirer_mot(self) -> None:
        selection = self.liste_mots.curselection()
        if not selection:
            self._dire("Choisissez d'abord un mot dans la liste.")
            return
        mot = self.liste_mots.get(selection[0])
        self.config["mots_perso"] = [
            m for m in self.config.get("mots_perso", []) if m != mot
        ]
        self._enregistrer(f"« {mot} » retiré de votre dictionnaire.")
        self._rafraichir_dictionnaire()

    def _ajouter_remplacement(self) -> None:
        de = self.saisie_de.get().strip()
        vers = self.saisie_vers.get().strip()
        if not de or not vers:
            self._dire("Il faut un mot à remplacer et son remplacement.")
            return
        if de.lower() == vers.lower():
            self._dire("Les deux sont identiques.")
            return
        remplacements = dict(self.config.get("remplacements_perso", {}))
        remplacements[de] = vers
        self.config["remplacements_perso"] = remplacements
        self.saisie_de.delete(0, "end")
        self.saisie_vers.delete(0, "end")
        self._enregistrer(f"« {de} » deviendra « {vers} ».")
        self._rafraichir_dictionnaire()

    def _retirer_remplacement(self) -> None:
        selection = self.liste_remplacements.curselection()
        if not selection:
            self._dire("Choisissez d'abord une ligne dans la liste.")
            return
        de = self.liste_remplacements.get(selection[0]).split("  →  ")[0]
        remplacements = dict(self.config.get("remplacements_perso", {}))
        remplacements.pop(de, None)
        self.config["remplacements_perso"] = remplacements
        self._enregistrer(f"« {de} » retiré.")
        self._rafraichir_dictionnaire()

    # -- page « Réglages » --------------------------------------------------

    def _page_reglages(self, page: tk.Frame) -> None:
        self.cases: dict[str, tk.BooleanVar] = {}

        def case(parent, cle, libelle, explication, valeur):
            variable = tk.BooleanVar(value=bool(valeur))
            self.cases[cle] = variable
            tk.Checkbutton(
                parent, text=libelle, variable=variable, bg=FOND, fg=TEXTE,
                selectcolor=FOND_CHAMP, activebackground=FOND,
                activeforeground=TEXTE, anchor="w", font=(POLICE, 10),
                highlightthickness=0, borderwidth=0, cursor="hand2",
            ).pack(fill="x", pady=(6, 0))
            _note(parent, "    " + explication).pack(fill="x")

        regles_actives = self.config.get("regles_optionnelles", {})

        case(page, "correction_auto", "Corriger pendant que j'écris",
             "Le texte se corrige tout seul, sans raccourci. "
             f"{self.config.get('raccourci_annuler', 'ctrl+alt+z')} annule la dernière correction.",
             self.config.get("correction_auto", True))
        case(page, "collage_auto", "Recoller le texte corrigé automatiquement",
             "Sinon le texte corrigé est seulement mis dans le presse-papiers.",
             self.config.get("collage_auto", True))
        case(page, "notifications", "Afficher les notifications",
             "Le résumé des corrections près de l'horloge.",
             self.config.get("notifications", True))
        case(page, "MAJUSCULE_PHRASE", "Mettre une majuscule en début de phrase",
             "Désactivé d'origine : beaucoup de gens tiennent au tout-minuscules.",
             regles_actives.get("MAJUSCULE_PHRASE", False))
        case(page, "PONCTUATION_POINT", "Ajouter le point final manquant",
             "Désactivé d'origine, pour la même raison.",
             regles_actives.get("PONCTUATION_POINT", False))

        raccourcis = tk.Frame(page, bg=FOND, pady=10)
        raccourcis.pack(fill="x")

        tk.Label(raccourcis, text="Raccourci :", bg=FOND, fg=TEXTE,
                 font=(POLICE, 10)).pack(side="left")
        self.saisie_raccourci = _champ(raccourcis, largeur=14)
        self.saisie_raccourci.insert(0, self.config.get("raccourci", "ctrl+alt+c"))
        self.saisie_raccourci.pack(side="left", padx=(6, 16), ipady=4)

        tk.Label(raccourcis, text="Annuler :", bg=FOND, fg=TEXTE,
                 font=(POLICE, 10)).pack(side="left")
        self.saisie_annuler = _champ(raccourcis, largeur=14)
        self.saisie_annuler.insert(0, self.config.get("raccourci_annuler", "ctrl+alt+z"))
        self.saisie_annuler.pack(side="left", padx=(6, 0), ipady=4)

        _note(page, "Exemples : ctrl+alt+c, ctrl+shift+f, f9.").pack(fill="x")

        if demarrage.disponible():
            self.case_demarrage = tk.BooleanVar(value=demarrage.actif())
            tk.Checkbutton(
                page, text="Lancer au démarrage de Windows",
                variable=self.case_demarrage, command=self._basculer_demarrage,
                bg=FOND, fg=TEXTE, selectcolor=FOND_CHAMP, activebackground=FOND,
                activeforeground=TEXTE, anchor="w", font=(POLICE, 10),
                highlightthickness=0, borderwidth=0, cursor="hand2",
            ).pack(fill="x", pady=(10, 0))

        barre = tk.Frame(page, bg=FOND, pady=12)
        barre.pack(fill="x")
        _bouton(barre, "Enregistrer", self._enregistrer_reglages,
                principal=True).pack(side="left")
        _note(page, f"Fichier de réglages : {config_mod.chemin_config()}"
              ).pack(fill="x")

    def _basculer_demarrage(self) -> None:
        try:
            actif = demarrage.basculer()
        except OSError as e:
            self._dire(f"Impossible de modifier le démarrage automatique : {e}")
            return
        self.case_demarrage.set(actif)
        self._dire("Le correcteur se lancera avec Windows." if actif
                   else "Le correcteur ne se lancera plus avec Windows.")

    def _enregistrer_reglages(self) -> None:
        for cle in ("correction_auto", "collage_auto", "notifications"):
            self.config[cle] = self.cases[cle].get()
        self.config["regles_optionnelles"] = {
            nom: self.cases[nom].get() for nom in regles.REGLES_OPTIONNELLES
        }

        raccourci = self.saisie_raccourci.get().strip().lower()
        annuler = self.saisie_annuler.get().strip().lower()
        if not raccourci or not annuler:
            self._dire("Un raccourci ne peut pas être vide.")
            return
        if raccourci == annuler:
            self._dire("Les deux raccourcis doivent être différents.")
            return
        self.config["raccourci"] = raccourci
        self.config["raccourci_annuler"] = annuler

        self._enregistrer("Réglages enregistrés.")

    # -- enregistrement -----------------------------------------------------

    def _enregistrer(self, message: str) -> None:
        """Ecrit les reglages et previent l'application qui tourne."""
        try:
            config_mod.sauvegarder(self.config)
        except OSError as e:
            self._dire(f"Impossible d'enregistrer : {e}")
            return
        try:
            self.app.recharger(dict(self.config))
        except Exception:
            # L'icone de la barre des taches relira le fichier de son cote ;
            # ne pas pouvoir recharger ici n'est pas une raison d'alerter.
            pass
        self._dire(message)

    # -- boucle -------------------------------------------------------------

    def lancer(self) -> None:
        self.racine.mainloop()
