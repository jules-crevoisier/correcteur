# -*- coding: utf-8 -*-
"""La correction au fil de la frappe, jugee sur ce qui arrive vraiment a l'ecran.

Une regle qui regarde le mot suivant ne peut pas trancher quand ce mot n'est
pas encore ecrit : « c'est la » attend « vie ». Elle se prononcait pourtant,
et la phrase sortait « c'est là vie ». Ces tests tapent des phrases justes,
lettre a lettre, et exigent qu'elles sortent intactes.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote.frappe import Frappe  # noqa: E402


def taper(correcteur, texte: str) -> str:
    """Ce qui reste a l'ecran une fois `texte` tape, corrections comprises."""
    frappe = Frappe(correcteur)
    ecran = ""
    for caractere in texte:
        remplacement = frappe.caractere(caractere)
        if remplacement is None:
            ecran += caractere
        else:
            # `effacer` compte le separateur, qui n'est pas encore a l'ecran.
            ecran = ecran[:len(ecran) - (remplacement.effacer - 1)]
            ecran += remplacement.ecrire
    return ecran


@pytest.mark.parametrize("phrase", [
    "c'est la vie",
    "c'est la fin de tout ça",
    "il est la preuve que ça marche",
    "elle est la meilleure de la classe",
    "Tous les jours c'est la même chose",
    "elle s'est lavé les cheveux",
    "elle s'est cassé la jambe",
    "des yeux bleu foncé",
])
def test_une_phrase_juste_sort_intacte(correcteur, phrase):
    assert taper(correcteur, phrase + " puis") == phrase + " puis"
    assert taper(correcteur, phrase + ".") == phrase + "."


@pytest.mark.parametrize("fautif,attendu", [
    ("je suis la.", "je suis là."),
    ("mon frere est la, viens", "mon frère est là, viens"),
    ("il à mangé du pain.", "il a mangé du pain."),
    ("les enfant sont la.", "les enfants sont là."),
])
def test_la_faute_est_corrigee_des_que_le_membre_est_clos(correcteur, fautif,
                                                          attendu):
    assert taper(correcteur, fautif) == attendu


def test_une_espace_ne_suffit_pas_a_trancher_sur_le_dernier_mot(correcteur):
    frappe = Frappe(correcteur)
    remplacements = [frappe.caractere(c) for c in "je suis la "]
    assert not any(remplacements)


def test_le_correcteur_ecarte_ce_qui_depend_d_un_mot_absent(correcteur):
    assert correcteur.corriger("c'est la", fin_ouverte=True)[0] == "c'est la"
    assert correcteur.corriger("c'est la")[0] == "c'est là"
