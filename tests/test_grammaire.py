# -*- coding: utf-8 -*-
"""Tests des regles de grammaire, une par une.

Chaque regle est jugee sur deux exemples : la faute qu'elle doit corriger, et
la phrase correcte voisine qu'elle ne doit surtout pas toucher.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import grammaire  # noqa: E402


# (texte fautif, texte attendu, nom de la regle)
CORRIGES = [
    ("je sais pas si sa va", "je sais pas si ça va", "SA_CA"),
    ("ca ma pris deux heures", "ça m'a pris deux heures", "APOSTROPHE_AVANT_PARTICIPE"),
    ("tas vu le film", "t'as vu le film", "APOSTROPHE_AVANT_PARTICIPE"),
    ("il me la dit hier", "il me l'a dit hier", "APOSTROPHE_AVANT_PARTICIPE"),
    ("il à mangé", "il a mangé", "IL_A"),
    ("je vais a la gare", "je vais à la gare", "A_ACCENT"),
    ("elle et contente", "elle est contente", "ET_EST"),
    ("ils on mangé", "ils ont mangé", "ILS_ONT"),
    ("elles son parties", "elles sont parties", "ILS_SONT"),
    ("je sais pas se que tu veux", "je sais pas ce que tu veux", "SE_CE"),
    ("il ce lave", "il se lave", "CE_SE"),
    ("s'est pas grave", "c'est pas grave", "S_EST_C_EST"),
    ("tu sais ou est mon sac", "tu sais où est mon sac", "OU_ACCENT"),
    ("je suis la", "je suis là", "LA_ACCENT"),
    ("je suis la bas", "je suis là-bas", "LA_ACCENT"),
    ("tout les jours", "tous les jours", "TOUT_TOUS"),
    ("mes je peux pas", "mais je peux pas", "MES_MAIS"),
    ("un peut plus tard", "un peu plus tard", "PEUT_PEU"),
    ("est ce que tu viens", "est-ce que tu viens", "EST_CE"),
    ("j'ai manger des frites", "j'ai mangé des frites", "PARTICIPE_APRES_AUXILIAIRE"),
    ("je vais mangé", "je vais manger", "INFINITIF_APRES_SEMI_AUXILIAIRE"),
    ("elles sont venu hier", "elles sont venues hier", "ACCORD_PARTICIPE_ETRE"),
    ("des enfant", "des enfants", "ACCORD_DETERMINANT_NOM"),
    ("je peut pas", "je peux pas", "ACCORD_SUJET_VERBE"),
    ("je croit pas", "je crois pas", "ACCORD_JE_TU_S"),
    ("tu mange quoi", "tu manges quoi", "ACCORD_TU_S"),
    ("ils mange trop", "ils mangent trop", "ACCORD_ILS_ENT"),
]

# Phrases correctes que les regles ci-dessus pourraient abimer.
INTOUCHABLES = [
    "sa mère est venue",              # « sa » possessif
    "un tas de trucs",                # « tas » nom commun
    "il a la flemme",                 # « a » verbe avoir
    "lui et elle sont partis",        # vraie coordination
    "on mange à midi",                # « on » pronom
    "son frère arrive",               # « son » possessif
    "ils se sont levés",              # « se » pronominal
    "ce que je veux",                 # « ce » demonstratif
    "il s'est levé tôt",              # « s'est » correct
    "du pain ou du fromage",          # « ou » conjonction
    "la maison est grande",           # « la » article
    "tout le monde est là",           # « tout » singulier
    "mes amis sont là",               # « mes » possessif
    "il peut venir demain",           # « peut » verbe
    "j'ai été manger dehors",         # infinitif apres « été »
    "je vais au café",                # « café » n'est pas un participe
    "je les mange",                   # « les » pronom, pas determinant
    "elle est venue",                 # accord deja fait
    "il est content",                 # rien a accorder
]


def corriger(correcteur, texte):
    return correcteur.corriger(texte)[0]


@pytest.mark.parametrize("texte,attendu,regle", CORRIGES)
def test_la_regle_corrige(correcteur, texte, attendu, regle):
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == attendu
    assert regle in {c.regle for c in corrections}


@pytest.mark.parametrize("texte", INTOUCHABLES)
def test_les_phrases_correctes_sont_intactes(correcteur, texte):
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == texte, f"corrections indues : {[str(c) for c in corrections]}"


# -- decoupage --------------------------------------------------------------

def test_le_decoupage_garde_les_apostrophes():
    jetons = [j.texte for j in grammaire.decouper("j'ai vu aujourd'hui qu'il partait")]
    assert jetons == ["j'ai", "vu", "aujourd'hui", "qu'il", "partait"]


def test_le_decoupage_separe_les_traits_d_union():
    jetons = [j.texte for j in grammaire.decouper("est-ce que peut-être")]
    assert jetons == ["est", "ce", "que", "peut", "être"]


@pytest.mark.parametrize("mot,elision,noyau", [
    ("c'est", "c'", "est"),
    ("j'ai", "j'", "ai"),
    ("qu'il", "qu'", "il"),
    ("aujourd'hui", "", "aujourd'hui"),
    ("bonjour", "", "bonjour"),
])
def test_separation_des_elisions(mot, elision, noyau):
    assert grammaire.separer_clitique(mot) == (elision, noyau)
