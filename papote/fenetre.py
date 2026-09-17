# -*- coding: utf-8 -*-
"""La fenetre : corriger, apprendre, regler.

Papote travaille normalement sans se montrer — il corrige pendant qu'on
ecrit. Cette fenetre sert aux quatre choses qu'il ne peut pas faire tout
seul : relire un texte, lui apprendre un mot, voir ce qu'on rate le plus, et
regler ce qu'il fait.

La mise en page suit ce que font les applications d'aujourd'hui : une colonne
de navigation a gauche, le contenu a droite, des panneaux poses sur un fond
sombre. Les couleurs, les espacements et les widgets dessines vivent dans
`theme.py` ; les icones, en pixel art, dans `icones.py`.
"""

from __future__ import annotations

import re
import threading
import tkinter as tk

from . import __version__, config as config_mod
from . import demarrage, icones, journal as journal_mod, maj
from . import politique as politique_mod, regles
from . import relecture, theme
from .lexique import LexiqueIntrouvable
from .moteur import _normaliser_mot
from .raccourci import MODIFICATEURS, nom_de_touche

# Les pages, dans l'ordre de la colonne de gauche.
PAGES = (
    ("Corriger", "crayon", "Collez un texte, relisez-le avant de l'envoyer."),
    ("Mon dictionnaire", "livre", "Les mots et les tournures qui vous appartiennent."),
    ("Vos fautes", "barres", "Ce que vous corrigez le plus, compté chez vous."),
    ("Applications", "fenetre", "Où se taire, et où hausser le ton."),
    ("Réglages", "reglages", "Tout ce qui se réglait dans un fichier."),
)


class ChampRaccourci:
    """Un bouton qui attend qu'on appuie sur la combinaison voulue.

    Saisir « ctrl+alt+c » a la main suppose de connaitre l'orthographe exacte
    attendue par la bibliotheque de raccourcis. Appuyer sur les touches, non.
    """

    INVITE = "Appuyez…"

    def __init__(self, parent, valeur: str, sur_erreur=None):
        self.valeur = valeur or ""
        self.sur_erreur = sur_erreur or (lambda _message: None)
        self.enfonces: list[str] = []
        self.capture = False

        self.bouton = theme.Bouton(parent, self._libelle(), self._capturer,
                                   petit=True, fond=theme.SURFACE)

    def _libelle(self) -> str:
        return self.valeur.upper() if self.valeur else "aucun"

    def pack(self, **options):
        self.bouton.pack(**options)
        return self

    def get(self) -> str:
        return self.valeur

    def _capturer(self) -> None:
        if self.capture:
            return
        self.capture = True
        self.enfonces = []
        self.bouton.configurer(texte=self.INVITE)
        self.bouton.canevas.focus_set()
        self.bouton.canevas.grab_set()
        self.bouton.canevas.bind("<KeyPress>", self._enfoncee)
        self.bouton.canevas.bind("<KeyRelease>", self._relachee)

    def _terminer(self) -> None:
        self.capture = False
        self.bouton.canevas.grab_release()
        self.bouton.canevas.unbind("<KeyPress>")
        self.bouton.canevas.unbind("<KeyRelease>")
        self.bouton.configurer(texte=self._libelle())

    def _enfoncee(self, evenement):
        touche = nom_de_touche(evenement.keysym)

        if evenement.keysym == "Escape":
            self._terminer()
            return "break"
        if evenement.keysym in ("BackSpace", "Delete"):
            self.valeur = ""
            self._terminer()
            return "break"
        if touche is None:
            return "break"

        if touche in MODIFICATEURS:
            if touche not in self.enfonces:
                self.enfonces.append(touche)
            self.bouton.configurer(texte=("+".join(self.enfonces) + "+…").upper())
            return "break"

        # Une touche seule ferait un raccourci global insupportable : elle
        # partirait a chaque fois qu'on l'ecrit. Les touches de fonction, si.
        touche_de_fonction = touche.startswith("f") and touche[1:].isdigit()
        if not self.enfonces and not touche_de_fonction:
            self.sur_erreur("Ajoutez Ctrl, Alt ou Maj — sans quoi le raccourci "
                            "partirait chaque fois que vous tapez cette touche.")
            self.bouton.configurer(texte=self.INVITE)
            return "break"

        self.valeur = "+".join(self.enfonces + [touche])
        self._terminer()
        return "break"

    def _relachee(self, evenement):
        touche = nom_de_touche(evenement.keysym)
        if touche in self.enfonces:
            self.enfonces.remove(touche)
        return "break"


class Fenetre:
    """Corriger, apprendre, regler."""

    LARGEUR_COLONNE = 208

    def __init__(self, app):
        self.app = app
        self.config = dict(app.config)
        self.images: list = []          # les PhotoImage se perdent sans reference
        self.pages: dict[str, tk.Frame] = {}
        self.entrees: dict[str, theme.EntreeNavigation] = {}
        self.maj_trouvee: maj.Version | None = None

        self.racine = tk.Tk()
        self.racine.title("Papote")
        self.racine.geometry("940x660")
        # Tout defile : la fenetre peut donc devenir petite sans rien cacher.
        self.racine.minsize(540, 420)
        self.racine.configure(bg=theme.FOND)

        self._construire()
        self._afficher("Corriger")

        # Une mise a jour peut avoir ete telechargee en arriere-plan avant
        # meme que la fenetre ne s'ouvre : elle doit se proposer tout de
        # suite, sans qu'il faille aller la chercher dans les reglages.
        self._annoncer_si_prete()

        threading.Thread(target=self._precharger, daemon=True).start()

    # -- ossature -----------------------------------------------------------

    def _construire(self) -> None:
        colonne = tk.Frame(self.racine, bg=theme.FOND,
                           width=self.LARGEUR_COLONNE)
        colonne.pack(side="left", fill="y")
        colonne.pack_propagate(False)
        self._colonne(colonne)

        droite = tk.Frame(self.racine, bg=theme.FOND)
        droite.pack(side="left", fill="both", expand=True)

        self.entete = tk.Frame(droite, bg=theme.FOND, padx=theme.TRES_GRAND,
                               pady=theme.GRAND)
        self.entete.pack(fill="x")
        self.titre_page = tk.Label(self.entete, text="", bg=theme.FOND,
                                   fg=theme.TEXTE, anchor="w",
                                   font=theme.police(15, gras=True))
        self.titre_page.pack(fill="x")
        self.sous_titre = theme.note(self.entete, "", fond=theme.FOND)
        self.sous_titre.pack(fill="x", pady=(2, 0))

        contenu = tk.Frame(droite, bg=theme.FOND, padx=theme.TRES_GRAND)
        contenu.pack(fill="both", expand=True)

        for nom, _icone, _sous_titre in PAGES:
            construire = getattr(self, "_page_" + _cle(nom))
            if nom == "Corriger":
                # La zone de texte occupe toute la hauteur : la faire defiler
                # reviendrait a lui donner la taille de son contenu.
                page = tk.Frame(contenu, bg=theme.FOND)
                construire(page)
                self.pages[nom] = page
            else:
                zone = theme.Defilement(contenu)
                construire(zone.interieur)
                self.pages[nom] = zone.exterieur

        barre = tk.Frame(droite, bg=theme.FOND, padx=theme.TRES_GRAND,
                         pady=theme.MOYEN)
        barre.pack(fill="x")
        self.etat = theme.note(barre, "", fond=theme.FOND)
        self.etat.pack(fill="x")

        self.racine.bind("<Escape>", lambda _: self.racine.destroy())

    def _colonne(self, colonne: tk.Frame) -> None:
        marque = tk.Frame(colonne, bg=theme.FOND, padx=14, pady=18)
        marque.pack(fill="x")

        image = icones.image_tk(
            "papote", icones.palette(theme.ACCENT, theme.FOND,
                                     lumiere=theme.ACCENT_VIF),
            theme.FOND, 2,
        )
        self.images.append(image)
        tk.Label(marque, image=image, bg=theme.FOND, bd=0).pack(side="left")

        titres = tk.Frame(marque, bg=theme.FOND)
        titres.pack(side="left", padx=(10, 0))
        tk.Label(titres, text="Papote", bg=theme.FOND, fg=theme.TEXTE,
                 font=theme.police(13, gras=True), anchor="w").pack(fill="x")
        tk.Label(titres, text=__version__, bg=theme.FOND, fg=theme.TEXTE_ETEINT,
                 font=theme.police(8), anchor="w").pack(fill="x")

        for nom, icone, _sous_titre in PAGES:
            self.entrees[nom] = theme.EntreeNavigation(
                colonne, nom, icone, self._afficher
            ).pack(fill="x", padx=8, pady=1)

        # Le bas de la colonne annonce une mise a jour prete, et rien d'autre.
        self.bandeau_maj = tk.Frame(colonne, bg=theme.FOND, padx=12, pady=12)
        self.bandeau_maj.pack(side="bottom", fill="x")

    def _afficher(self, nom: str) -> None:
        for autre, page in self.pages.items():
            page.pack_forget()
            self.entrees[autre].choisir(False)
        self.pages[nom].pack(fill="both", expand=True)
        self.entrees[nom].choisir(True)

        self.titre_page.configure(text=nom)
        self.sous_titre.configure(
            text=next(s for n, _i, s in PAGES if n == nom))

        if nom == "Mon dictionnaire":
            self._rafraichir_dictionnaire()
        elif nom == "Vos fautes":
            self._rafraichir_fautes()
        elif nom == "Applications":
            self._rafraichir_applications()

    def _dire(self, message: str, couleur: str | None = None) -> None:
        self.etat.configure(text=message, fg=couleur or theme.TEXTE_DOUX)

    def _precharger(self) -> None:
        try:
            self.app.correcteur  # noqa: B018
        except Exception:
            pass

    # -- page « Corriger » --------------------------------------------------

    def _page_corriger(self, page: tk.Frame) -> None:
        cadre = theme.carte(page)
        cadre.pack(fill="both", expand=True)

        self.champ = theme.texte(cadre, fond=theme.SURFACE)
        self.champ.pack(fill="both", expand=True, padx=2, pady=2)
        self.champ.focus_set()

        barre = tk.Frame(page, bg=theme.FOND, pady=theme.MOYEN)
        barre.pack(fill="x")

        self.bouton_corriger = theme.Bouton(
            barre, "Corriger", self.corriger, principal=True, icone="coche"
        ).pack(side="left")
        theme.Bouton(barre, "Copier", self.copier).pack(side="left",
                                                        padx=(theme.MOYEN, 0))
        theme.note(barre, "Ctrl+Entrée", fond=theme.FOND).pack(
            side="left", padx=(theme.MOYEN, 0))

        # Les mots que le dictionnaire ne connait pas s'affichent ici, chacun
        # avec son bouton : un clic et ils n'y reviendront plus.
        self.inconnus = tk.Frame(page, bg=theme.FOND)
        self.inconnus.pack(fill="x")

        self.racine.bind("<Control-Return>", lambda _: self.corriger())

    def corriger(self) -> None:
        texte = self.champ.get("1.0", "end-1c")
        if not texte.strip():
            return

        self.bouton_corriger.configurer(texte="…", actif=False)
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
        self.bouton_corriger.configurer(texte="Corriger", actif=True)
        self.champ.delete("1.0", "end")
        self.champ.insert("1.0", corrige)

        if corrections:
            detail = " · ".join(str(c) for c in corrections[:6])
            if len(corrections) > 6:
                detail += f" · (+{len(corrections) - 6})"
            pluriel = "s" if len(corrections) > 1 else ""
            self._dire(f"{len(corrections)} correction{pluriel} : {detail}",
                       theme.SUCCES)
        else:
            self._dire("Aucune faute trouvée.", theme.SUCCES)

        self._proposer_inconnus(corrige)

    def _proposer_inconnus(self, texte: str) -> None:
        """Une ligne par mot inconnu : ce qu'on aurait mis a la place, et
        le bouton pour dire qu'il n'y avait rien a mettre.

        Le correcteur ne remplace que ce dont il est sur — « ourné » vaut
        « journée » autant que « durée », alors il n'y touche pas. Plutot que
        de laisser la faute sans rien dire, on montre ici ce qu'il a trouve.
        """
        for enfant in self.inconnus.winfo_children():
            enfant.destroy()
        try:
            mots = self._mots_inconnus(texte)
        except Exception:
            return
        if not mots:
            return

        theme.note(self.inconnus,
                   "Mots inconnus — cliquez le bon, ou gardez le vôtre :",
                   fond=theme.FOND).pack(fill="x", pady=(2, 6))

        for mot in mots[:10]:
            ligne = tk.Frame(self.inconnus, bg=theme.FOND)
            ligne.pack(fill="x", pady=1)
            theme.note(ligne, f"{mot} →", fond=theme.FOND).pack(
                side="left", padx=(0, 6))
            for remplacement in self._propositions(mot):
                theme.Bouton(
                    ligne, remplacement,
                    lambda m=mot, r=remplacement: self._remplacer_mot(m, r),
                    petit=True, fond=theme.FOND,
                ).pack(side="left", padx=(0, 4), pady=1)
            theme.Bouton(ligne, f"garder « {mot} »",
                         lambda m=mot: self._apprendre_mot(m),
                         petit=True, fond=theme.FOND).pack(side="left",
                                                           padx=(4, 0), pady=1)

    def _propositions(self, mot: str) -> list[str]:
        """Ce que le correcteur aurait propose, sans en etre assez sur."""
        try:
            return self.app.correcteur.propositions(mot, maximum=3)
        except Exception:
            return []

    def _remplacer_mot(self, mot: str, remplacement: str) -> None:
        """Remplace le mot partout dans le texte, mot entier seulement."""
        texte = self.champ.get("1.0", "end-1c")
        motif = re.compile(rf"(?<!\w){re.escape(mot)}(?!\w)")
        nouveau, nombre = motif.subn(remplacement.replace("\\", "\\\\"), texte)
        if not nombre:
            return
        self.champ.delete("1.0", "end")
        self.champ.insert("1.0", nouveau)
        self._dire(f"« {mot} » remplacé par « {remplacement} ».", theme.SUCCES)
        self._proposer_inconnus(nouveau)

    def _mots_inconnus(self, texte: str) -> list[str]:
        """Les mots que ni le dictionnaire ni vos listes ne connaissent."""
        from . import grammaire

        correcteur = self.app.correcteur
        connus = {_normaliser_mot(m) for m in self.config.get("mots_perso", [])}
        vus, inconnus = set(), []
        for jeton in grammaire.decouper(texte):
            mot = jeton.texte
            cle = mot.lower()
            if cle in vus or len(mot) < 2 or any(c.isdigit() for c in mot):
                continue
            vus.add(cle)
            if correcteur._connu(mot) or correcteur._protege(mot):
                continue
            if _normaliser_mot(mot) in connus:
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
        self._dire("Texte copié dans le presse-papiers.", theme.SUCCES)

    def _echouer(self, message: str) -> None:
        self.bouton_corriger.configurer(texte="Corriger", actif=True)
        self._dire(message.split("\n")[0], theme.ALERTE)

    # -- page « Mon dictionnaire » ------------------------------------------

    def _page_mon_dictionnaire(self, page: tk.Frame) -> None:
        colonnes = theme.Colonnes(page).pack(fill="both", expand=True)
        gauche, droite = self._carte(colonnes.ajouter()), \
            self._carte(colonnes.ajouter())

        dedans = gauche
        theme.titre(dedans, "Mots à ne pas corriger").pack(fill="x")
        theme.note(dedans, "Pseudos, jargon, noms de jeux.").pack(
            fill="x", pady=(2, theme.MOYEN))

        self.liste_mots = theme.liste(dedans, hauteur=9)
        self.liste_mots.pack(fill="both", expand=True)

        saisie = tk.Frame(dedans, bg=theme.SURFACE, pady=theme.MOYEN)
        saisie.pack(fill="x")
        self.saisie_mot = theme.entree(saisie, largeur=14)
        self.saisie_mot.pack(side="left", fill="x", expand=True, ipady=5)
        self.saisie_mot.bind("<Return>", lambda _: self._ajouter_mot())
        theme.Bouton(saisie, "Ajouter", self._ajouter_mot, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))
        theme.Bouton(saisie, "Retirer", self._retirer_mot, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))

        self.retablis = tk.Frame(dedans, bg=theme.SURFACE)
        self.retablis.pack(fill="x")

        dedans = droite
        theme.titre(dedans, "Mes remplacements").pack(fill="x")
        theme.note(dedans, "« ptetre » → « peut-être ». Ils passent avant tout "
                           "le reste, et servent aussi d'abréviations.").pack(fill="x", pady=(2, theme.MOYEN))

        self.liste_remplacements = theme.liste(dedans, hauteur=9)
        self.liste_remplacements.pack(fill="both", expand=True)

        saisie = tk.Frame(dedans, bg=theme.SURFACE, pady=theme.MOYEN)
        saisie.pack(fill="x")
        self.saisie_de = theme.entree(saisie, largeur=8)
        self.saisie_de.pack(side="left", fill="x", expand=True, ipady=5)
        tk.Label(saisie, text="→", bg=theme.SURFACE, fg=theme.TEXTE_DOUX,
                 font=theme.police(11)).pack(side="left", padx=6)
        self.saisie_vers = theme.entree(saisie, largeur=8)
        self.saisie_vers.pack(side="left", fill="x", expand=True, ipady=5)
        self.saisie_vers.bind("<Return>", lambda _: self._ajouter_remplacement())

        boutons = tk.Frame(dedans, bg=theme.SURFACE)
        boutons.pack(fill="x")
        theme.Bouton(boutons, "Ajouter", self._ajouter_remplacement, petit=True,
                     fond=theme.SURFACE).pack(side="left")
        theme.Bouton(boutons, "Retirer", self._retirer_remplacement, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))

    def _rafraichir_dictionnaire(self) -> None:
        self.liste_mots.delete(0, "end")
        for mot in sorted(self.config.get("mots_perso", []), key=str.lower):
            self.liste_mots.insert("end", f"  {mot}")

        self.liste_remplacements.delete(0, "end")
        for de, vers in sorted(self.config.get("remplacements_perso", {}).items()):
            self.liste_remplacements.insert("end", f"  {de}  →  {vers}")

        for enfant in self.retablis.winfo_children():
            enfant.destroy()
        connus = {m.lower() for m in self.config.get("mots_perso", [])}
        propositions = [m for m in getattr(self.app, "mots_retablis", [])
                        if m.lower() not in connus]
        if not propositions:
            return
        theme.note(self.retablis, "Vous avez rétabli ces mots à la main :").pack(
            fill="x", pady=(theme.MOYEN, theme.PETIT))
        ligne = tk.Frame(self.retablis, bg=theme.SURFACE)
        ligne.pack(fill="x")
        for mot in propositions[-6:]:
            theme.Bouton(ligne, f"+ {mot}", lambda m=mot: self._ajouter_mot(m),
                         petit=True, fond=theme.SURFACE).pack(side="left",
                                                              padx=(0, 6), pady=2)

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
        mot = self._choisi(self.liste_mots, "un mot")
        if mot is None:
            return
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
        ligne = self._choisi(self.liste_remplacements, "une ligne")
        if ligne is None:
            return
        de = ligne.split("  →  ")[0]
        remplacements = dict(self.config.get("remplacements_perso", {}))
        remplacements.pop(de, None)
        self.config["remplacements_perso"] = remplacements
        self._enregistrer(f"« {de} » retiré.")
        self._rafraichir_dictionnaire()

    def _choisi(self, liste: tk.Listbox, quoi: str) -> str | None:
        selection = liste.curselection()
        if not selection:
            self._dire(f"Choisissez d'abord {quoi} dans la liste.")
            return None
        return liste.get(selection[0]).strip()

    # -- page « Vos fautes » ------------------------------------------------

    def _page_vos_fautes(self, page: tk.Frame) -> None:
        dedans = self._carte(page)
        theme.titre(dedans, "Ce que vous corrigez le plus").pack(fill="x")
        theme.note(dedans, "Compté sur votre machine, et nulle part ailleurs.").pack(
            fill="x", pady=(2, theme.MOYEN))

        self.liste_fautes = theme.liste(dedans, hauteur=12)
        self.liste_fautes.pack(fill="both", expand=True)

        barre = tk.Frame(dedans, bg=theme.SURFACE, pady=theme.MOYEN)
        barre.pack(fill="x")
        # « Ne plus corriger ça » se tenait ici. La liste ne montre plus que
        # la forme **corrigee** — « ça », « j'ai » —, et ajouter celle-la au
        # dictionnaire personnel n'aurait aucun sens : c'est deja du
        # francais. Pour ecarter un mot, la page « Corriger » a « garder
        # « mot » », qui sait de quoi elle parle.
        theme.Bouton(barre, "Effacer l'historique", self._effacer_historique,
                     petit=True, fond=theme.SURFACE).pack(side="left")

        self.cadre_regles = tk.Frame(dedans, bg=theme.SURFACE)
        self.cadre_regles.pack(fill="x")

    def _rafraichir_fautes(self) -> None:
        journal = getattr(self.app, "journal_habitudes", None)
        self.liste_fautes.delete(0, "end")

        fautes = journal.fautes_frequentes(30) if journal is not None else []
        if not fautes:
            self.liste_fautes.insert(
                "end", "  Rien encore — Papote vous regarde écrire.")
        for faute, compte in fautes:
            self.liste_fautes.insert("end", f"  {compte:>4} ×   {faute}")

        if journal is not None:
            total = journal.total_corrections()
            self._dire(f"{total} correction{'s' if total > 1 else ''} appliquée"
                       f"{'s' if total > 1 else ''} depuis l'installation.")

        for enfant in self.cadre_regles.winfo_children():
            enfant.destroy()
        contestees = [r for r in getattr(self.app, "regles_contestees", [])
                      if self.config.get("regles_optionnelles", {}).get(r, True)]
        if not contestees:
            return
        theme.note(self.cadre_regles,
                   "Vous annulez souvent ces règles — un clic les éteint :").pack(
            fill="x", pady=(theme.MOYEN, theme.PETIT))
        ligne = tk.Frame(self.cadre_regles, bg=theme.SURFACE)
        ligne.pack(fill="x")
        for nom in dict.fromkeys(contestees):
            theme.Bouton(ligne, f"✕ {nom}", lambda n=nom: self._eteindre_regle(n),
                         petit=True, fond=theme.SURFACE).pack(side="left",
                                                              padx=(0, 6), pady=2)

    def _eteindre_regle(self, nom: str) -> None:
        regles_actives = dict(self.config.get("regles_optionnelles", {}))
        regles_actives[nom] = False
        self.config["regles_optionnelles"] = regles_actives
        if nom in self.bascules:
            self.bascules[nom].set(False)
        self._enregistrer(f"La règle {nom} est éteinte.")
        self._rafraichir_fautes()

    def _effacer_historique(self) -> None:
        journal = getattr(self.app, "journal_habitudes", None)
        if journal is None:
            return
        journal.vider()
        self.app.enregistrer_habitudes()
        self._rafraichir_fautes()
        self._dire("Historique effacé.", theme.SUCCES)

    # -- page « Applications » ----------------------------------------------

    def _page_applications(self, page: tk.Frame) -> None:
        colonnes = theme.Colonnes(page).pack(fill="both", expand=True)
        gauche, droite = self._carte(colonnes.ajouter()), \
            self._carte(colonnes.ajouter())

        dedans = gauche
        theme.titre(dedans, "Ne rien corriger ici").pack(fill="x")
        theme.note(dedans, "Terminaux, éditeurs de code, jeux : la correction "
                           "automatique y fait plus de mal que de bien.").pack(fill="x", pady=(2, theme.MOYEN))

        self.liste_applications = theme.liste(dedans, hauteur=10)
        self.liste_applications.pack(fill="both", expand=True)

        saisie = tk.Frame(dedans, bg=theme.SURFACE, pady=theme.MOYEN)
        saisie.pack(fill="x")
        self.saisie_application = theme.entree(saisie, largeur=14)
        self.saisie_application.pack(side="left", fill="x", expand=True, ipady=5)
        self.saisie_application.bind("<Return>", lambda _: self._exclure())
        theme.Bouton(saisie, "Ajouter", self._exclure, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))
        theme.Bouton(saisie, "Retirer", self._reintegrer, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))
        theme.note(dedans, "Le nom du programme : discord.exe, code.exe…").pack(
            fill="x")

        dedans = droite
        theme.titre(dedans, "Registre par application").pack(fill="x")
        theme.note(dedans, "« soutenu » remet les « ne » de négation et déplie "
                           "les abréviations. Pratique pour Outlook, pas pour "
                           "Discord.").pack(
            fill="x", pady=(2, theme.MOYEN))

        self.liste_registres = theme.liste(dedans, hauteur=10)
        self.liste_registres.pack(fill="both", expand=True)

        saisie = tk.Frame(dedans, bg=theme.SURFACE, pady=theme.MOYEN)
        saisie.pack(fill="x")
        self.saisie_registre_app = theme.entree(saisie, largeur=12)
        self.saisie_registre_app.pack(side="left", fill="x", expand=True, ipady=5)
        theme.Bouton(saisie, "→ soutenu",
                     lambda: self._registre_application(politique_mod.SOUTENU),
                     petit=True, fond=theme.SURFACE).pack(side="left", padx=(6, 0))
        theme.Bouton(saisie, "Retirer", self._retirer_registre_application,
                     petit=True, fond=theme.SURFACE).pack(side="left", padx=(6, 0))

    def _rafraichir_applications(self) -> None:
        self.liste_applications.delete(0, "end")
        for nom in sorted(self.config.get("applications_exclues", []),
                          key=str.lower):
            self.liste_applications.insert("end", f"  {nom}")

        self.liste_registres.delete(0, "end")
        for nom, registre in sorted(
            self.config.get("registre_par_application", {}).items()
        ):
            self.liste_registres.insert("end", f"  {nom}  →  {registre}")

    def _exclure(self) -> None:
        nom = self.saisie_application.get().strip().lower()
        if not nom:
            return
        exclues = list(self.config.get("applications_exclues", []))
        if nom not in exclues:
            exclues.append(nom)
        self.config["applications_exclues"] = exclues
        self.saisie_application.delete(0, "end")
        self._enregistrer(f"Plus de correction automatique dans {nom}.")
        self._rafraichir_applications()

    def _reintegrer(self) -> None:
        nom = self._choisi(self.liste_applications, "une application")
        if nom is None:
            return
        self.config["applications_exclues"] = [
            a for a in self.config.get("applications_exclues", []) if a != nom
        ]
        self._enregistrer(f"Papote corrige de nouveau dans {nom}.")
        self._rafraichir_applications()

    def _registre_application(self, registre: str) -> None:
        nom = self.saisie_registre_app.get().strip().lower()
        if not nom:
            self._dire("Indiquez d'abord le nom du programme.")
            return
        registres = dict(self.config.get("registre_par_application", {}))
        registres[nom] = registre
        self.config["registre_par_application"] = registres
        self.saisie_registre_app.delete(0, "end")
        self._enregistrer(f"{nom} sera corrigé en registre {registre}.")
        self._rafraichir_applications()

    def _retirer_registre_application(self) -> None:
        ligne = self._choisi(self.liste_registres, "une ligne")
        if ligne is None:
            return
        nom = ligne.split("  →  ")[0]
        registres = dict(self.config.get("registre_par_application", {}))
        registres.pop(nom, None)
        self.config["registre_par_application"] = registres
        self._enregistrer(f"{nom} revient au registre par défaut.")
        self._rafraichir_applications()

    # -- page « Réglages » --------------------------------------------------

    def _page_reglages(self, page: tk.Frame) -> None:
        self.bascules: dict[str, theme.Interrupteur] = {}
        regles_actives = self.config.get("regles_optionnelles", {})

        colonne = tk.Frame(page, bg=theme.FOND)
        colonne.pack(fill="both", expand=True)

        comportement = self._section(colonne, "Ce qu'il fait")
        for cle, libelle, explication, valeur in (
            ("correction_auto", "Corriger pendant que j'écris",
             "Sans raccourci, dans n'importe quelle application.",
             self.config.get("correction_auto", True)),
            ("apprentissage", "Apprendre de mes annulations",
             "Une correction annulée trois fois, et il n'y revient plus.",
             self.config.get("apprentissage", True)),
            ("collage_auto", "Recoller le texte corrigé",
             "Sinon il se contente du presse-papiers.",
             self.config.get("collage_auto", True)),
            ("notifications", "Afficher les notifications",
             "Le résumé des corrections près de l'horloge.",
             self.config.get("notifications", True)),
        ):
            self._ligne_bascule(comportement, cle, libelle, explication, valeur)

        style = self._section(colonne, "Comment il écrit")
        for cle, libelle, explication in (
            ("TYPOGRAPHIE", "Typographie française",
             "« … », guillemets « », espaces insécables."),
            ("MAJUSCULE_PHRASE", "Majuscule en début de phrase",
             "Éteint d'origine : beaucoup tiennent au tout-minuscules."),
            ("PONCTUATION_POINT", "Point final manquant",
             "Éteint d'origine, pour la même raison."),
        ):
            self._ligne_bascule(style, cle, libelle, explication,
                                regles_actives.get(cle, False))

        ligne = tk.Frame(style, bg=theme.SURFACE)
        ligne.pack(fill="x", padx=theme.GRAND, pady=(0, theme.GRAND))
        textes = tk.Frame(ligne, bg=theme.SURFACE)
        textes.pack(fill="x")
        tk.Label(textes, text="Registre par défaut", bg=theme.SURFACE,
                 fg=theme.TEXTE, anchor="w",
                 font=theme.police(10)).pack(fill="x")
        theme.note(textes, "« Parlé » laisse « j'ai pas compris » tel quel ; "
                           "« soutenu » en fait « je n'ai pas compris »."
                   ).pack(fill="x", pady=(0, theme.MOYEN))
        self.choix_registre = theme.Segments(
            ligne,
            [(politique_mod.PARLE, "Parlé"), (politique_mod.SOUTENU, "Soutenu")],
            self.config.get("registre", politique_mod.PARLE),
        ).pack(anchor="w")

        raccourcis = self._section(colonne, "Raccourcis")
        theme.note(raccourcis, "Cliquez, puis appuyez sur la combinaison. "
                               "Échap annule, Retour arrière l'efface.").pack(
            fill="x", padx=theme.GRAND, pady=(0, theme.MOYEN))
        self.champs_raccourcis = {}
        for cle, libelle in (
            ("raccourci", "Corriger la sélection"),
            ("raccourci_annuler", "Annuler la dernière correction"),
            ("raccourci_relecture", "Relire avant de corriger"),
            ("raccourci_fenetre", "Ouvrir la fenêtre"),
        ):
            ligne = tk.Frame(raccourcis, bg=theme.SURFACE)
            ligne.pack(fill="x", padx=theme.GRAND, pady=2)
            tk.Label(ligne, text=libelle, bg=theme.SURFACE, fg=theme.TEXTE,
                     width=30, anchor="w", font=theme.police(10)).pack(side="left")
            self.champs_raccourcis[cle] = ChampRaccourci(
                ligne, self.config.get(cle, ""), sur_erreur=self._dire
            ).pack(side="left")

        if demarrage.disponible():
            systeme = self._section(colonne, "Windows")
            self.bascule_demarrage = self._ligne_interrupteur(
                systeme, "Lancer au démarrage de Windows",
                "Sans droits administrateur, et réversible.",
                demarrage.actif(), self._basculer_demarrage,
            )

        self._section_maj(colonne)
        self._section_journal(colonne)

        barre = tk.Frame(colonne, bg=theme.FOND, pady=theme.GRAND)
        barre.pack(fill="x")
        theme.Bouton(barre, "Enregistrer", self._enregistrer_reglages,
                     principal=True, icone="coche", fond=theme.FOND).pack(side="left")
        theme.note(barre, f"Fichier : {config_mod.chemin_config()}",
                   fond=theme.FOND).pack(side="left", padx=(theme.GRAND, 0))

    def _carte(self, parent) -> tk.Frame:
        """Un panneau, et son interieur convenablement espace."""
        cadre = theme.carte(parent)
        cadre.pack(fill="both", expand=True)
        dedans = tk.Frame(cadre, bg=theme.SURFACE, padx=theme.GRAND,
                          pady=theme.GRAND)
        dedans.pack(fill="both", expand=True)
        return dedans

    def _section(self, parent, titre: str) -> tk.Frame:
        cadre = theme.carte(parent)
        cadre.pack(fill="x", pady=(0, theme.MOYEN))
        theme.titre(cadre, titre).pack(fill="x", padx=theme.GRAND,
                                       pady=(theme.GRAND, theme.MOYEN))
        return cadre

    def _ligne_interrupteur(self, parent, libelle: str, explication: str,
                            valeur: bool, commande=None) -> theme.Interrupteur:
        ligne = tk.Frame(parent, bg=theme.SURFACE)
        ligne.pack(fill="x", padx=theme.GRAND, pady=(0, theme.MOYEN))

        textes = tk.Frame(ligne, bg=theme.SURFACE)
        textes.pack(side="left", fill="x", expand=True)
        tk.Label(textes, text=libelle, bg=theme.SURFACE, fg=theme.TEXTE,
                 anchor="w", font=theme.police(10)).pack(fill="x")
        theme.note(textes, explication).pack(fill="x")

        bascule = theme.Interrupteur(ligne, valeur, commande)
        bascule.pack(side="right", padx=(theme.MOYEN, 0))
        return bascule

    def _ligne_bascule(self, parent, cle: str, libelle: str, explication: str,
                       valeur: bool) -> None:
        self.bascules[cle] = self._ligne_interrupteur(parent, libelle,
                                                      explication, valeur)

    def _basculer_demarrage(self) -> None:
        try:
            actif = demarrage.basculer()
        except OSError as e:
            self._dire(f"Impossible : {e}", theme.ALERTE)
            return
        self.bascule_demarrage.set(actif)
        self._dire("Papote se lancera avec Windows." if actif
                   else "Papote ne se lancera plus avec Windows.", theme.SUCCES)

    # -- mises a jour -------------------------------------------------------

    def _section_maj(self, parent) -> None:
        cadre = self._section(parent, f"Mises à jour — version {__version__}")
        self.cadre_maj = tk.Frame(cadre, bg=theme.SURFACE)
        self.cadre_maj.pack(fill="x", padx=theme.GRAND, pady=(0, theme.GRAND))

        if maj.compilee():
            self.bascules["verifier_maj"] = self._ligne_interrupteur(
                cadre, "Chercher les nouvelles versions automatiquement",
                "Téléchargées en arrière-plan, installées au redémarrage.",
                self.config.get("verifier_maj", True),
            )

        # Le cadre existe meme lance depuis les sources : une fenetre dont la
        # moitie des attributs n'existent qu'a la compilation se casse ailleurs.
        self.boutons_maj = tk.Frame(self.cadre_maj, bg=theme.SURFACE)
        self.boutons_maj.pack(fill="x")
        self._dessiner_boutons_maj()

    def _dessiner_boutons_maj(self) -> None:
        for enfant in self.boutons_maj.winfo_children():
            enfant.destroy()

        if not maj.compilee() and self.maj_trouvee is None:
            theme.note(self.boutons_maj,
                       "Lancé depuis les sources : « git pull » fait le travail."
                       ).pack(fill="x")
            return

        if self.maj_trouvee is not None or maj.en_attente() is not None:
            version = self.maj_trouvee or maj.numero_en_attente()
            libelle = (f"Redémarrer pour installer {version}" if version
                       else "Redémarrer pour installer la mise à jour")
            theme.Bouton(self.boutons_maj, libelle, self._redemarrer,
                         principal=True, icone="telecharger",
                         fond=theme.SURFACE).pack(side="left")
            theme.note(self.boutons_maj,
                       "Papote se relance : rien de ce que vous écrivez n'est perdu."
                       ).pack(side="left", padx=(theme.MOYEN, 0))
            return

        theme.Bouton(self.boutons_maj, "Vérifier maintenant", self._verifier_maj,
                     petit=True, fond=theme.SURFACE).pack(side="left")

    def _verifier_maj(self) -> None:
        self._dire("Recherche d'une nouvelle version…")

        def travailler():
            try:
                version = maj.disponible()
            except maj.MiseAJourImpossible as e:
                self.racine.after(0, self._dire, f"Vérification impossible : {e}",
                                  theme.ALERTE)
                return
            if version is None:
                self.racine.after(0, self._dire, "Vous êtes déjà à jour.",
                                  theme.SUCCES)
                return
            # Vingt megaoctets par une connexion ordinaire, cela se compte en
            # secondes : sans un mot, on croit la recherche bloquee.
            self.racine.after(0, self._dire,
                              f"Téléchargement de la version {version}…")
            try:
                maj.installer_maintenant(version)
            except maj.MiseAJourImpossible as e:
                self.racine.after(0, self._dire, f"Téléchargement impossible : {e}",
                                  theme.ALERTE)
                return
            self.racine.after(0, self._maj_prete, version)

        threading.Thread(target=travailler, daemon=True).start()

    def _maj_prete(self, version) -> None:
        self.maj_trouvee = version
        self._dessiner_boutons_maj()
        self._annoncer_maj(version)
        self._dire(f"Version {version} téléchargée.", theme.SUCCES)

    def _annoncer_si_prete(self) -> None:
        """Propose le redemarrage si une version attend deja, d'ou qu'elle vienne.

        Le telechargement se fait souvent dans l'autre processus, celui de
        l'icone : la fenetre ne l'apprend qu'en regardant a cote de
        l'executable.
        """
        try:
            if maj.en_attente() is None:
                return
            numero = maj.numero_en_attente()
        except Exception:
            return
        self._annoncer_maj(numero)

    def _annoncer_maj(self, version) -> None:
        """Propose le redemarrage en bas de la colonne, quelle que soit la page.

        Telecharger sans le dire ne sert a rien : tant que Papote ne s'est pas
        relance, c'est l'ancienne version qui corrige. La proposition reste
        donc visible sur toutes les pages, et ne part que si on la renvoie.
        """
        for enfant in self.bandeau_maj.winfo_children():
            enfant.destroy()
        titre = f"Version {version} prête" if version else "Mise à jour prête"
        tk.Label(self.bandeau_maj, text=titre,
                 bg=theme.FOND, fg=theme.SUCCES, anchor="w",
                 font=theme.police(9, gras=True)).pack(fill="x")
        theme.note(self.bandeau_maj,
                   "Redémarrez pour l'installer. Rien n'est perdu.",
                   fond=theme.FOND).pack(fill="x", pady=(2, 6))
        theme.Bouton(self.bandeau_maj, "Redémarrer maintenant", self._redemarrer,
                     principal=True, petit=True, icone="telecharger",
                     fond=theme.FOND).pack(fill="x")
        theme.Bouton(self.bandeau_maj, "Plus tard", self._remettre_maj,
                     petit=True, fond=theme.FOND).pack(fill="x", pady=(4, 0))

    def _remettre_maj(self) -> None:
        """Renvoie la proposition : elle reste dans « Réglages », et au redemarrage."""
        for enfant in self.bandeau_maj.winfo_children():
            enfant.destroy()
        self._dire("La mise à jour s'installera au prochain démarrage.",
                   theme.TEXTE_DOUX)

    def _redemarrer(self) -> None:
        """Demande a Papote de se relancer : la mise a jour prend alors sa place."""
        try:
            maj.demander_redemarrage()
        except OSError as e:
            self._dire(f"Impossible : {e}", theme.ALERTE)
            return
        self._dire("Papote redémarre… Cette fenêtre peut être fermée.",
                   theme.SUCCES)

    # -- journal ------------------------------------------------------------

    def _section_journal(self, parent) -> None:
        cadre = self._section(parent, "Quand quelque chose ne va pas")
        dedans = tk.Frame(cadre, bg=theme.SURFACE)
        dedans.pack(fill="x", padx=theme.GRAND, pady=(0, theme.GRAND))

        theme.note(dedans, "Papote note ici ce qui s'est mal passé. Rien n'en "
                           "sort : le fichier reste sur votre machine.").pack(fill="x", pady=(0, theme.MOYEN))

        boutons = tk.Frame(dedans, bg=theme.SURFACE)
        boutons.pack(fill="x")
        theme.Bouton(boutons, "Ouvrir le journal", self._ouvrir_journal,
                     petit=True, fond=theme.SURFACE).pack(side="left")
        theme.Bouton(boutons, "Copier", self._copier_journal, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))
        theme.Bouton(boutons, "Effacer", self._effacer_journal, petit=True,
                     fond=theme.SURFACE).pack(side="left", padx=(6, 0))

    def _ouvrir_journal(self) -> None:
        chemin = journal_mod.chemin()
        if not chemin.exists():
            self._dire("Rien à signaler : le journal est vide.", theme.SUCCES)
            return
        try:
            _ouvrir_fichier(chemin)
        except OSError as e:
            self._dire(f"Ouverture impossible : {e}", theme.ALERTE)
            return
        self._dire(f"Journal ouvert : {chemin}")

    def _copier_journal(self) -> None:
        contenu = journal_mod.lire()
        if not contenu:
            self._dire("Rien à signaler : le journal est vide.", theme.SUCCES)
            return
        self.racine.clipboard_clear()
        self.racine.clipboard_append(contenu)
        self._dire("Journal copié — vous pouvez le coller quelque part.",
                   theme.SUCCES)

    def _effacer_journal(self) -> None:
        journal_mod.vider()
        self._dire("Journal effacé.", theme.SUCCES)

    # -- enregistrement -----------------------------------------------------

    def _enregistrer_reglages(self) -> None:
        for cle in ("correction_auto", "collage_auto", "notifications",
                    "apprentissage"):
            self.config[cle] = self.bascules[cle].get()
        self.config["regles_optionnelles"] = {
            nom: self.bascules[nom].get() for nom in regles.REGLES_OPTIONNELLES
        }
        self.config["registre"] = self.choix_registre.get()
        if "verifier_maj" in self.bascules:
            self.config["verifier_maj"] = self.bascules["verifier_maj"].get()

        choisis = {cle: champ.get() for cle, champ in self.champs_raccourcis.items()}
        occupes = [valeur for valeur in choisis.values() if valeur]
        if len(set(occupes)) != len(occupes):
            self._dire("Deux raccourcis ne peuvent pas être identiques.",
                       theme.ALERTE)
            return
        if not choisis["raccourci"]:
            self._dire("Le raccourci de correction ne peut pas être supprimé.",
                       theme.ALERTE)
            return
        self.config.update(choisis)

        self._enregistrer("Réglages enregistrés.")

    def _enregistrer(self, message: str) -> None:
        """Ecrit les reglages et previent l'application qui tourne."""
        try:
            config_mod.sauvegarder(self.config)
        except OSError as e:
            self._dire(f"Impossible d'enregistrer : {e}", theme.ALERTE)
            return
        try:
            self.app.recharger(dict(self.config))
        except Exception:
            # L'icone de la barre des taches relira le fichier de son cote.
            pass
        self._dire(message, theme.SUCCES)

    # -- boucle -------------------------------------------------------------

    def poser_le_texte(self, texte: str) -> None:
        """Remplit la page « Corriger », avant que la fenetre ne s'ouvre.

        C'est par la qu'arrive le texte selectionne au raccourci de
        relecture : il est deja la quand l'utilisateur voit la fenetre.
        """
        self.champ.delete("1.0", "end")
        self.champ.insert("1.0", texte)

    def lancer(self) -> None:
        self.racine.mainloop()


def _ouvrir_fichier(chemin) -> None:
    """Confie le fichier au systeme, qui sait avec quoi l'ouvrir."""
    import os
    import subprocess
    import sys as systeme

    if os.name == "nt":
        os.startfile(chemin)  # noqa: S606
    elif systeme.platform == "darwin":
        subprocess.Popen(["open", str(chemin)])
    else:
        subprocess.Popen(["xdg-open", str(chemin)])


def _cle(nom: str) -> str:
    """« Mon dictionnaire » -> « mon_dictionnaire », pour nommer les methodes."""
    sans_accents = (nom.lower().replace("é", "e").replace("è", "e")
                    .replace("ê", "e").replace("à", "a").replace("ç", "c"))
    return sans_accents.replace(" ", "_").replace("'", "_")
