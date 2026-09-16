# -*- coding: utf-8 -*-
"""Tests de la correction au fil de la frappe.

Le principe de ces tests : un ecran factice. On tape caractere par caractere,
on applique les remplacements demandes, et on verifie ce que l'utilisateur
aurait sous les yeux. L'ecran refuse au passage tout remplacement qui
n'efface pas exactement ce que le correcteur croyait effacer — c'est la
verification qui compte, puisqu'un decalage d'un seul caractere abimerait le
texte.
"""

import sys
import threading
import time
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import bulle as bulle_mod  # noqa: E402
from papote.frappe import EcouteClavier, Frappe, Remplacement  # noqa: E402
from papote.moteur import Correcteur  # noqa: E402


class Ecran:
    """Ce que l'utilisateur voit vraiment."""

    def __init__(self):
        self.texte = ""

    def taper(self, caractere):
        self.texte += caractere

    def appliquer(self, remplacement):
        assert remplacement.effacer <= len(self.texte), \
            "le correcteur efface plus de caracteres qu'il n'en existe"
        coupe = len(self.texte) - remplacement.effacer
        assert self.texte[coupe:] == remplacement.avant, \
            (f"le correcteur croit effacer {remplacement.avant!r} "
             f"alors qu'il efface {self.texte[coupe:]!r}")
        self.texte = self.texte[:coupe] + remplacement.ecrire


def frapper(correcteur, saisie):
    """Tape `saisie` caractere par caractere. Renvoie (ecran, corrections)."""
    frappe = Frappe(correcteur)
    ecran = Ecran()
    corrections = []
    for caractere in saisie:
        ecran.taper(caractere)
        remplacement = frappe.caractere(caractere)
        if remplacement is not None:
            ecran.appliquer(remplacement)
            corrections.append(remplacement)
    return ecran.texte, corrections


SAISIES = [
    ("je sais pas si sa va marcher ", "je sais pas si ça va marcher "),
    ("ils on mangé tout les gateaux. ", "ils ont mangé tous les gâteaux. "),
    ("cest tres interressant se truc ", "c'est très intéressant ce truc "),
    ("salut sa va ? jai pas compris ", "salut ça va ? j'ai pas compris "),
    ("tu mange quoi ce soir ? ", "tu manges quoi ce soir ? "),
    ("elles sont venu hier, ", "elles sont venues hier, "),
]

INTOUCHABLES = [
    "j'ai pas eu le temps, on se voit demain ? ",
    "wsh tkt frr ",
    "c'est pas grave, y a personne ",
    "the game is over ",
]


@pytest.mark.parametrize("saisie,attendu", SAISIES)
def test_le_texte_se_corrige_en_le_tapant(correcteur, saisie, attendu):
    assert frapper(correcteur, saisie)[0] == attendu


@pytest.mark.parametrize("saisie", INTOUCHABLES)
def test_rien_ne_bouge_quand_il_n_y_a_rien_a_corriger(correcteur, saisie):
    ecran, corrections = frapper(correcteur, saisie)
    assert ecran == saisie
    assert corrections == []


def test_la_correction_attend_le_mot_suivant(correcteur):
    """« sa » seul est un possessif : c'est « va » qui le condamne."""
    frappe = Frappe(correcteur)
    for caractere in "sa ":
        assert frappe.caractere(caractere) is None
    remplacement = None
    for caractere in "va ":
        remplacement = frappe.caractere(caractere) or remplacement
    assert remplacement is not None
    assert remplacement.ecrire.endswith("ça va ")


def test_rien_ne_part_avant_la_fin_du_mot(correcteur):
    """Tant que le mot n'est pas termine, on ne touche a rien."""
    frappe = Frappe(correcteur)
    for caractere in "gateaux":
        assert frappe.caractere(caractere) is None


def test_le_point_referme_la_phrase(correcteur):
    frappe = Frappe(correcteur)
    for caractere in "bonjour. ":
        frappe.caractere(caractere)
    assert frappe.texte == ""


def test_le_retour_arriere_suit_la_frappe(correcteur):
    frappe = Frappe(correcteur)
    for caractere in "salut":
        frappe.caractere(caractere)
    frappe.retour_arriere()
    assert frappe.texte == "salu"


def test_effacer_plus_que_ce_qu_on_a_vu_fait_tout_oublier(correcteur):
    """L'utilisateur efface du texte ecrit avant nous : on ne sait plus rien."""
    frappe = Frappe(correcteur)
    frappe.caractere("a")
    frappe.retour_arriere()
    frappe.retour_arriere()
    assert frappe.texte == ""


def test_une_correction_trop_lointaine_est_abandonnee(correcteur):
    """Mieux vaut manquer une correction qu'effacer la moitie d'une phrase."""
    # « sa » n'est condamne qu'une fois « va » ecrit : la correction doit
    # remonter six caracteres en arriere, ce qu'on s'interdit ici.
    frappe = Frappe(correcteur, effacement_max=3)
    assert all(frappe.caractere(c) is None for c in "sa va ")

    # Avec la marge par defaut, la meme phrase se corrige.
    frappe = Frappe(correcteur)
    assert any(frappe.caractere(c) is not None for c in "sa va ")


def test_le_tampon_ne_grandit_pas_indefiniment(correcteur):
    frappe = Frappe(correcteur, longueur_max=40)
    for caractere in "un texte assez long pour deborder le tampon prevu " * 3:
        frappe.caractere(caractere)
    assert len(frappe.texte) <= 40


def test_les_remplacements_perso_partent_aussi_a_la_frappe(lexique):
    correcteur = Correcteur(lexique, remplacements_perso={"ptetre": "peut-être"})
    assert frapper(correcteur, "ptetre ")[0] == "peut-être "


def test_annuler_remet_ce_qui_etait_ecrit():
    remplacement = Remplacement(effacer=3, ecrire="ça ", avant="sa ")
    inverse = remplacement.inverse
    assert inverse.effacer == len("ça ")
    assert inverse.ecrire == "sa "


# -- traduction des touches -------------------------------------------------

class FauxClavier(types.ModuleType):
    """Un module `keyboard` factice : les tests n'ont pas de vrai clavier."""

    def __init__(self, enfonces=()):
        super().__init__("keyboard")
        self.enfonces = set(enfonces)
        self.tapes = []

    def is_pressed(self, touche):
        return touche in self.enfonces

    def hook(self, fonction):
        return fonction

    def unhook(self, _branchement):
        pass

    def send(self, touche):
        self.tapes.append(touche)

    def write(self, texte, delay=0):
        self.tapes.append(texte)


class FauxEvenement:
    def __init__(self, name, event_type="down"):
        self.name = name
        self.event_type = event_type


@pytest.fixture
def clavier(monkeypatch):
    faux = FauxClavier()
    monkeypatch.setitem(sys.modules, "keyboard", faux)
    return faux


def ecoute(correcteur):
    """Une ecoute branchee sur rien, qui corrige partout.

    Sans `application`, elle interroge le systeme pour savoir ou l'on tape.
    Sur une machine de test Windows, la reponse est une vraie application —
    parfois un terminal, ou Papote se tait — et le test echoue pour une
    raison qui n'a rien a voir avec ce qu'il eprouve.
    """
    return EcouteClavier(Frappe(correcteur), application=lambda: None)


@pytest.mark.parametrize("touche,attendu", [
    ("a", "a"),
    ("space", " "),
    ("enter", "\n"),
    ("tab", "\t"),
    ("é", "é"),
])
def test_les_touches_ordinaires_deviennent_des_caracteres(correcteur, clavier,
                                                          touche, attendu):
    assert ecoute(correcteur)._traduire(FauxEvenement(touche)) == attendu


def test_la_majuscule_est_respectee(correcteur, clavier):
    clavier.enfonces.add("shift")
    assert ecoute(correcteur)._traduire(FauxEvenement("a")) == "A"


@pytest.mark.parametrize("touche", ["left", "home", "delete", "escape", "^", "f5"])
def test_les_touches_qui_brouillent_la_piste_ne_sont_pas_retenues(correcteur,
                                                                  clavier, touche):
    assert ecoute(correcteur)._traduire(FauxEvenement(touche)) is None


def test_un_raccourci_fait_oublier_la_phrase(correcteur, clavier):
    clavier.enfonces.add("ctrl")
    surveillant = ecoute(correcteur)
    surveillant.frappe.texte = "bonjour"
    assert surveillant._traduire(FauxEvenement("c")) is None
    assert surveillant.frappe.texte == ""


def test_le_retour_arriere_ne_produit_aucun_caractere(correcteur, clavier):
    surveillant = ecoute(correcteur)
    surveillant.frappe.texte = "salut"
    assert surveillant._traduire(FauxEvenement("backspace")) is None
    assert surveillant.frappe.texte == "salu"


def test_les_relachements_de_touche_sont_ignores(correcteur, clavier):
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    surveillant._sur_evenement(FauxEvenement("a", event_type="up"))
    assert surveillant.frappe.texte == ""


def test_un_silence_trop_long_fait_oublier_la_phrase(correcteur, clavier):
    """Apres une pause, le curseur a pu aller ailleurs : on repart de zero.

    L'horloge est reculee a la main plutot qu'attendue : sous Windows,
    `time.monotonic` avance par paliers de quinze millisecondes, et un test
    qui compte sur une pause reelle y devient une loterie.
    """
    surveillant = EcouteClavier(Frappe(correcteur), delai_oubli=5.0)
    surveillant.actif = True

    surveillant._sur_evenement(FauxEvenement("a"))
    assert surveillant.frappe.texte == "a"

    surveillant._derniere_touche -= 60
    surveillant._sur_evenement(FauxEvenement("b"))
    assert surveillant.frappe.texte == "b"


def test_on_ne_s_ecoute_pas_soi_meme(correcteur, clavier):
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    surveillant._en_ecriture = True
    surveillant._sur_evenement(FauxEvenement("a"))
    assert surveillant.frappe.texte == ""
    assert surveillant._touche_pendant_ecriture


# -- retour arriere = annuler ------------------------------------------------

def _corriger_puis(surveillant, touches: str, tapes: list) -> None:
    for caractere in touches:
        surveillant._sur_evenement(FauxEvenement(
            {" ": "space"}.get(caractere, caractere)))


def test_le_premier_retour_arriere_ne_retire_que_l_espace(correcteur, clavier,
                                                           monkeypatch):
    """« mot␣ » puis retour arriere, c'est pour coller une virgule au mot.

    Corriger un mot pose une espace derriere lui. Beaucoup de gens la
    retirent aussitot pour ecrire « bonjour, » plutot que « bonjour , ».
    Prendre ce geste pour un refus de la correction la defaisait a chaque
    virgule.
    """
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    tapes = []
    monkeypatch.setattr(surveillant, "_taper_ailleurs", tapes.append)

    _corriger_puis(surveillant, "sa va ", tapes)
    assert tapes, "la correction n'a pas eu lieu"
    apres_correction = len(tapes)

    surveillant._sur_evenement(FauxEvenement("backspace"))

    assert len(tapes) == apres_correction, "rien ne devait etre retape"
    assert surveillant.frappe.texte == "ça va"


def test_la_virgule_se_colle_au_mot_corrige(correcteur, clavier, monkeypatch):
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    tapes = []
    monkeypatch.setattr(surveillant, "_taper_ailleurs", tapes.append)

    _corriger_puis(surveillant, "sa va ", tapes)
    surveillant._sur_evenement(FauxEvenement("backspace"))
    surveillant._sur_evenement(FauxEvenement(","))

    assert surveillant.frappe.texte == "ça va,"


def test_le_second_retour_arriere_defait_la_correction(correcteur, clavier,
                                                        monkeypatch):
    """Comme sur un clavier de telephone : on efface, la correction s'annule.

    Le premier appui a retire l'espace ; le second attaque le mot, et c'est
    la qu'on comprend le refus.
    """
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    tapes = []
    monkeypatch.setattr(surveillant, "_taper_ailleurs", tapes.append)

    _corriger_puis(surveillant, "sa va ", tapes)
    correction = tapes[-1]

    surveillant._sur_evenement(FauxEvenement("backspace"))
    surveillant._sur_evenement(FauxEvenement("backspace"))
    annulation = tapes[-1]

    # L'espace est deja parti, et la touche vient d'emporter une lettre : il
    # reste le mot moins ces deux caracteres a reprendre.
    assert annulation.effacer == len(correction.ecrire) - 2
    # On remet le mot d'origine, sans son espace : elle a ete retiree expres.
    assert annulation.ecrire == correction.avant.rstrip(" ")


def test_une_correction_sans_espace_se_defait_du_premier_appui(correcteur,
                                                                clavier,
                                                                monkeypatch):
    """La relecture a la pause ne pose pas de separateur : rien a retirer."""
    from papote.frappe import Remplacement

    surveillant = ecoute(correcteur)
    surveillant.actif = True
    tapes = []
    monkeypatch.setattr(surveillant, "_taper_ailleurs", tapes.append)

    surveillant._appliquer(Remplacement(3, "fous", "fou", ("ACCORD",)))
    assert surveillant._separateur_en_attente is False

    # Sans cela, le long silence depuis le demarrage ferme d'abord la
    # fenetre du retour arriere.
    surveillant._derniere_touche = time.monotonic()
    surveillant._sur_evenement(FauxEvenement("backspace"))
    assert tapes[-1].ecrire == "fou"


def test_une_autre_touche_referme_la_fenetre_de_l_annulation(correcteur, clavier,
                                                             monkeypatch):
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    tapes = []
    monkeypatch.setattr(surveillant, "_taper_ailleurs", tapes.append)

    for caractere in "sa va ":
        surveillant._sur_evenement(FauxEvenement(
            {" ": "space"}.get(caractere, caractere)))
    nombre = len(tapes)

    surveillant._sur_evenement(FauxEvenement("b"))
    surveillant._sur_evenement(FauxEvenement("backspace"))
    assert len(tapes) == nombre, "le retour arriere a annule trop tard"


def test_le_remplacement_retient_les_regles_qui_l_ont_produit(correcteur):
    """Annuler trois fois la meme regle doit pouvoir se remarquer."""
    frappe = Frappe(correcteur)
    remplacement = None
    for caractere in "sa va ":
        remplacement = frappe.caractere(caractere) or remplacement
    assert "SA_CA" in remplacement.regles


# -- ou corriger -------------------------------------------------------------

def test_papote_se_tait_dans_les_applications_exclues(correcteur, clavier):
    from papote.politique import Politique

    surveillant = EcouteClavier(
        Frappe(correcteur),
        politique=Politique(exclues=["cmd.exe"]),
        application=lambda: "cmd.exe",
    )
    surveillant.actif = True
    for caractere in "sa va ":
        surveillant._sur_evenement(FauxEvenement(
            {" ": "space"}.get(caractere, caractere)))
    assert surveillant.frappe.texte == ""


def test_changer_de_fenetre_fait_oublier_la_phrase(correcteur, clavier):
    fenetres = ["discord.exe"]
    surveillant = EcouteClavier(
        Frappe(correcteur), application=lambda: fenetres[0]
    )
    surveillant.actif = True
    surveillant._sur_evenement(FauxEvenement("a"))
    assert surveillant.frappe.texte == "a"

    fenetres[0] = "word.exe"
    surveillant._application_vue = 0        # la memoire de la fenetre expire
    surveillant._sur_evenement(FauxEvenement("b"))
    assert surveillant.frappe.texte == "b"


def test_le_registre_suit_l_application(correcteur, clavier):
    from papote.politique import PARLE, SOUTENU, Politique

    temoins = []
    surveillant = EcouteClavier(
        Frappe(correcteur),
        politique=Politique(registres={"outlook.exe": SOUTENU}),
        application=lambda: "outlook.exe",
        correcteur_pour=lambda registre: temoins.append(registre) or correcteur,
    )
    surveillant.actif = True
    surveillant._sur_evenement(FauxEvenement("a"))
    assert temoins == [SOUTENU]
    assert surveillant._registre == SOUTENU
    assert surveillant.politique.registre_ici("discord.exe") == PARLE


# -- relecture a la pause ----------------------------------------------------
#
# Mot a mot, le correcteur travaille a l'aveugle : il ne voit pas ce qui n'est
# pas encore ecrit. « les gens » ne peut pas devenir « les gens sont fous »
# avant que « fou » ne soit tape. La relecture rattrape ce qui demandait la
# phrase entiere.

def taper(frappe, texte: str) -> None:
    for caractere in texte:
        frappe.caractere(caractere)


def test_la_relecture_accorde_ce_que_la_frappe_ne_pouvait_pas_voir(correcteur):
    frappe = Frappe(correcteur)
    taper(frappe, "les gens son fou")
    assert frappe.texte == "les gens sont fou", "la frappe corrige déjà « son »"

    remplacement = frappe.relire()
    assert remplacement is not None
    assert frappe.texte == "les gens sont fous"


@pytest.mark.parametrize("tape,attendu", [
    ("elle est venu", "elle est venue"),
    ("nous sommes arrive", "nous sommes arrivés"),
    ("les enfant", "les enfants"),
])
def test_la_relecture_rattrape_les_accords(correcteur, tape, attendu):
    frappe = Frappe(correcteur)
    taper(frappe, tape)
    frappe.relire()
    assert frappe.texte == attendu


def test_la_relecture_ne_termine_pas_un_mot_commence(correcteur):
    """Quelqu'un qui s'arrete sur « je mang » allait peut-etre ecrire
    « mangeais » : lui imposer « mange » serait insupportable."""
    frappe = Frappe(correcteur)
    taper(frappe, "je mang")
    assert frappe.relire() is None
    assert frappe.texte == "je mang"


def test_la_relecture_laisse_la_faute_de_frappe_du_dernier_mot(correcteur):
    """Elle sera corrigee des qu'une espace suivra — la, rien ne dit que le
    mot est fini."""
    frappe = Frappe(correcteur)
    taper(frappe, "je vais au bureua")
    assert frappe.relire() is None


def test_la_relecture_corrige_le_dernier_mot_fini_par_une_espace(correcteur):
    frappe = Frappe(correcteur)
    taper(frappe, "je vais au bureua ")
    assert frappe.texte == "je vais au bureau "


def test_une_phrase_deja_juste_ne_bouge_pas(correcteur):
    frappe = Frappe(correcteur)
    taper(frappe, "les enfants sont rentrés")
    assert frappe.relire() is None


def test_la_relecture_ne_touche_pas_a_un_tampon_vide(correcteur):
    assert Frappe(correcteur).relire() is None


def test_une_relecture_trop_longue_est_refusee(correcteur):
    """Une longue rafale de retours arriere se verrait a l'ecran."""
    frappe = Frappe(correcteur, effacement_relecture=0)
    taper(frappe, "nous sommes arrive")
    assert frappe.relire() is None
    assert frappe.texte == "nous sommes arrive"


def test_la_regle_d_une_lettre_ajoutee_n_est_pas_perdue(correcteur):
    """« fou » -> « fous » se termine la ou commence la reecriture.

    Sans cela, l'apprentissage ne saurait pas quelle regle annuler quand
    l'utilisateur defait la correction.
    """
    frappe = Frappe(correcteur)
    taper(frappe, "les gens son fou")
    remplacement = frappe.relire()
    assert remplacement.regles, "aucune regle attribuee"


def test_le_guetteur_ne_relit_qu_une_fois_par_pause(correcteur, monkeypatch):
    """Sans temoin, il relancerait la relecture quatre fois par seconde."""
    import papote.frappe as frappe_mod

    frappe = Frappe(correcteur)
    ecoute = frappe_mod.EcouteClavier(frappe, delai_oubli=5.0)
    ecoute.actif = True
    taper(frappe, "les gens son fou")

    relectures = []
    monkeypatch.setattr(frappe, "relire",
                        lambda: relectures.append(1) or None)
    monkeypatch.setattr(ecoute, "_application", lambda: None)
    ecoute._relu = False
    ecoute._derniere_touche = time.monotonic() - 1.0

    ecoute._relire_si_pause()
    ecoute._relire_si_pause()
    ecoute._relire_si_pause()
    assert len(relectures) == 1


def test_le_guetteur_attend_le_silence(correcteur, monkeypatch):
    import papote.frappe as frappe_mod

    frappe = Frappe(correcteur)
    ecoute = frappe_mod.EcouteClavier(frappe, delai_oubli=5.0)
    ecoute.actif = True
    taper(frappe, "les gens son fou")

    relectures = []
    monkeypatch.setattr(frappe, "relire",
                        lambda: relectures.append(1) or None)
    monkeypatch.setattr(ecoute, "_application", lambda: None)
    ecoute._relu = False
    # Les doigts viennent de bouger : trop tot.
    ecoute._derniere_touche = time.monotonic()
    ecoute._relire_si_pause()
    assert not relectures


def test_apres_un_long_silence_on_ne_relit_plus(correcteur, monkeypatch):
    """Passe le delai d'oubli, on ne sait plus ou est le curseur."""
    import papote.frappe as frappe_mod

    frappe = Frappe(correcteur)
    ecoute = frappe_mod.EcouteClavier(frappe, delai_oubli=2.0)
    ecoute.actif = True
    taper(frappe, "les gens son fou")

    relectures = []
    monkeypatch.setattr(frappe, "relire",
                        lambda: relectures.append(1) or None)
    monkeypatch.setattr(ecoute, "_application", lambda: None)
    ecoute._relu = False
    ecoute._derniere_touche = time.monotonic() - 10.0
    ecoute._relire_si_pause()
    assert not relectures


# -- prediction et bulle -----------------------------------------------------

class BulleTemoin:
    """Une bulle qui note ce qu'on lui demande, sans ouvrir d'ecran."""

    def __init__(self):
        self.montrees = []
        self.cachees = 0
        self.fermee = False
        self.visible = False

    def montrer(self, mot, propositions, touche="Tab"):
        self.montrees.append((mot, list(propositions), touche))
        self.visible = True

    def cacher(self):
        self.cachees += 1
        self.visible = False

    def fermer(self):
        self.fermee = True


@pytest.fixture
def predicteur(lexique):
    from papote.prediction import Predicteur

    return Predicteur(lexique)


def test_le_mot_en_cours_s_arrete_au_dernier_separateur(correcteur):
    frappe = Frappe(correcteur)
    taper(frappe, "mon anni")
    assert frappe.mot_en_cours() == "anni"
    taper(frappe, " ")
    assert frappe.mot_en_cours() == ""


def test_sans_predicteur_rien_n_est_propose(correcteur):
    frappe = Frappe(correcteur)
    taper(frappe, "mon anni")
    assert frappe.prediction() == []
    assert frappe.accepter_prediction() is None


def test_la_prediction_suit_le_mot_en_cours(correcteur, predicteur):
    frappe = Frappe(correcteur, predicteur=predicteur)
    taper(frappe, "mon anni")
    assert "anniversaire" in frappe.prediction()


def test_accepter_ecrit_la_suite_et_met_a_jour_le_tampon(correcteur,
                                                          predicteur):
    frappe = Frappe(correcteur, predicteur=predicteur)
    taper(frappe, "mon anni")
    remplacement = frappe.accepter_prediction()
    assert remplacement.effacer == 0
    assert remplacement.ecrire == "versaire"
    assert frappe.texte == "mon anniversaire"


def test_la_prediction_n_efface_jamais(correcteur, predicteur):
    """« deja » propose « déjà », mais l'accepter demanderait de reculer."""
    frappe = Frappe(correcteur, predicteur=predicteur)
    taper(frappe, "deja")
    assert "déjà" in frappe.prediction()
    assert frappe.accepter_prediction() is None


def test_la_bulle_s_affiche_quand_il_y_a_de_quoi_proposer(correcteur,
                                                           predicteur):
    bulle = BulleTemoin()
    frappe = Frappe(correcteur, predicteur=predicteur)
    ecoute = EcouteClavier(frappe, bulle=bulle)
    ecoute.actif = True

    taper(frappe, "mon anni")
    ecoute._proposer()
    assert bulle.montrees
    mot, propositions, touche = bulle.montrees[-1]
    assert mot == "anni"
    assert "anniversaire" in propositions
    assert touche == "Tab"


def test_la_bulle_disparait_quand_il_n_y_a_rien(correcteur, predicteur):
    bulle = BulleTemoin()
    frappe = Frappe(correcteur, predicteur=predicteur)
    ecoute = EcouteClavier(frappe, bulle=bulle)
    ecoute.actif = True

    taper(frappe, "zz")
    ecoute._proposer()
    assert not bulle.montrees
    assert bulle.cachees


def test_accepter_depuis_le_clavier_tape_la_suite(correcteur, predicteur,
                                                   monkeypatch):
    bulle = BulleTemoin()
    frappe = Frappe(correcteur, predicteur=predicteur)
    ecoute = EcouteClavier(frappe, bulle=bulle)
    ecoute.actif = True
    taper(frappe, "mon anni")

    tapes = []
    monkeypatch.setattr(ecoute, "_taper_ailleurs", tapes.append)
    ecoute._accepter_prediction()

    assert tapes and tapes[0].ecrire == "versaire"
    assert bulle.cachees, "la bulle doit disparaitre une fois acceptee"


def test_la_touche_n_est_detournee_que_pendant_l_affichage(correcteur,
                                                            predicteur,
                                                            monkeypatch):
    """L'intercepter en permanence casserait la tabulation partout."""
    bulle = BulleTemoin()
    frappe = Frappe(correcteur, predicteur=predicteur)
    ecoute = EcouteClavier(frappe, bulle=bulle)
    ecoute.actif = True

    armes = []
    monkeypatch.setattr(ecoute, "_armer_la_touche",
                        lambda: armes.append("armee"))
    monkeypatch.setattr(ecoute, "_desarmer_la_touche",
                        lambda: armes.append("desarmee"))

    taper(frappe, "mon anni")
    ecoute._proposer()
    assert armes == ["armee"]

    taper(frappe, "zzzz")
    ecoute._proposer()
    assert armes == ["armee", "desarmee"]


def test_une_prediction_qui_leve_ne_casse_rien(correcteur, monkeypatch):
    """Le clavier passe avant l'agrement."""
    class Fache:
        def completer(self, _prefixe, maximum=3):
            raise RuntimeError("non")

        def suite(self, _prefixe):
            raise RuntimeError("non")

    bulle = BulleTemoin()
    frappe = Frappe(correcteur, predicteur=Fache())
    ecoute = EcouteClavier(frappe, bulle=bulle)
    ecoute.actif = True
    taper(frappe, "mon anni")

    ecoute._proposer()          # ne doit pas lever
    ecoute._accepter_prediction()
    assert not bulle.montrees


def test_la_bulle_muette_ne_fait_rien():
    from papote.bulle import BulleMuette

    muette = BulleMuette()
    muette.montrer("anni", ["anniversaire"])
    muette.cacher()
    muette.fermer()
    assert muette.visible is False


def test_la_bulle_se_perime_et_rend_la_touche(correcteur):
    """Une bulle oubliee a l'ecran garde la touche de validation detournee.

    Quelqu'un qui commence a taper un identifiant, voit la bulle apparaitre
    et appuie sur Tab pour passer au mot de passe verrait sa tabulation
    avalee. Passe le delai, la touche redevient la touche.
    """
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None)
    ecoute._montree_a = time.monotonic() - bulle_mod.DUREE_MAXIMALE - 1
    ecoute._perimer_la_bulle()
    assert ecoute._montree_a is None


def test_une_bulle_recente_reste_affichee(correcteur):
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None)
    ecoute._montree_a = time.monotonic()
    ecoute._perimer_la_bulle()
    assert ecoute._montree_a is not None


# ---------------------------------------------------------------------------
# Ce qu'un testeur a trouvé en pilotant vraiment le clavier
# ---------------------------------------------------------------------------

def test_un_clic_fait_oublier_la_phrase(correcteur):
    """Un clic déplace le curseur, et aucune touche ne le signale.

    Les flèches étaient surveillées, la souris non : cliquer ailleurs puis
    reprendre la frappe faisait corriger à partir d'un tampon qui décrivait
    un autre endroit du texte.
    """
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None)
    ecoute.actif = True
    for caractere in "sa ":
        ecoute.frappe.caractere(caractere)
    ecoute._sur_clic(type("ButtonEvent", (), {})())
    assert ecoute.frappe.texte == ""


def test_la_molette_ne_fait_rien_oublier(correcteur):
    """Elle fait défiler, elle ne déplace pas le curseur."""
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None)
    ecoute.actif = True
    for caractere in "sa ":
        ecoute.frappe.caractere(caractere)
    ecoute._sur_clic(type("WheelEvent", (), {})())
    assert ecoute.frappe.texte == "sa "


def test_une_annulation_trop_tardive_ne_tape_rien(correcteur):
    """Le raccourci est global : rien n'empêche de l'actionner ailleurs.

    L'annulation tape là où est le curseur, pas là où la correction a eu
    lieu : « ça va bien » + Ctrl+Alt+Z donnait « ça vsa va ».
    """
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None)
    ecoute.annulables.append(Remplacement(5, "ça va", "sa va"))
    ecoute._derniere_touche = time.monotonic() - 100
    assert ecoute.annuler() is None
    # Elle reste disponible : on n'a rien perdu, on a seulement refusé de
    # taper à l'aveugle.
    assert ecoute.annulables


def test_une_tabulation_ferme_la_phrase(correcteur):
    """Dans un formulaire, la tabulation change de champ.

    Sans cela, « sa » tapé dans un champ puis « va » dans le suivant
    donnait six retours arrière envoyés au second champ, qui n'en
    contenait que trois.
    """
    frappe = Frappe(correcteur)
    for caractere in "sa":
        frappe.caractere(caractere)
    frappe.caractere("\t")
    correction = None
    for caractere in "va ":
        correction = frappe.caractere(caractere) or correction
    assert correction is None


def test_une_exception_dans_le_rappel_ne_tue_pas_l_ecoute(correcteur):
    """Sous Windows, une exception qui traverse le crochet le fait supprimer.

    Papote devient alors muet sans le dire. `sur_correction` écrit sur le
    disque : un disque plein suffisait.
    """
    ecoute = EcouteClavier(Frappe(correcteur), application=lambda: None,
                           sur_correction=lambda _r: 1 / 0)
    ecoute.actif = True
    for caractere in "sa va ":
        ecoute._sur_evenement(_touche(caractere))
    # On est encore là, et le tampon a été oublié par prudence.
    assert ecoute.frappe.texte == ""


def _touche(caractere: str):
    nom = "space" if caractere == " " else caractere
    return type("E", (), {"event_type": "down", "name": nom,
                          "scan_code": 0})()


# ---------------------------------------------------------------------------
# Deux fils, un seul tampon
#
# Le crochet clavier et le guetteur de pause tournent en parallele. Le second
# lit la phrase, calcule une correction, puis l'ecrit — et entre la lecture et
# l'ecriture, le premier peut avoir tout change. Ces epreuves verifient que la
# relecture renonce plutot que d'ecrire au hasard.
# ---------------------------------------------------------------------------

def test_la_relecture_renonce_si_le_clavier_tient_le_verrou(correcteur,
                                                            clavier):
    ecouteur = ecoute(correcteur)
    ecouteur.actif = True
    for caractere in "les gens":
        ecouteur.frappe.caractere(caractere)
    ecouteur._relu = False
    ecouteur._derniere_touche = time.monotonic() - 1.0

    relu = []
    ecouteur._relire_maintenant = lambda: relu.append(True)

    verrou_pris = threading.Event()
    relacher = threading.Event()

    def tenir():
        with ecouteur._verrou:
            verrou_pris.set()
            relacher.wait(1.0)

    fil = threading.Thread(target=tenir, daemon=True)
    fil.start()
    assert verrou_pris.wait(1.0)
    try:
        ecouteur._relire_si_pause()
        assert relu == []
        # Le temoin n'a pas ete pose : le battement suivant reessaiera.
        assert ecouteur._relu is False
    finally:
        relacher.set()
        fil.join(1.0)

    ecouteur._relire_si_pause()
    assert relu == [True]


def test_le_crochet_clavier_prend_le_verrou(correcteur, clavier):
    ecouteur = ecoute(correcteur)
    ecouteur.actif = True

    tenus = []
    vrai_traitement = ecouteur._sur_evenement_sans_filet

    def observer(evenement):
        # `acquire(blocking=False)` depuis le meme fil reussirait : le verrou
        # est reentrant. On regarde donc depuis un autre fil.
        essai = []

        def tenter():
            essai.append(ecouteur._verrou.acquire(blocking=False))
            if essai[0]:
                ecouteur._verrou.release()

        fil = threading.Thread(target=tenter)
        fil.start()
        fil.join(1.0)
        tenus.append(essai[0])
        return vrai_traitement(evenement)

    ecouteur._sur_evenement_sans_filet = observer
    ecouteur._sur_evenement(FauxEvenement("a"))
    assert tenus == [False]


def test_l_arret_attend_le_guetteur(correcteur, clavier, monkeypatch):
    ecouteur = ecoute(correcteur)
    monkeypatch.setattr(ecouteur, "_ecouter_la_souris", lambda: None)
    ecouteur.activer()
    guetteur = ecouteur._guetteur
    assert guetteur is not None and guetteur.is_alive()
    ecouteur.desactiver()
    assert not guetteur.is_alive()
