# -*- coding: utf-8 -*-
"""Ce que Papote ecrit sur le disque, et ce qu'il n'y ecrit pas.

Papote lit tout ce qui est tape. C'est la condition pour corriger au fil de
la frappe, et c'est ce qui rend ces tests-la plus importants que les autres :
la promesse ecrite est que rien de ce qui n'est pas un mot du dictionnaire ne
survit a la session, et une promesse ecrite qui n'est pas tenue vaut moins
que pas de promesse du tout.

Le cas qui les motive : un mot de passe tape dans la mauvaise fenetre. C'est
exactement ce qui declenche une correction d'orthographe.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote import apprentissage as apprentissage_mod  # noqa: E402
from papote.app import _trace_sans_texte  # noqa: E402
from papote.frappe import Frappe, Remplacement  # noqa: E402
from papote.memoire import Memoire  # noqa: E402

SECRET = "Motdepase123"


def test_le_journal_ne_contient_jamais_le_texte_tape():
    """« ORTHOGRAPHE 12→13 » suffit a diagnostiquer une panne."""
    trace = _trace_sans_texte(
        Remplacement(12, "Motdepasse123", SECRET, ("ORTHOGRAPHE",)))
    assert SECRET not in trace
    assert "Motdepasse123" not in trace
    assert "ORTHOGRAPHE" in trace


def test_la_trace_dit_quand_meme_ce_qui_s_est_passe():
    trace = _trace_sans_texte(Remplacement(5, "ça va", "sa va", ("SA_CA",)))
    assert trace == "SA_CA 5→5"


def test_la_memoire_de_frappe_refuse_ce_qui_n_est_pas_un_mot(correcteur):
    memoire = Memoire()
    frappe = Frappe(correcteur, memoire=memoire)
    for caractere in f"bonjour {SECRET} ":
        frappe.caractere(caractere)
    assert "bonjour" in memoire.mots
    assert not any(SECRET.lower() in mot.lower() for mot in memoire.mots)


def filtre(correcteur):
    """Le filtre d'apprentissage, sorti de l'application qui le porte."""
    from papote.app import Application

    faux = object.__new__(Application)
    object.__setattr__(faux, "_correcteurs", {})
    type(faux)._mots_connus  # noqa: B018
    faux.__dict__["correcteur"] = correcteur
    return lambda *mots: Application._mots_connus(_AvecLexique(correcteur),
                                                  *mots)


class _AvecLexique:
    """Le strict minimum que `_mots_connus` demande : un correcteur."""

    def __init__(self, correcteur):
        self.correcteur = correcteur


def test_l_apprentissage_ne_retient_que_des_mots_connus(correcteur):
    """Le meme filtre que la memoire de frappe, sur l'autre chemin.

    Il manquait : « Motdepase123 → Motdepasse123 » entrait tel quel dans le
    fichier d'habitudes, qui survit a la session.
    """
    connus = filtre(correcteur)
    assert connus("bonjour", "bonjour")
    assert not connus(SECRET, "Motdepasse123")
    assert not connus("", "bonjour")
    assert not connus("zbeulotron", "bonjour")


def test_l_apprentissage_accepte_une_vraie_correction(correcteur):
    assert filtre(correcteur)("sa va", "ça va")


def test_le_fichier_d_habitudes_se_vide_vraiment(tmp_path):
    """Le bouton « Effacer l'historique » disait « effacé » sans effacer."""
    journal = apprentissage_mod.Journal()
    for _ in range(3):
        journal.correction_appliquee("malgres", "malgré")
    assert journal.total_corrections() == 3
    journal.vider()
    assert journal.total_corrections() == 0
    assert journal.fautes_frequentes() == []


# ---------------------------------------------------------------------------
# Le fichier du raccourci de relecture
#
# Ctrl+Alt+R ecrit la selection sur le disque pour la passer au processus qui
# affiche la fenetre. C'est le seul moment ou du texte saisi touche un
# fichier, et il doit disparaitre quoi qu'il arrive — y compris quand la
# fenetre refuse de s'ouvrir.
# ---------------------------------------------------------------------------

def test_le_fichier_de_relecture_disparait_meme_si_la_fenetre_echoue(
        tmp_path, monkeypatch):
    from papote import __main__ as principal

    fichier = tmp_path / "relecture.txt"
    fichier.write_text("mon code secret 4712", encoding="utf-8")

    class FenetreImpossible(Exception):
        pass

    def refuser(app):
        raise FenetreImpossible

    monkeypatch.setattr(principal, "_ouvrir_fenetre", refuser)

    class FausseApp:
        texte_a_relire = ""

    app = FausseApp()
    with pytest.raises(FenetreImpossible):
        principal._relire(app, str(fichier))

    assert not fichier.exists()


def test_le_fichier_de_relecture_disparait_apres_usage(tmp_path, monkeypatch):
    from papote import __main__ as principal

    fichier = tmp_path / "relecture.txt"
    fichier.write_text("jai pas vu sa", encoding="utf-8")
    monkeypatch.setattr(principal, "_ouvrir_fenetre", lambda app: 0)

    class FausseApp:
        texte_a_relire = ""

    app = FausseApp()
    assert principal._relire(app, str(fichier)) == 0
    assert app.texte_a_relire == "jai pas vu sa"
    assert not fichier.exists()


# ---------------------------------------------------------------------------
# Le compteur des fautes
#
# La page « Vos fautes » vit d'un fichier qui survit a la session. Ce qui y
# entre doit donc etre du francais, et rien d'autre.
# ---------------------------------------------------------------------------

def test_le_compteur_ne_garde_que_la_forme_corrigee():
    """« Motdepase → Motdepasse » ne doit rien laisser derriere lui.

    Papote ne corrige que vers un mot qu'il connait : le cote droit est
    toujours du francais. Le cote gauche est par definition ce que le
    dictionnaire ignore, et rien ne distingue « jai » d'un mot de passe tape
    dans la mauvaise fenetre.
    """
    journal = apprentissage_mod.Journal()
    journal.correction_appliquee("Motdepase", "Motdepasse")
    journal.correction_appliquee("jai", "j'ai")

    ecrit = repr(journal.en_dictionnaire())
    assert "Motdepase→" not in ecrit
    assert "Motdepase " not in ecrit
    assert "jai" not in ecrit.replace("j'ai", "")
    assert set(journal.corrections) == {"Motdepasse", "j'ai"}


def test_la_page_se_remplit_quand_meme():
    """Le filtre d'amont exigeait que la faute soit un mot du dictionnaire.

    Une faute n'en est jamais un : la page restait vide. C'est la forme
    corrigee qu'on examine desormais, et elle, elle en est toujours un.
    """
    journal = apprentissage_mod.Journal()
    for avant, apres in [("jai", "j'ai"), ("sa", "ça"), ("jai", "j'ai"),
                         ("platforme", "plateforme")]:
        journal.correction_appliquee(avant, apres)
    assert journal.fautes_frequentes()[0] == ("j'ai", 2)
    assert journal.total_corrections() == 4


@pytest.mark.parametrize("mot,connu", [
    # L'elision : « j'ai » n'est pas au dictionnaire, « ai » l'est.
    ("j'ai", True),
    ("c'est", True),
    ("l'avion", True),
    ("qu'elle", True),
    ("ça", True),
    ("bonjour", True),
    # Et ce qui n'est pas du francais reste dehors, apostrophe ou pas.
    ("Motdepasse", False),
    ("zbeulotron", False),
    ("l'zbeulotron", False),
    ("", False),
])
def test_l_elision_ne_fait_pas_passer_un_mot_inconnu(correcteur, mot, connu):
    from papote.app import _mot_connu

    assert _mot_connu(correcteur.lexique, mot) is connu
