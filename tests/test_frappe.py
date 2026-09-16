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
import time
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    return EcouteClavier(Frappe(correcteur))


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

def test_le_retour_arriere_defait_la_correction(correcteur, clavier, monkeypatch):
    """Comme sur un clavier de telephone : on efface, la correction s'annule."""
    surveillant = ecoute(correcteur)
    surveillant.actif = True
    tapes = []
    monkeypatch.setattr(surveillant, "_taper_ailleurs", tapes.append)

    for caractere in "sa va ":
        surveillant._sur_evenement(FauxEvenement(
            {" ": "space"}.get(caractere, caractere)))

    assert tapes, "la correction n'a pas eu lieu"
    correction = tapes[-1]

    surveillant._sur_evenement(FauxEvenement("backspace"))
    annulation = tapes[-1]

    # Le retour arriere de l'utilisateur a deja efface un caractere : il en
    # reste un de moins a reprendre.
    assert annulation.effacer == len(correction.ecrire) - 1
    assert annulation.ecrire == correction.avant


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
