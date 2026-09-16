# -*- coding: utf-8 -*-
"""Correction au fil de la frappe.

Le raccourci oblige a s'interrompre : selectionner, appuyer, verifier. Ce
module supprime cette etape — le texte se corrige tout seul pendant qu'on
ecrit, comme sur un telephone.

Le principe est simple : on retient la phrase en cours de frappe, et chaque
fois qu'un mot se termine — une espace, une virgule, un point — on soumet la
phrase au correcteur. S'il propose autre chose, on efface ce qu'il faut et on
reecrit. « sa » ne devient « ça » qu'une fois « va » tape : c'est la phrase
qui tranche, pas le mot.

Tout est dans le fait de savoir exactement ce qui est a l'ecran. Le module
s'y tient par une regle unique : **au moindre doute, on oublie la phrase**.
Une touche inconnue, un accent mort, un deplacement du curseur, un silence
un peu long, et le tampon repart de zero. Une correction manquee ne se voit
pas ; une correction appliquee au mauvais endroit detruit le texte.

Deux details achevent le tableau. Papote ne corrige pas partout : dans un
terminal ou un editeur de code, il se tait (`politique.py`). Et un simple
**retour arriere** juste apres une correction la defait, comme sur un clavier
de telephone — la touche efface deja un caractere, il ne reste qu'a reprendre
les autres.

`Frappe` ne connait ni le clavier ni le systeme : elle recoit des caracteres
et rend des remplacements, ce qui la rend entierement testable.
`EcouteClavier` fait le reste.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from . import politique as politique_mod

# Un mot se termine sur l'un de ces caracteres. Ni l'apostrophe ni le trait
# d'union n'y figurent : « j'ai » et « est-ce » sont des mots entiers.
SEPARATEURS = " \t\n.,;:!?…\"()[]{}«»/\\|"

# Apres l'un de ceux-la, la phrase est finie : on repart a zero.
FINS_DE_PHRASE = ".!?…\n"

# Touches qui deplacent le curseur : ce qui est a l'ecran nous echappe.
TOUCHES_DE_DEPLACEMENT = {
    "left", "right", "up", "down", "home", "end", "page up", "page down",
    "delete", "esc", "escape", "insert",
}

# Accents morts : « ^ » puis « e » affiche « ê ». Le clavier nous annonce
# deux touches la ou l'ecran montre un caractere ; on ne sait plus compter.
ACCENTS_MORTS = {"^", "¨", "`", "~", "dead"}

TOUCHES_SPECIALES = {
    "space": " ",
    "enter": "\n",
    "return": "\n",
    "tab": "\t",
}


@dataclass(frozen=True)
class Remplacement:
    """Ce qu'il faut taper a la place de ce qui vient d'etre ecrit."""

    effacer: int      # nombre de retours arriere
    ecrire: str       # texte a taper ensuite
    avant: str        # ce qui disparait, pour pouvoir le remettre
    # Les regles qui ont produit ce remplacement. Annuler trois fois la meme
    # regle, c'est dire a Papote qu'elle derange.
    regles: tuple[str, ...] = ()

    @property
    def inverse(self) -> "Remplacement":
        """Le remplacement qui annule celui-ci."""
        return Remplacement(len(self.ecrire), self.avant, self.ecrire,
                            self.regles)

    def inverse_apres_retour_arriere(
            self, separateur_retire: bool = False) -> "Remplacement":
        """L'annulation quand l'utilisateur vient d'appuyer sur retour arriere.

        Sa touche a deja efface un caractere : il en reste un de moins a
        reprendre. C'est ce qui permet a Papote de se defaire d'un simple
        retour arriere, comme un clavier de telephone, sans avoir a empecher
        la touche d'agir.

        `separateur_retire` dit qu'un premier retour arriere a deja emporte
        l'espace pose par la correction. Il ne faut alors pas le remettre :
        s'il a ete efface, c'est qu'on voulait coller quelque chose au mot.
        """
        ecrit = self.ecrire[:-1] if separateur_retire else self.ecrire
        avant = self.avant[:-1] if separateur_retire else self.avant
        return Remplacement(max(0, len(ecrit) - 1), avant, ecrit, self.regles)

    def __str__(self) -> str:
        return f"{self.avant.strip()} → {self.ecrire.strip()}"


class Frappe:
    """Le texte en cours de frappe, et les corrections qu'il appelle.

    On lui donne les caracteres tapes ; elle rend un `Remplacement` quand une
    correction s'impose, et `None` le reste du temps.
    """

    def __init__(self, correcteur, longueur_max: int = 400,
                 effacement_max: int = 40,
                 effacement_relecture: int = 90,
                 predicteur=None, memoire=None):
        self.correcteur = correcteur
        # Facultatif : sans lui, `prediction()` ne rend rien et personne ne
        # s'en apercoit.
        self.predicteur = predicteur
        # Facultative aussi : c'est elle qui apprend vos tournures, et qui
        # fait passer « désolé » devant « désormais ».
        self.memoire = memoire
        self.longueur_max = longueur_max
        # Au-dela, la correction porte trop loin en arriere : la rafale de
        # retours arriere serait visible, et une desynchronisation couteuse.
        self.effacement_max = effacement_max
        # La relecture a la pause peut se permettre davantage : personne ne
        # tape pendant qu'elle travaille, et un accord se corrige souvent au
        # debut d'une phrase deja longue.
        self.effacement_relecture = effacement_relecture
        self.texte = ""

    # -- ce qui arrive du clavier -------------------------------------------

    def oublier(self) -> None:
        """Repart de zero : on ne sait plus ce qu'il y a a l'ecran."""
        self.texte = ""

    def retour_arriere(self) -> None:
        if self.texte:
            self.texte = self.texte[:-1]
        else:
            # L'utilisateur efface du texte qu'on n'a pas vu passer.
            self.oublier()

    def caractere(self, caractere: str) -> Remplacement | None:
        """Enregistre un caractere tape. Renvoie la correction s'il en faut une."""
        if not caractere:
            return None

        if not self.texte and caractere in SEPARATEURS:
            # Une phrase ne commence pas par une espace : ne pas la retenir
            # evite de croire qu'on suit un texte qu'on ne suit pas.
            return None

        avant = self.texte
        self.texte += caractere
        self._raccourcir()

        if caractere not in SEPARATEURS:
            return None

        self._retenir(avant)

        remplacement = self._examiner(caractere)

        if caractere in FINS_DE_PHRASE:
            # La phrase est close : la suivante n'a pas besoin de son contexte,
            # et un tampon qui ne grandit pas est un tampon qui ne derive pas.
            self.oublier()

        return remplacement

    def _retenir(self, avant: str) -> None:
        """Note le mot qui vient de s'achever, et ce qui le precede.

        Seuls les mots du dictionnaire sont retenus : un mot de passe tape
        dans la mauvaise fenetre, un numero, un nom propre n'ont rien a faire
        dans un fichier qui traine.
        """
        if self.memoire is None:
            return
        mots = avant.split()
        if not mots:
            return
        mot = mots[-1].lower().strip("'\u2019-")
        if len(mot) < 2 or not self.correcteur.lexique.connait(mot):
            return
        precedent = mots[-2].lower().strip("'\u2019-") if len(mots) > 1 else ""
        if precedent and not self.correcteur.lexique.connait(precedent):
            precedent = ""
        try:
            self.memoire.noter(precedent, mot)
        except Exception:
            pass

    # -- decision -----------------------------------------------------------

    def _raccourcir(self) -> None:
        """Ne garde que la fin du texte, coupee proprement entre deux mots."""
        if len(self.texte) <= self.longueur_max:
            return
        reste = self.texte[-self.longueur_max:]
        for i, caractere in enumerate(reste):
            if caractere in SEPARATEURS:
                self.texte = reste[i + 1:]
                return
        self.texte = reste

    def _examiner(self, separateur: str) -> Remplacement | None:
        corps = self.texte[:-1]
        if not corps.strip():
            return None

        # Ni majuscule ni point final — la phrase n'est pas finie — et pas de
        # recherche a deux frappes d'ecart : elle coute deux dixiemes de
        # seconde sur un mot inconnu, ce qui se sentirait sous les doigts.
        corrige, corrections = self.correcteur.corriger(
            corps, mise_en_forme=False, profond=False)
        if corrige == corps or not corrections:
            return None

        commun = _prefixe_commun(corps, corrige)

        # On ne sait taper que par la fin : tout ce qui suit le premier
        # caractere different doit etre reecrit, separateur compris.
        efface = corps[commun:] + separateur
        ecrit = corrige[commun:] + separateur

        if len(efface) > self.effacement_max:
            return None
        if "\n" in efface:
            # Remonter au-dessus d'une ligne demande de savoir ou elle
            # commence, ce que les retours arriere ne garantissent pas.
            return None

        self.texte = corrige + separateur
        # Seules comptent les regles qui ont touche la partie reecrite. Le
        # « superieur ou egal » n'est pas une coquetterie : « fou » -> « fous »
        # n'ajoute qu'une lettre, et sa correction se termine exactement la ou
        # commence la reecriture. Sans lui, l'apprentissage ne saurait jamais
        # quelle regle annuler.
        regles = tuple(dict.fromkeys(
            c.regle for c in corrections if c.fin >= commun
        ))
        return Remplacement(len(efface), ecrit, efface, regles)


    # -- prediction du mot en cours -------------------------------------------

    def mot_precedent(self) -> str:
        """Le mot acheve juste avant celui qu'on tape.

        C'est tout le contexte dont dispose la prediction : apres « bonne »,
        quelqu'un qui ecrit souvent « bonne journée » doit voir « journée »
        passer devant « jours ».
        """
        avant = self.texte[:self._debut_du_mot_en_cours()].rstrip(SEPARATEURS)
        for i in range(len(avant) - 1, -1, -1):
            if avant[i] in SEPARATEURS:
                return avant[i + 1:].lower()
        return avant.lower()

    def mot_en_cours(self) -> str:
        """Le debut de mot que l'on est en train de taper.

        Vide si le dernier caractere est un separateur : il n'y a alors aucun
        mot en cours, et rien a proposer.
        """
        return self.texte[self._debut_du_mot_en_cours():]

    def prediction(self) -> list[str]:
        """Les suites possibles du mot en cours, de la plus probable aux autres.

        Vide si la prediction est eteinte, ou si le debut de mot ne designe
        rien d'assez precis.
        """
        if self.predicteur is None:
            return []
        return self.predicteur.completer(self.mot_en_cours(),
                                         precedent=self.mot_precedent())

    def accepter_prediction(self) -> Remplacement | None:
        """Ce qu'il faut taper pour completer le mot, si la suite s'ajoute.

        La prediction n'efface jamais : elle ne fait qu'ajouter des lettres a
        droite. Une proposition qui demanderait de revenir sur un accent deja
        tape — « deja » vers « déjà » — s'affiche mais ne se valide pas.
        """
        if self.predicteur is None:
            return None
        suite = self.predicteur.suite(self.mot_en_cours(),
                                      precedent=self.mot_precedent())
        if not suite:
            return None
        self.texte += suite
        return Remplacement(0, suite, "", ("PREDICTION",))

    # -- relecture a la pause ------------------------------------------------

    def relire(self) -> Remplacement | None:
        """Relit toute la phrase, une fois les doigts arretes.

        Mot a mot, le correcteur travaille a l'aveugle : il ne voit pas ce qui
        n'est pas encore ecrit. « les gens » ne devient « les gens sont fous »
        qu'une fois « fou » tape, et la regle d'accord ne peut rien avant.
        Cette relecture rattrape ce que la frappe ne pouvait pas savoir —
        accords, conjugaisons, tout ce qui demande la phrase entiere.

        Elle s'autorise deux choses de plus que `_examiner`, parce qu'il n'y a
        plus personne aux commandes : la recherche a deux frappes d'ecart, et
        un effacement plus large. Elle s'en interdit une : toucher au mot en
        cours de frappe, qui n'est peut-etre qu'a moitie ecrit.
        """
        corps = self.texte
        if not corps.strip():
            return None

        # Le dernier mot est peut-etre a moitie ecrit — on s'est peut-etre
        # arrete au milieu pour reflechir. On note ou il commence.
        dernier_mot = self._debut_du_mot_en_cours()

        corrige, corrections = self.correcteur.corriger(
            corps, mise_en_forme=False, profond=True)
        if corrige == corps or not corrections:
            return None

        # Completer un mot inacheve serait insupportable : « je mang »
        # deviendrait « je mange » sous les doigts de quelqu'un qui allait
        # ecrire « mangeais ». L'accord, lui, n'a pas ce defaut : il ne
        # s'applique qu'a un mot que le dictionnaire connait deja, donc a un
        # mot fini. On ecarte donc l'orthographe sur le dernier mot, et elle
        # seule.
        if any(c.fin > dernier_mot and c.regle == "ORTHOGRAPHE"
               for c in corrections):
            return None

        commun = _prefixe_commun(corps, corrige)

        efface = corps[commun:]
        ecrit = corrige[commun:]
        if len(efface) > self.effacement_relecture or "\n" in efface:
            return None

        self.texte = corrige
        regles = tuple(dict.fromkeys(
            c.regle for c in corrections if c.fin >= commun
        ))
        return Remplacement(len(efface), ecrit, efface, regles)

    def _debut_du_mot_en_cours(self) -> int:
        """Ou commence le mot qu'on est en train de taper.

        Si le tampon se termine par un separateur, aucun mot n'est en cours et
        toute la phrase est relisible.
        """
        for i in range(len(self.texte) - 1, -1, -1):
            if self.texte[i] in SEPARATEURS:
                return i + 1
        return 0


def _prefixe_commun(gauche: str, droite: str) -> int:
    limite = min(len(gauche), len(droite))
    for i in range(limite):
        if gauche[i] != droite[i]:
            return i
    return limite


class EcouteClavier:
    """Branche `Frappe` sur le vrai clavier.

    Deux precautions gouvernent cette classe :

    - **Ne jamais s'ecouter soi-meme.** Taper un remplacement produit des
      evenements clavier ; les prendre pour de la frappe humaine ferait boucler
      l'ensemble. Un verrou les ecarte, et toute touche pressee pendant qu'on
      ecrit fait oublier la phrase : on ne sait plus dans quel ordre tout cela
      s'est pose a l'ecran.
    - **Ne rien retenir.** Le tampon vit en memoire, quelques centaines de
      caracteres au plus, et rien n'en sort : ni fichier, ni reseau. Il
      s'efface des que le doute s'installe.
    """

    # Duree pendant laquelle on se fie a la derniere application reconnue.
    # Interroger Windows a chaque touche serait du gaspillage ; un dixieme de
    # seconde de retard sur un changement de fenetre n'a aucune consequence.
    MEMOIRE_APPLICATION = 0.5

    # Silence au bout duquel on relit la phrase entiere. Assez long pour ne
    # pas tomber au milieu d'une hesitation, assez court pour que la
    # correction arrive avant qu'on ait appuye sur Entree.
    DELAI_RELECTURE = 0.9

    # Cadence du guetteur. Il ne fait rien tant que les doigts bougent ; ce
    # n'est pas la peine de le reveiller souvent.
    BATTEMENT = 0.25

    def __init__(self, frappe: Frappe, delai_oubli: float = 5.0,
                 sur_correction: Callable[[Remplacement], None] | None = None,
                 sur_annulation: Callable[[Remplacement], None] | None = None,
                 profondeur_annulation: int = 20,
                 politique: politique_mod.Politique | None = None,
                 application: Callable[[], str | None] | None = None,
                 correcteur_pour: Callable[[str], object] | None = None,
                 bulle=None, touche_prediction: str = "tab"):
        self.frappe = frappe
        # Sans bulle, la prediction ne s'affiche pas et la touche de
        # validation reste a l'application : c'est le comportement par defaut.
        self.bulle = bulle
        self.touche_prediction = touche_prediction
        self._piege_prediction = None
        self.delai_oubli = delai_oubli
        self.sur_correction = sur_correction
        self.sur_annulation = sur_annulation
        self.annulables: list[Remplacement] = []
        self.profondeur_annulation = profondeur_annulation

        self.politique = politique or politique_mod.Politique()
        self.application = application or politique_mod.application_active
        self.correcteur_pour = correcteur_pour

        self.actif = False
        self.derniere_application: str | None = None
        self._registre = politique_mod.PARLE
        self._application_vue = 0.0
        self._en_ecriture = False
        self._touche_pendant_ecriture = False
        self._derniere_touche = 0.0
        # La derniere correction, tant qu'aucune autre touche n'est venue :
        # c'est elle qu'un retour arriere immediat defait.
        self._defaisable: Remplacement | None = None
        # Cette correction s'est-elle terminee par un separateur que
        # l'utilisateur n'a pas encore retire ? Voir `_sur_evenement`.
        self._separateur_en_attente = False
        self._branchement = None
        # La relecture n'a lieu qu'une fois par pause : sans ce temoin, le
        # guetteur la relancerait quatre fois par seconde.
        self._relu = True
        self._guetteur: threading.Thread | None = None
        self._arret = threading.Event()

    # -- cycle de vie -------------------------------------------------------

    def activer(self) -> None:
        import keyboard

        if self._branchement is not None:
            return
        self.frappe.oublier()
        self._defaisable = None
        self._branchement = keyboard.hook(self._sur_evenement)
        self.actif = True
        self._arret.clear()
        self._guetteur = threading.Thread(target=self._guetter, daemon=True)
        self._guetteur.start()

    def desactiver(self) -> None:
        import keyboard

        self.actif = False
        self._arret.set()
        self._guetteur = None
        self._retirer_la_bulle()
        if self.bulle is not None:
            self.bulle.fermer()
        self.frappe.oublier()
        if self._branchement is None:
            return
        try:
            keyboard.unhook(self._branchement)
        except (KeyError, ValueError):
            pass
        self._branchement = None

    # -- reception des touches ----------------------------------------------

    def _application(self) -> str | None:
        """L'application au premier plan, sans harceler le systeme."""
        maintenant = time.monotonic()
        if maintenant - self._application_vue > self.MEMOIRE_APPLICATION:
            self._application_vue = maintenant
            try:
                nouvelle = self.application()
            except Exception:
                nouvelle = None
            if nouvelle != self.derniere_application:
                # On a change de fenetre : la phrase en cours n'est plus la
                # notre, et le registre peut changer avec elle.
                self.frappe.oublier()
                self._defaisable = None
                self.derniere_application = nouvelle
                self._adapter_registre(nouvelle)
        return self.derniere_application

    def _adapter_registre(self, application: str | None) -> None:
        if self.correcteur_pour is None:
            return
        registre = self.politique.registre_ici(application)
        if registre == self._registre:
            return
        self._registre = registre
        self.frappe.correcteur = self.correcteur_pour(registre)

    def _sur_evenement(self, evenement) -> None:
        if not self.actif:
            return

        if self._en_ecriture:
            # C'est nous qui tapons — ou l'utilisateur, par-dessus nous.
            self._touche_pendant_ecriture = True
            return

        if getattr(evenement, "event_type", None) != "down":
            return

        if not self.politique.corrige_ici(self._application()):
            # Un terminal, un editeur de code : on regarde ailleurs.
            self.frappe.oublier()
            self._defaisable = None
            return

        maintenant = time.monotonic()
        if maintenant - self._derniere_touche > self.delai_oubli:
            # Un silence : le curseur a pu aller ailleurs entre-temps.
            self.frappe.oublier()
            self._defaisable = None
        self._derniere_touche = maintenant
        self._relu = False

        if (getattr(evenement, "name", None) == "backspace"
                and self._defaisable is not None):
            if self._separateur_en_attente:
                # Le premier retour arriere retire l'espace que la correction
                # vient de poser. Ce n'est pas un refus : c'est qu'on veut
                # coller une virgule au mot — « bonjour, » plutot que
                # « bonjour , ». On laisse donc la touche agir, et la
                # correction reste defaisable d'un second appui.
                self._separateur_en_attente = False
                self.frappe.retour_arriere()
                return
            self._defaire(self._defaisable)
            return

        caractere = self._traduire(evenement)
        # Toute autre touche referme la fenetre du retour arriere.
        self._defaisable = None
        self._separateur_en_attente = False
        if caractere is None:
            return

        try:
            remplacement = self.frappe.caractere(caractere)
        except Exception:
            # Une correction ratee ne doit jamais emporter le clavier.
            self.frappe.oublier()
            return

        if remplacement is not None:
            self._appliquer(remplacement)
            self._proposer()
        else:
            self._proposer()

    # -- prediction ----------------------------------------------------------

    def _proposer(self) -> None:
        """Montre ou retire la bulle selon le mot en cours.

        Appelee a chaque touche : elle doit rester sans effet mesurable. La
        prediction coute un dixieme de milliseconde, l'affichage passe par
        une file d'attente et ne bloque pas.
        """
        if self.bulle is None:
            return
        try:
            propositions = self.frappe.prediction()
        except Exception:
            propositions = []

        if not propositions:
            self._retirer_la_bulle()
            return

        self.bulle.montrer(self.frappe.mot_en_cours(), propositions,
                           self.touche_prediction.title())
        self._armer_la_touche()

    def _armer_la_touche(self) -> None:
        """Detourne la touche de validation, le temps que la bulle soit la.

        Elle n'est detournee qu'a ce moment : l'intercepter en permanence
        casserait la tabulation partout ailleurs, dans les formulaires comme
        dans les editeurs.
        """
        if self._piege_prediction is not None:
            return
        try:
            import keyboard

            self._piege_prediction = keyboard.add_hotkey(
                self.touche_prediction, self._accepter_prediction,
                suppress=True, trigger_on_release=False)
        except Exception:
            # La bibliotheque refuse de detourner cette touche : la bulle
            # reste informative, et la touche garde son role habituel.
            self._piege_prediction = None

    def _retirer_la_bulle(self) -> None:
        if self.bulle is not None:
            self.bulle.cacher()
        self._desarmer_la_touche()

    def _desarmer_la_touche(self) -> None:
        if self._piege_prediction is None:
            return
        try:
            import keyboard

            keyboard.remove_hotkey(self._piege_prediction)
        except Exception:
            pass
        self._piege_prediction = None

    def _accepter_prediction(self) -> None:
        """La touche de validation a ete pressee pendant que la bulle etait la."""
        self._retirer_la_bulle()
        try:
            remplacement = self.frappe.accepter_prediction()
        except Exception:
            self.frappe.oublier()
            return
        if remplacement is not None:
            self._taper_ailleurs(remplacement)

    def _traduire(self, evenement) -> str | None:
        """Le caractere reellement tape, ou None s'il n'y a rien a retenir."""
        import keyboard

        nom = getattr(evenement, "name", None)
        if not nom:
            self.frappe.oublier()
            return None

        # Un raccourci est en cours : ce qui suit n'est pas de la frappe.
        # (AltGr se presente comme ctrl+alt : on prefere l'ecarter aussi.)
        if any(keyboard.is_pressed(touche) for touche in ("ctrl", "alt", "windows")):
            self.frappe.oublier()
            return None

        if nom == "backspace":
            self.frappe.retour_arriere()
            return None

        if nom in TOUCHES_DE_DEPLACEMENT:
            self.frappe.oublier()
            return None

        if nom in TOUCHES_SPECIALES:
            return TOUCHES_SPECIALES[nom]

        if nom in ACCENTS_MORTS:
            self.frappe.oublier()
            return None

        if len(nom) != 1:
            # Majuscule, fonction, verrouillage... : rien a ajouter au tampon.
            return None

        if keyboard.is_pressed("shift"):
            return nom.upper()
        return nom

    # -- relecture a la pause ------------------------------------------------

    def _guetter(self) -> None:
        """Attend que les doigts s'arretent, puis relit la phrase.

        Mot a mot, le correcteur ne voit que ce qui est deja ecrit : « les
        gens » ne peut pas devenir « les gens sont fous » avant que « fou » ne
        soit tape. Cette relecture rattrape ce qui demandait la phrase
        entiere — les accords, surtout.
        """
        while not self._arret.wait(self.BATTEMENT):
            try:
                self._relire_si_pause()
            except Exception:
                # Une relecture ratee ne doit jamais emporter le clavier.
                self.frappe.oublier()

    def _relire_si_pause(self) -> None:
        if not self.actif or self._relu or self._en_ecriture:
            return
        if not self.frappe.texte:
            return

        attente = time.monotonic() - self._derniere_touche
        if attente < self.DELAI_RELECTURE:
            return
        if attente > self.delai_oubli:
            # Le silence a dure : on ne sait plus ou est le curseur, et le
            # tampon va etre oublie de toute facon.
            self._relu = True
            return

        # L'utilisateur a pu changer de fenetre sans toucher au clavier.
        if not self.politique.corrige_ici(self._application()):
            self._relu = True
            return

        self._relu = True
        remplacement = self.frappe.relire()
        if remplacement is not None:
            self._retirer_la_bulle()
            self._appliquer(remplacement)

    # -- ecriture -----------------------------------------------------------

    def _appliquer(self, remplacement: Remplacement) -> None:
        self.annulables.append(remplacement)
        del self.annulables[:-self.profondeur_annulation]
        self._defaisable = remplacement
        self._separateur_en_attente = remplacement.ecrire[-1:] in SEPARATEURS
        if self.sur_correction is not None:
            self.sur_correction(remplacement)
        self._taper_ailleurs(remplacement)

    def _taper_ailleurs(self, remplacement: Remplacement) -> None:
        """Taper depuis le fil du crochet clavier le bloquerait."""
        threading.Thread(target=self._taper, args=(remplacement,),
                         daemon=True).start()

    def _defaire(self, remplacement: Remplacement) -> None:
        """Annule la correction que le retour arriere vient d'entamer."""
        separateur_retire = (remplacement.ecrire[-1:] in SEPARATEURS
                             and not self._separateur_en_attente)
        self._defaisable = None
        self._separateur_en_attente = False
        if self.annulables and self.annulables[-1] is remplacement:
            self.annulables.pop()
        self._taper_ailleurs(
            remplacement.inverse_apres_retour_arriere(separateur_retire))
        self.frappe.oublier()
        if self.sur_annulation is not None:
            self.sur_annulation(remplacement)

    def _taper(self, remplacement: Remplacement) -> None:
        import keyboard

        self._touche_pendant_ecriture = False
        self._en_ecriture = True
        try:
            for _ in range(remplacement.effacer):
                keyboard.send("backspace")
            keyboard.write(remplacement.ecrire, delay=0)
        except Exception:
            self.frappe.oublier()
        finally:
            self._en_ecriture = False
            if self._touche_pendant_ecriture:
                # L'utilisateur a tape pendant qu'on ecrivait : impossible de
                # savoir ce que donne le melange.
                self.frappe.oublier()

    # -- annulation ---------------------------------------------------------

    def annuler(self) -> Remplacement | None:
        """Remet ce qui etait ecrit avant la derniere correction automatique."""
        if not self.annulables:
            return None
        remplacement = self.annulables.pop()
        self._defaisable = None
        self._taper(remplacement.inverse)
        # Le mot rétabli ne doit pas etre recorrige dans la foulee : on repart
        # de la phrase suivante.
        self.frappe.oublier()
        if self.sur_annulation is not None:
            self.sur_annulation(remplacement)
        return remplacement
