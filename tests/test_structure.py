# -*- coding: utf-8 -*-
"""Qui est le sujet de quel verbe : les accords a distance.

Les phrases sont ecrites ici, pas reprises des bancs d'essai : la moitie
tenue a l'ecart des bancs doit le rester.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote.grammaire import Contexte, decouper  # noqa: E402
from papote.moteur import construire  # noqa: E402
from papote.structure import sujet_de_l_attribut, sujet_du_verbe  # noqa: E402


@pytest.fixture(scope="module")
def correcteur():
    return construire()


def _contexte(correcteur, phrase):
    return Contexte(phrase, decouper(phrase), correcteur.lexique, correcteur.morphologie)


@pytest.mark.parametrize("phrase,verbe,personne,debut", [
    ("Les voisins de ma tante arrivent demain.", 5, "3p", 0),
    ("Le prix des billets augmente.", 4, "3s", 0),
    ("La fille que tu as vue hier chante bien.", 6, "3s", 0),
    ("Mon frère et sa femme habitent ici.", 5, "3p", 0),
    ("Quand les beaux jours reviennent, on sort.", 4, "3p", 1),
    ("Les enfants, qui ont faim, mangent vite.", 5, "3p", 0),
    ("Les enfants ne lui parlent pas.", 4, "3p", 0),
    ("Beaucoup de gens pensent ça.", 3, "3p", 0),
])
def test_le_sujet_est_trouve(correcteur, phrase, verbe, personne, debut):
    sujet = sujet_du_verbe(_contexte(correcteur, phrase), verbe)
    assert sujet is not None and (sujet.personne, sujet.debut) == (personne, debut)


@pytest.mark.parametrize("phrase,verbe", [
    # une question : le sujet suit le verbe
    ("Quels livres lit ton frère ?", 2),
    ("Dans la cour jouent les enfants.", 3),
    # une enumeration, dont on ne voit que la fin
    ("Le pain, le lait, la farine manquent.", 7),
    # une comparaison n'ouvre pas de proposition
    ("Un homme plus fort que les autres gagne.", 7),
    # un nom collectif : les deux accords se disent
    ("Une foule de gens attendait.", 4),
])
def test_le_sujet_reste_inconnu_quand_le_chemin_est_douteux(correcteur, phrase, verbe):
    sujet = sujet_du_verbe(_contexte(correcteur, phrase), verbe)
    assert sujet is None or sujet.pronom


@pytest.mark.parametrize("phrase,attribut,personne,genre", [
    ("Elle semble vraiment fatiguée.", 3, "3s", "f"),
    ("Ils ont été très surpris.", 4, "3p", "m"),
    ("Les filles de la voisine sont parties.", 6, "3p", "f"),
    ("Ma sœur paraît être heureuse.", 4, "3s", "f"),
])
def test_l_attribut_trouve_son_sujet(correcteur, phrase, attribut, personne, genre):
    sujet = sujet_de_l_attribut(_contexte(correcteur, phrase), attribut)
    assert sujet is not None and (sujet.personne, sujet.genre) == (personne, genre)


@pytest.mark.parametrize("fautif,attendu", [
    # le verbe et son sujet eloigne
    ("Les voisins de ma tante arrive demain.", "Les voisins de ma tante arrivent demain."),
    ("Le prix des billets augmentent.", "Le prix des billets augmente."),
    ("La fille que tu as vue hier chantent bien.", "La fille que tu as vue hier chante bien."),
    ("Les amis de Paul vient ce soir.", "Les amis de Paul viennent ce soir."),
    ("Mon frère et sa femme habite ici.", "Mon frère et sa femme habitent ici."),
    ("Les enfants, qui a faim, mangent vite.", "Les enfants, qui ont faim, mangent vite."),
    # l'attribut et son sujet eloigne
    ("Elle semble vraiment fatigué.", "Elle semble vraiment fatiguée."),
    ("Ils ont été très surpris.", "Ils ont été très surpris."),
    ("Elles ont été surpris.", "Elles ont été surprises."),
    ("Ma sœur paraît être heureux.", "Ma sœur paraît être heureuse."),
    ("Ils semblent avoir été oublié.", "Ils semblent avoir été oubliés."),
    ("Les filles de la voisine sont vraiment parti.", "Les filles de la voisine sont vraiment parties."),
    ("Je suis tellement contents.", "Je suis tellement content."),
    ("Mon père et mon oncle sont restés très calme.", "Mon père et mon oncle sont restés très calmes."),
])
def test_l_accord_a_distance_est_corrige(correcteur, fautif, attendu):
    assert correcteur.corriger(fautif, mise_en_forme=False)[0] == attendu


@pytest.mark.parametrize("phrase", [
    "Quels livres lit ton frère ?",
    "Dans la cour jouent les enfants.",
    "Le pain, le lait, la farine manquent.",
    "Un homme plus fort que ses frères gagne la course.",
    "Une foule de gens attendait.",
    "Ces choses nous les gardons.",
    "Les chaises en bois craquent.",
    "Toute la semaine des camions passent ici.",
    "Mon père puis ma mère sont arrivés.",
    "Chaque élève et chaque professeur a reçu un livre.",
    "Ce sont des histoires vraies.",
    "La première chose qu'on voit sont les arbres.",
    "Nous nous étions promis de revenir.",
    "Elle était tout sourire.",
    "Ils sont bien sûr partis.",
    "Ce qu'ils croient être juste est discutable.",
    "Le rendez-vous que nous nous sommes fixé.",
    "Les gens comme Paul aiment ça.",
    "Après le repas, les invités sont partis.",
    "M. Martin et Mme Durand sont venus.",
    "Votre ancien site précédent reste en ligne.",
])
def test_la_phrase_juste_reste_intacte(correcteur, phrase):
    assert correcteur.corriger(phrase, mise_en_forme=False)[0] == phrase
