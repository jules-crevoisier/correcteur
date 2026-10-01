# -*- coding: utf-8 -*-
"""Le modele statistique : son format, sa lecture du contexte, ses gardes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from papote import statistique as st  # noqa: E402
from papote.grammaire_suite import modele_statistique  # noqa: E402


def test_le_format_se_relit(tmp_path):
    chemin = tmp_path / "m.bin.gz"
    table = {st.empreinte("G1", "va\x1fà"): 120, st.empreinte("G1", "va\x1fa"): 3}
    st.Modele.ecrire(chemin, table)
    modele = st.Modele.charger(chemin)
    assert len(modele) == 2
    assert modele.compte("G1", "va\x1fà") == 120
    assert modele.compte("G1", "va\x1finconnu") == 0


def test_un_fichier_etranger_est_refuse(tmp_path):
    import gzip
    chemin = tmp_path / "faux.bin.gz"
    with gzip.open(chemin, "wb") as f:
        f.write(b"autre chose")
    assert st.Modele.charger(chemin) is None
    assert st.Modele.charger(tmp_path / "absent.bin.gz") is None


def test_la_ponctuation_fait_partie_du_contexte():
    suite, place = st.sequence(["tu", "vas", "où"], [" ", " ", " ?"])
    assert suite == ["<s>", "tu", "vas", "où", ".", "</s>"]
    assert place == [1, 2, 3]


def test_un_homophone_n_appartient_qu_a_un_ensemble():
    vus = set()
    for ensemble in st.HOMOPHONES:
        assert not (vus & ensemble), ensemble
        vus |= ensemble


def test_les_verbes_en_e_partagent_leur_classe(correcteur):
    morphologie = correcteur.morphologie
    assert st.classe_verbale(morphologie, "manger") == (st.INF, "manger")
    assert st.classe_verbale(morphologie, "mangé") == (st.PP, "manger")
    # Un nom n'est pas une forme verbale : « le marché », « une entrée ».
    assert st.classe_verbale(morphologie, "marché") is None
    assert st.forme_de_classe(morphologie, "manger", st.PP) == "mangé"


requiert_le_modele = pytest.mark.skipif(
    modele_statistique() is None, reason="modele statistique absent")


@requiert_le_modele
@pytest.mark.parametrize("fautif,attendu", [
    ("on va a la plage demain", "on va à la plage demain"),
    ("tu as vu se film ?", "tu as vu ce film ?"),
    ("il faut aller le chercher a la gare", "il faut aller le chercher à la gare"),
])
def test_le_modele_tranche(correcteur, fautif, attendu):
    assert correcteur.corriger(fautif)[0] == attendu


@requiert_le_modele
@pytest.mark.parametrize("phrase", [
    "Paul a la clé de la maison.",
    "Chaque photo a son histoire.",
    "Qui se ressemble s'assemble.",
    "Il a existé ou il existe encore.",
    "Gardez la honte, mais supportez-la.",
    "Mets la bouilloire à chauffer.",
    "La querelle et le repentir sont frère et sœur.",
    "Des objets connectés et lancés en 2020.",
    "Si a existe, alors b existe.",
])
def test_le_modele_se_tait_quand_la_grammaire_le_contredit(correcteur, phrase):
    assert correcteur.corriger(phrase)[0] == phrase


@requiert_le_modele
def test_le_modele_attend_que_son_voisinage_soit_propre(correcteur):
    """« mes meilleur amis » : « meilleur » est corrige, « mes » reste."""
    assert correcteur.corriger("mes meilleur amis")[0] == "mes meilleurs amis"
