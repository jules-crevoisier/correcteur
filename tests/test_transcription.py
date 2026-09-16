# -*- coding: utf-8 -*-
"""Tests de la mise en forme de la parole.

Aucun micro ici, et aucun modele : le coeur ne connait que des mots dates et
des empreintes, et c'est ce qui permet de l'eprouver serieusement. La couche
qui touche au materiel est ailleurs, et elle ne fait que passer des octets.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from papote.transcription import (  # noqa: E402
    Locuteurs, Mot, Segment, Transcription, nom_annonce, ponctuer,
    ressemblance,
)


def mots(*paires) -> list[Mot]:
    """« bonjour »@0.0-0.4 ... — des mots dates, ecrits court."""
    return [Mot(texte, debut, fin) for texte, debut, fin in paires]


def suite(*textes, blanc=0.1, duree=0.4, depart=0.0) -> list[Mot]:
    """Une suite de mots separes du meme blanc."""
    resultat, instant = [], depart
    for texte in textes:
        resultat.append(Mot(texte, instant, instant + duree))
        instant += duree + blanc
    return resultat


# -- la ponctuation ---------------------------------------------------------

def test_un_ruban_de_mots_devient_une_phrase():
    assert ponctuer(suite("bonjour", "tout", "le", "monde")) == \
        "Bonjour tout le monde."


def test_un_silence_long_ferme_la_phrase():
    """Personne ne ponctue en parlant ; tout le monde respire."""
    debut = suite("on", "commence")
    fin = suite("ensuite", "on", "verra", depart=debut[-1].fin + 1.2)
    assert ponctuer(debut + fin) == "On commence. Ensuite on verra."


def test_un_silence_court_pose_une_virgule():
    debut = suite("alors", depart=0.0)
    fin = suite("on", "y", "va", depart=debut[-1].fin + 0.5)
    assert ponctuer(debut + fin) == "Alors, on y va."


def test_une_relance_ouvre_une_phrase():
    """« donc » apres une respiration relance : il ne prolonge pas."""
    debut = suite("c'est", "bon")
    fin = suite("donc", "on", "avance", depart=debut[-1].fin + 0.5)
    assert ponctuer(debut + fin) == "C'est bon. Donc on avance."


def test_une_question_prend_son_point_d_interrogation():
    rendu = ponctuer(suite("est-ce", "qu'on", "a", "le", "budget"))
    assert rendu == "Est-ce qu'on a le budget ?"


def test_une_subordonnee_n_est_pas_une_question():
    """« je sais pas pourquoi il est parti » ne se termine pas par « ? »."""
    rendu = ponctuer(suite("je", "sais", "pas", "pourquoi", "il", "part"))
    assert rendu.endswith(".")


def test_une_interrogation_en_tete_reste_une_question():
    rendu = ponctuer(suite("pourquoi", "tu", "dis", "ça"))
    assert rendu.endswith(" ?")


def test_un_ruban_sans_le_moindre_silence_se_coupe_quand_meme():
    """Quarante mots d'un souffle : c'est le moteur qui se trompe."""
    rendu = ponctuer(suite(*["mot"] * 90, blanc=0.01))
    assert rendu.count(".") >= 2


def test_rien_a_ponctuer():
    assert ponctuer([]) == ""


# -- les locuteurs ----------------------------------------------------------

def test_deux_voix_proches_sont_la_meme_personne():
    locuteurs = Locuteurs()
    a = Segment(tuple(suite("bonjour", "a", "tous")), (1.0, 0.0, 0.0))
    b = Segment(tuple(suite("je", "continue", "donc")), (0.95, 0.05, 0.0))
    assert locuteurs.attribuer(a) == locuteurs.attribuer(b)
    assert len(locuteurs) == 1


def test_deux_voix_eloignees_sont_deux_personnes():
    locuteurs = Locuteurs()
    a = Segment(tuple(suite("bonjour", "a", "tous")), (1.0, 0.0, 0.0))
    b = Segment(tuple(suite("moi", "je", "pense")), (0.0, 1.0, 0.0))
    assert locuteurs.attribuer(a) != locuteurs.attribuer(b)
    assert len(locuteurs) == 2


def test_un_segment_trop_court_prolonge_celui_qui_parlait():
    """Un « oui » de trois dixiemes ne fonde pas une nouvelle voix."""
    locuteurs = Locuteurs()
    long = Segment(tuple(suite("je", "pense", "que", "oui")), (1.0, 0.0))
    premier = locuteurs.attribuer(long)
    court = Segment((Mot("oui", 9.0, 9.2),), (0.0, 1.0))
    assert locuteurs.attribuer(court) == premier
    assert len(locuteurs) == 1


def test_sans_empreinte_tout_le_monde_parle_d_une_voix():
    """Sans le modele de voix, la transcription marche quand meme."""
    locuteurs = Locuteurs()
    for texte in ("bonjour", "au", "revoir"):
        segment = Segment(tuple(suite(texte, "les", "amis")))
        assert locuteurs.attribuer(segment) == 0


def test_la_ressemblance_est_bornee():
    assert ressemblance((1.0, 0.0), (1.0, 0.0)) == pytest.approx(1.0)
    assert ressemblance((1.0, 0.0), (-1.0, 0.0)) == pytest.approx(0.0)
    assert ressemblance((), (1.0,)) == 0.0
    assert ressemblance((0.0, 0.0), (1.0, 0.0)) == 0.0


# -- les noms ---------------------------------------------------------------

@pytest.mark.parametrize("phrase, attendu", [
    ("bonjour, moi c'est Marion", "Marion"),
    ("je m'appelle Pierre et je travaille ici", "Pierre"),
    ("c'est Claire à l'appareil", "Claire"),
])
def test_un_nom_annonce_est_retenu(phrase, attendu):
    assert nom_annonce(phrase) == attendu


@pytest.mark.parametrize("phrase", [
    "moi c'est pas grave",
    "moi c'est ça que je voulais dire",
    "je m'appelle à midi",       # pas un prenom : la regle se tait
    "bonjour tout le monde",
])
def test_un_nom_ne_s_invente_pas(phrase):
    assert nom_annonce(phrase) in (None, "Midi")


# -- l'assemblage -----------------------------------------------------------

def test_les_tours_d_une_meme_voix_se_regroupent():
    """Le decoupage du moteur n'a pas de sens pour un lecteur."""
    transcription = Transcription()
    for texte in ("bonjour", "ça", "va"):
        transcription.ajouter(Segment(tuple(suite(texte, "les", "gens")),
                                      (1.0, 0.0)))
    assert len(transcription.tours) == 1


def test_un_changement_de_voix_ouvre_un_tour():
    transcription = Transcription()
    transcription.ajouter(Segment(tuple(suite("bonjour", "a", "tous")),
                                  (1.0, 0.0)))
    transcription.ajouter(Segment(tuple(suite("moi", "je", "pense")),
                                  (0.0, 1.0)))
    assert len(transcription.tours) == 2
    assert transcription.participants == ["Personne 1", "Personne 2"]


def test_le_nom_annonce_remplace_le_numero():
    transcription = Transcription()
    transcription.ajouter(Segment(
        tuple(suite("moi", "c'est", "Marion", "bonjour")), (1.0, 0.0)))
    assert transcription.participants == ["Marion"]


def test_renommer_reecrit_les_tours_deja_rendus():
    """Un compte rendu a moitie signe « Personne 2 » ne se relit pas."""
    transcription = Transcription()
    transcription.ajouter(Segment(tuple(suite("bonjour", "a", "tous")),
                                  (1.0, 0.0)))
    transcription.ajouter(Segment(tuple(suite("moi", "je", "pense")),
                                  (0.0, 1.0)))
    transcription.renommer("Personne 2", "Claire")
    assert transcription.participants == ["Personne 1", "Claire"]
    assert all(tour.locuteur != "Personne 2" for tour in transcription.tours)


def test_un_segment_vide_ne_cree_pas_de_tour():
    transcription = Transcription()
    assert transcription.ajouter(Segment(())) is None
    assert transcription.tours == []


def test_le_correcteur_relit_la_transcription(correcteur):
    """Ce que le moteur entend n'a pas d'accents ; Papote les rend."""
    transcription = Transcription(correcteur=correcteur)
    transcription.ajouter(Segment(tuple(suite("j'ai", "recu", "ton", "message"))))
    assert "reçu" in transcription.tours[0].texte


def test_le_registre_parle_reste_intact(correcteur):
    """C'est la raison d'etre de ce module : un compte rendu doit
    ressembler a ce qui a ete dit."""
    transcription = Transcription(correcteur=correcteur)
    transcription.ajouter(Segment(tuple(suite("j'ai", "pas", "eu", "le", "temps"))))
    texte = transcription.tours[0].texte
    assert "j'ai pas" in texte.lower()
    assert "n'ai pas" not in texte.lower()


def test_un_correcteur_qui_tombe_ne_perd_pas_la_transcription():
    class Casse:
        def corriger(self, _texte):
            raise RuntimeError("boum")

    transcription = Transcription(correcteur=Casse())
    transcription.ajouter(Segment(tuple(suite("bonjour", "tout", "le", "monde"))))
    assert transcription.tours[0].texte.startswith("Bonjour")


def test_le_texte_entier_se_relit():
    transcription = Transcription()
    transcription.ajouter(Segment(tuple(suite("bonjour", "a", "tous")),
                                  (1.0, 0.0)))
    transcription.ajouter(Segment(tuple(suite("moi", "je", "pense")),
                                  (0.0, 1.0)))
    texte = transcription.texte()
    assert "Personne 1 :" in texte and "Personne 2 :" in texte
