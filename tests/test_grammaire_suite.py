# -*- coding: utf-8 -*-
"""Les fautes de tous les jours : elision oubliee, « -là », « est-il », homophones.

Chaque regle a ses deux moities : ce qu'elle corrige, et ce qu'elle doit
laisser tranquille. La seconde compte plus.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.mark.parametrize("fautif,attendu", [
    # l'elision oubliee
    ("je ai pas le temps", "j'ai pas le temps"),
    ("Je aime ce jeu", "J'aime ce jeu"),
    ("que il vienne", "qu'il vienne"),
    ("de accord avec toi", "d'accord avec toi"),
    ("le ami de mon frère", "l'ami de mon frère"),
    ("la école ferme", "l'école ferme"),
    ("si il vient je pars", "s'il vient je pars"),
    ("ce est bon", "c'est bon"),
    ("ne ai pas compris", "n'ai pas compris"),
    ("de hier soir", "d'hier soir"),
    # l'apostrophe tapee comme une espace
    ("c est bon", "c'est bon"),
    ("j ai faim", "j'ai faim"),
    ("qu est ce que tu fais", "qu'est-ce que tu fais"),
    ("on sen fout", "on s'en fout"),
    # -là
    ("ce mec la est fou", "ce mec-là est fou"),
    ("cette fille la est sympa", "cette fille-là est sympa"),
    ("ces gens la sont fous", "ces gens-là sont fous"),
    ("ce jour la", "ce jour-là"),
    # l'inversion
    ("quelle heure est til", "quelle heure est-il"),
    ("a til le temps", "a-t-il le temps"),
    # homophones
    ("tu m'a dit quoi", "tu m'as dit quoi"),
    ("tu ma manquer", "tu m'as manqué"),
    ("il ma rien dit", "il m'a rien dit"),
    ("tu à raison", "tu as raison"),
    ("mon ami et venu me voir", "mon ami est venu me voir"),
    ("quand a moi je viens", "quant à moi je viens"),
    ("ils leurs ont dit merci", "ils leur ont dit merci"),
    ("a demain les gars", "à demain les gars"),
    ("a plus tard", "à plus tard"),
    ("j'ai quelque chose a te dire", "j'ai quelque chose à te dire"),
    ("c'est pas sa", "c'est pas ça"),
    ("on m'a dit que sa marchait pas", "on m'a dit que ça marchait pas"),
    ("on peut ce voir demain", "on peut se voir demain"),
    ("il ces passé quoi", "il s'est passé quoi"),
    ("il est pres de la", "il est près de là"),
    # accords et conjugaisons
    ("mes parent son la", "mes parents sont là"),
    ("elle est très joli", "elle est très jolie"),
    ("nous avont fini", "nous avons fini"),
    ("vous faite quoi", "vous faites quoi"),
    ("je voudrai un café", "je voudrais un café"),
    ("il a dit quil viendrai", "il a dit qu'il viendrait"),
    ("je te le dit demain", "je te le dis demain"),
    # un mot inacheve n'est pas un nom propre
    ("bonne anné", "bonne année"),
])
def test_la_faute_est_corrigee(correcteur, fautif, attendu):
    assert correcteur.corriger(fautif)[0] == attendu


@pytest.mark.parametrize("phrase", [
    "le onze novembre",
    "de ouf ce jeu",
    "un homme et une femme",
    "le hibou dort",
    "elle était là hier",
    "ce mec la voit de loin",
    "quand je voudrai un café je le dirai",
    "il a dit qu'il viendra demain",
    "il est parti et venu",
    "tu m'as dit que oui",
    "je t'ai dit non",
    "quant à moi je reste",
    "quand il a dit ça",
    "ma voiture est là",
    "il a ma voiture",
    "c'est la vie",
    "il y a beaucoup à faire",
    "elle est très jolie",
    "ils sont très bizarres",
    "a-t-il le temps",
    "il se voit dans la glace",
    "pour ce faire il faut attendre",
    "je la vois",
    "les gens la regardent",
    "il vous dit merci",
    "ça vous fait mal",
])
def test_la_phrase_juste_reste_intacte(correcteur, phrase):
    assert correcteur.corriger(phrase)[0] == phrase


def test_un_mot_accentue_ne_perd_pas_ses_accents(correcteur):
    """« anné » a un accent : le corriger en « Anne » le lui retirerait."""
    assert correcteur.lexique.suggestion("anné") != "Anne"
