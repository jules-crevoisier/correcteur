# -*- coding: utf-8 -*-
"""Tests du moteur, avec un LanguageTool simule.

Simuler l'outil permet de verifier la logique de filtrage — la partie qu'on
ecrit vraiment — sans dependre d'un serveur Java ni du reseau.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from correcteur.moteur import Correcteur, _changement_cosmetique  # noqa: E402


@dataclass
class FauxMatch:
    offset: int
    error_length: int
    replacements: list
    rule_id: str = "REGLE_TEST"
    category: str = "CAT_GRAMMAIRE"
    message: str = ""


@dataclass
class FauxOutil:
    """Renvoie les suggestions programmees pour chaque texte exact."""

    reponses: dict = field(default_factory=dict)
    mots_connus: set = field(default_factory=set)

    def check(self, texte):
        # Un mot isole : le moteur teste sa validite lexicale.
        if texte in self.reponses:
            return self.reponses[texte]
        if " " not in texte.strip() and texte.strip():
            if texte.lower() in self.mots_connus:
                return []
            return [FauxMatch(0, len(texte), ["?"], "FR_SPELLING_RULE", "TYPOS")]
        return []


def outil(texte, debut, longueur, remplacements, regle="REGLE_TEST",
          categorie="CAT_GRAMMAIRE", mots_connus=()):
    return FauxOutil(
        reponses={texte: [FauxMatch(debut, longueur, list(remplacements), regle, categorie)]},
        mots_connus=set(mots_connus),
    )


# -- respect du registre ----------------------------------------------------

def test_la_negation_orale_est_preservee():
    """« j'ai pas » ne doit jamais devenir « je n'ai pas » (regle P_V_PAS)."""
    texte = "j'ai pas compris"
    c = Correcteur(outil(texte, 0, 4, ["je n'ai"], "P_V_PAS"))
    assert c.corriger(texte) == (texte, [])


def test_les_categories_de_registre_sont_ecartees():
    texte = "y a personne"
    c = Correcteur(outil(texte, 0, 3, ["il n'y a"], "AUTRE", "CAT_TOURS_CRITIQUES"))
    assert c.corriger(texte)[0] == texte


@pytest.mark.parametrize("regle", ["IL_FAUT", "NE_IMP_PAS", "CA_CE", "DISPO"])
def test_regles_de_registre_individuelles(regle):
    texte = "faut y aller"
    c = Correcteur(outil(texte, 0, 4, ["il faut"], regle))
    assert c.corriger(texte)[0] == texte


# -- ce que l'utilisateur a ecrit expres ------------------------------------

def test_largot_internet_est_protege():
    """« dsl » ne doit pas devenir « ADSL »."""
    texte = "dsl je peux pas"
    c = Correcteur(outil(texte, 0, 3, ["ADSL"], "FR_SPELLING_RULE", "TYPOS"))
    assert c.corriger(texte)[0] == texte


def test_lemphase_est_preservee():
    """« mdrrrr » est volontaire, pas une faute de frappe."""
    texte = "mdrrrr trop fort"
    c = Correcteur(outil(texte, 0, 6, ["Marrer"], "FR_SPELLING_RULE", "TYPOS"))
    assert c.corriger(texte)[0] == texte


@pytest.mark.parametrize("texte,debut,longueur", [
    ("va sur https://exemple.fr/truc", 7, 22),
    ("salut <@123456789> ca va", 6, 12),
    ("tape `git comit` pour voir", 5, 11),
    ("regarde #general stp", 8, 8),
])
def test_les_zones_protegees_sont_intactes(texte, debut, longueur):
    """Liens, mentions, code : jamais touches."""
    c = Correcteur(outil(texte, debut, longueur, ["REMPLACE"], "FR_SPELLING_RULE", "TYPOS"))
    assert c.corriger(texte)[0] == texte


# -- corrections legitimes --------------------------------------------------

def test_accent_applique():
    texte = "sa va marcher"
    c = Correcteur(outil(texte, 0, 2, ["ça"], "SA_CA_SE",
                         "CAT_HOMONYMES_PARONYMES", mots_connus={"ça"}))
    corrige, corrections = c.corriger(texte)
    assert corrige == "ça va marcher"
    assert len(corrections) == 1
    assert str(corrections[0]) == "sa → ça"


def test_apostrophe_appliquee():
    texte = "il ma dit"
    c = Correcteur(outil(texte, 3, 6, ["m'a dit"], "MA", "CAT_HOMONYMES_PARONYMES"))
    assert c.corriger(texte)[0] == "il m'a dit"


def test_accord_en_suffixe_applique():
    texte = "elles sont venu"
    c = Correcteur(outil(texte, 11, 4, ["venues"], "ETRE_VPPA_OU_ADJ",
                         mots_connus={"venues"}))
    assert c.corriger(texte)[0] == "elles sont venues"


# -- garde-fous anti-degradation -------------------------------------------

def test_un_mot_inexistant_est_refuse():
    """LanguageTool propose parfois « mangait », qui n'existe pas."""
    texte = "ils ont mangé"
    c = Correcteur(outil(texte, 8, 5, ["mangait"], "ACCORD_R_PERS_VERBE",
                         mots_connus={"mangeait"}))
    assert c.corriger(texte)[0] == texte


def test_un_mot_existant_est_accepte():
    texte = "tu peut venir"
    c = Correcteur(outil(texte, 3, 4, ["peux"], "ACCORD_R_PERS_VERBE",
                         mots_connus={"peux"}))
    assert c.corriger(texte)[0] == "tu peux venir"


def test_le_redecoupage_en_mots_est_refuse():
    """« ceter » -> « ce ter » couperait un mot en deux."""
    texte = "sa ceter bien"
    c = Correcteur(outil(texte, 3, 5, ["ce ter"], "FR_SPELLING_RULE", "TYPOS"))
    assert c.corriger(texte)[0] == texte


def test_la_reecriture_multi_mots_est_refusee():
    """« ta fini » -> « te finir » change les deux mots : trop risque."""
    texte = "quand ta fini stp"
    c = Correcteur(outil(texte, 6, 7, ["te finir"], "MA", "CAT_HOMONYMES_PARONYMES"))
    assert c.corriger(texte)[0] == texte


def test_un_mot_insere_est_refuse():
    """« raison » -> « a raison » ajoute un mot que l'auteur n'a pas ecrit."""
    texte = "il raison"
    c = Correcteur(outil(texte, 3, 6, ["a raison"], "PRONSUJ_NONVERBE"))
    assert c.corriger(texte)[0] == texte


def test_un_remplacement_vide_est_refuse():
    texte = "un test ici"
    c = Correcteur(outil(texte, 3, 4, ["  "], "FR_SPELLING_RULE", "TYPOS"))
    assert c.corriger(texte)[0] == texte


# -- le test du changement cosmetique --------------------------------------

@pytest.mark.parametrize("avant,apres", [
    ("ma dit", "m'a dit"),       # apostrophe ajoutee
    ("a finir", "à finir"),      # accent ajoute
    ("Est ce", "Est-ce"),        # trait d'union
    ("nimporte", "n'importe"),   # apostrophe interne
    ("nous somme", "nous sommes"),   # terminaison d'accord
    ("sont chelou", "sont chelous"),
])
def test_changements_cosmetiques_acceptes(avant, apres):
    assert _changement_cosmetique(avant, apres)


@pytest.mark.parametrize("avant,apres", [
    ("ta fini", "te finir"),
    ("les enfant", "l'enfant"),
    ("des chose", "de la chose"),
    ("ma envoyer", "me envoyer"),
    ("ceter", "ce ter"),
    ("raison", "a raison"),
])
def test_changements_risques_refuses(avant, apres):
    assert not _changement_cosmetique(avant, apres)


# -- integrite du texte -----------------------------------------------------

def test_texte_vide():
    c = Correcteur(FauxOutil())
    assert c.corriger("") == ("", [])
    assert c.corriger("   ") == ("   ", [])


def test_les_espaces_de_bord_sont_conserves():
    """Au collage, un espace perdu colle deux mots l'un a l'autre."""
    texte = "  sa va  "
    c = Correcteur(outil(texte.strip(), 0, 2, ["ça"], "SA_CA_SE",
                         "CAT_HOMONYMES_PARONYMES", mots_connus={"ça"}))
    assert c.corriger(texte)[0] == "  ça va  "


def test_corrections_multiples_les_positions_restent_justes():
    """Plusieurs corrections dans une phrase ne doivent pas se decaler."""
    texte = "sa et sa"
    outil_multi = FauxOutil(reponses={
        texte: [
            FauxMatch(0, 2, ["ça"], "SA_CA_SE", "CAT_HOMONYMES_PARONYMES"),
            FauxMatch(6, 2, ["ça"], "SA_CA_SE", "CAT_HOMONYMES_PARONYMES"),
        ],
    }, mots_connus={"ça"})
    corrige, corrections = Correcteur(outil_multi).corriger(texte, passes=1)
    assert corrige == "ça et ça"
    assert len(corrections) == 2


def test_les_suggestions_qui_se_chevauchent_ne_sappliquent_quune_fois():
    texte = "sa va"
    outil_chevauchant = FauxOutil(reponses={
        texte: [
            FauxMatch(0, 2, ["ça"], "SA_CA_SE", "CAT_HOMONYMES_PARONYMES"),
            FauxMatch(0, 5, ["ça va"], "AUTRE", "CAT_GRAMMAIRE"),
        ],
    }, mots_connus={"ça"})
    corrige, corrections = Correcteur(outil_chevauchant).corriger(texte, passes=1)
    assert corrige == "ça va"
    assert len(corrections) == 1


def test_regle_optionnelle_desactivee_par_defaut():
    texte = "salut ca va"
    c = Correcteur(outil(texte, 0, 5, ["Salut"], "UPPERCASE_SENTENCE_START", "CASING"))
    assert c.corriger(texte)[0] == texte


def test_regle_optionnelle_reactivable():
    texte = "salut ca va"
    c = Correcteur(
        outil(texte, 0, 5, ["Salut"], "UPPERCASE_SENTENCE_START", "CASING"),
        regles_optionnelles={"UPPERCASE_SENTENCE_START": True},
    )
    assert c.corriger(texte)[0] == "Salut ca va"
