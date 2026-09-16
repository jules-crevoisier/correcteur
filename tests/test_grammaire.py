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
    ("ils mange trop", "ils mangent trop", "ACCORD_PRONOM_VERBE"),
    ("ils vient demain", "ils viennent demain", "ACCORD_PRONOM_VERBE"),
    ("les gens finit tard", "les gens finissent tard", "ACCORD_SUJET_NOMINAL"),
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


# -- le registre soutenu -----------------------------------------------------

SOUTENUS = [
    ("j'ai pas compris", "Je n'ai pas compris."),
    ("il peut pas venir", "Il ne peut pas venir."),
    ("on a pas le temps", "On n'a pas le temps."),
    ("t'as pas vu", "Tu n'as pas vu."),
    ("c'est pas grave", "Ce n'est pas grave."),
    ("y a personne", "Il n'y a personne."),
    ("faut pas exagérer", "Il ne faut pas exagérer."),
    ("il me l'a pas dit", "Il ne me l'a pas dit."),
    ("ça marche", "Cela marche."),
    ("dsl bcp de travail", "Désolé beaucoup de travail."),
]


@pytest.fixture(scope="module")
def correcteur_soutenu(request):
    from papote.moteur import Correcteur
    from papote.politique import SOUTENU

    return Correcteur(request.getfixturevalue("lexique"), registre=SOUTENU)


@pytest.mark.parametrize("texte,attendu", SOUTENUS)
def test_le_registre_soutenu_releve_le_ton(correcteur_soutenu, texte, attendu):
    assert correcteur_soutenu.corriger(texte)[0] == attendu


@pytest.mark.parametrize("texte,_attendu", SOUTENUS)
def test_le_registre_parle_ne_touche_a_rien(correcteur, texte, _attendu):
    """Par defaut, aucune de ces phrases ne doit bouger d'un iota."""
    corrige, corrections = correcteur.corriger(texte)
    assert corrige == texte, f"corrections indues : {[str(c) for c in corrections]}"


def test_le_soutenu_ne_nie_pas_deux_fois(correcteur_soutenu):
    texte = "il n'a pas compris."
    assert correcteur_soutenu.corriger(texte)[0] == "Il n'a pas compris."


def test_le_soutenu_ne_confond_pas_ne_que_et_que(correcteur_soutenu):
    """« faut que j'y aille » n'est pas une negation."""
    assert correcteur_soutenu.corriger("faut que j'y aille")[0] \
        == "Il faut que j'y aille."


def test_ca_va_reste_ca_va(correcteur_soutenu):
    """Personne n'ecrit « cela va ? »."""
    assert correcteur_soutenu.corriger("ça va ?")[0] == "Ça va ?"


# -- les mots justes qui en cachent un autre --------------------------------

def test_un_mot_reel_mais_improbable_est_corrige(correcteur):
    """« commet » est le verbe commettre — mais pas en tête de phrase."""
    assert correcteur.corriger("commet ça va")[0] == "comment ça va"


def test_le_meme_mot_reste_quand_il_est_a_sa_place(correcteur):
    assert correcteur.corriger("il commet une erreur")[0] == "il commet une erreur"


def test_un_mot_rare_ne_masque_plus_la_faute(correcteur):
    """« sui » est au dictionnaire ; « je sui » n'en reste pas moins faux."""
    assert correcteur.corriger("je sui en route")[0] == "je suis en route"
    assert correcteur.corriger("il fau qu'on parle")[0] == "il faut qu'on parle"


def test_l_elision_ne_cache_pas_l_auxiliaire(correcteur):
    """« j'ai » doit compter comme « ai » pour la condition qui le cherche."""
    assert correcteur.corriger("j'ai pri le bus")[0] == "j'ai pris le bus"


def test_un_nom_apres_determinant_reste_intact(correcteur):
    assert correcteur.corriger("le pri est correct")[0] == "le pri est correct"


# -- doublons ---------------------------------------------------------------

def test_un_mot_ecrit_deux_fois_est_reduit(correcteur):
    assert correcteur.corriger("je vais vais partir")[0] == "je vais partir"
    assert correcteur.corriger("c'est le le meilleur")[0] == "c'est le meilleur"


def test_les_doublons_legitimes_survivent(correcteur):
    """« nous nous levons » n'est pas une faute de frappe."""
    for phrase in ("nous nous levons tôt", "vous vous trompez",
                   "c'est très très bon", "il se se"):
        assert "  " not in correcteur.corriger(phrase)[0]
    assert correcteur.corriger("nous nous levons tôt")[0] == "nous nous levons tôt"
    assert correcteur.corriger("vous vous trompez")[0] == "vous vous trompez"


def test_une_ponctuation_entre_les_deux_protege_la_repetition(correcteur):
    """« bon, bon » est une insistance, pas une faute."""
    assert correcteur.corriger("bon, bon")[0] == "bon, bon"


# -- traits d'union ---------------------------------------------------------

@pytest.mark.parametrize("faute,attendu", [
    ("on prend rendez vous quand", "on prend rendez-vous quand"),
    ("peut etre que oui", "peut-être que oui"),
    ("c'est a dire quoi", "c'est-à-dire quoi"),
    ("qu'est ce que tu fais", "qu'est-ce que tu fais"),
    ("au dessus de la porte", "au-dessus de la porte"),
    ("il est la bas", "il est là-bas"),
])
def test_les_composes_prennent_leur_trait_d_union(correcteur, faute, attendu):
    assert correcteur.corriger(faute)[0] == attendu


def test_le_verbe_pouvoir_garde_ses_deux_mots(correcteur):
    """« il peut être là » n'est pas « il peut-être là »."""
    assert correcteur.corriger("il peut être là")[0] == "il peut être là"


@pytest.mark.parametrize("faute,attendu", [
    ("dis moi tout", "dis-moi tout"),
    ("envoie moi le lien", "envoie-moi le lien"),
    ("vas y doucement", "vas-y doucement"),
])
def test_l_imperatif_et_son_pronom_se_lient(correcteur, faute, attendu):
    assert correcteur.corriger(faute)[0] == attendu


def test_un_sujet_devant_empeche_la_liaison(correcteur):
    """« je dis moi aussi » n'est pas un impératif."""
    assert correcteur.corriger("je dis moi aussi")[0] == "je dis moi aussi"


# -- l'accent oublie sur un mot qui existe quand meme ------------------------

@pytest.mark.parametrize("faute,attendu", [
    ("par pole ou pas", "par pôle ou pas"),
    ("la moitie des gens", "la moitié des gens"),
    ("le comite se réunit", "le comité se réunit"),
    ("voila le résultat", "voilà le résultat"),
    ("une foret dense", "une forêt dense"),
])
def test_un_mot_sans_accent_qui_en_cache_un_autre(correcteur, faute, attendu):
    """« pole » est au dictionnaire — c'est la « pole position »."""
    assert correcteur.corriger(faute)[0] == attendu


@pytest.mark.parametrize("phrase", [
    "il prive son fils de sortie",
    "tu cites un exemple",
    "on publie demain",
    "je le cite souvent",
    "il la prive de dessert",
])
def test_un_verbe_conjugue_garde_sa_graphie(correcteur, phrase):
    """« il prive » n'est pas « il privé » : un sujet devant, on ne touche pas."""
    assert correcteur.corriger(phrase)[0] == phrase


def test_deux_participes_qui_se_ressemblent_ne_se_tranchent_pas(correcteur):
    """« elles sont reparties » : elles sont parties de nouveau, on ne les a
    pas réparties."""
    assert "réparties" not in correcteur.corriger("elles sont reparties")[0]


def test_un_mot_a_plusieurs_accents_possibles_reste_intact(correcteur):
    """« cote » peut être « côte », « côté » ou « coté » : rien ne tranche."""
    assert correcteur.corriger("du cote de chez moi")[0] == "du cote de chez moi"


# -- un determinant singulier veut un nom singulier -------------------------

@pytest.mark.parametrize("faute,attendu", [
    ("au niveaux du serveur", "au niveau du serveur"),
    ("une choses à faire", "une chose à faire"),
])
def test_le_nom_suit_son_determinant(correcteur, faute, attendu):
    assert correcteur.corriger(faute)[0] == attendu


@pytest.mark.parametrize("phrase", [
    "le temps passe vite",
    "un pays lointain",
    "le prix est correct",
    "au niveau du serveur",
    "les niveaux sont hauts",
])
def test_les_noms_invariables_et_les_vrais_pluriels_survivent(correcteur,
                                                               phrase):
    assert correcteur.corriger(phrase)[0] == phrase


def test_un_pronom_avant_le_determinant_annule_la_regle(correcteur):
    """« elles son parties » : c'est « sont » qu'il fallait lire."""
    assert correcteur.corriger("elles son parties")[0] == "elles sont parties"


# ---------------------------------------------------------------------------
# Ce que la morphologie a ouvert
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("avant, apres", [
    # Tous les groupes, la ou seul le 1er etait conjugable.
    ("les gens finit tard", "les gens finissent tard"),
    ("les enfants dort déjà", "les enfants dorment déjà"),
    ("les gens prend le bus", "les gens prennent le bus"),
    ("ils vient demain", "ils viennent demain"),
    ("tu dort encore", "tu dors encore"),
    ("je part demain", "je pars demain"),
    ("il sortais hier", "il sortait hier"),
    # Le sujet n'est pas toujours colle a son verbe.
    ("beaucoup de gens pense ça", "beaucoup de gens pensent ça"),
    ("les gens qui pense ça", "les gens qui pensent ça"),
    # Les pluriels qu'aucune terminaison ne devine.
    ("les bijou brillent", "les bijoux brillent"),
    ("les cheval courent", "les chevaux courent"),
    ("un chevaux blanc", "un cheval blanc"),
    # Les feminins irreguliers, que « mot + e » ne trouvait pas.
    ("des chevaux blanc", "des chevaux blancs"),
    ("les yeux fermé", "les yeux fermés"),
    ("ils sont national", "ils sont nationaux"),
    # Le participe, cherche hors du temps du mot ecrit.
    ("ils ont prit le train", "ils ont pris le train"),
    ("elle a mit la table", "elle a mis la table"),
])
def test_la_morphologie_etend_les_accords(correcteur, avant, apres):
    assert correcteur.corriger(avant)[0] == apres


@pytest.mark.parametrize("phrase", [
    # « court » est un adjectif autant qu'un verbe, et les deux lectures
    # demandent des corrections opposees : « courts » ou « courent ».
    "les chiens court vite",
    # Ils finissent par « s » sans etre des pluriels : la terminaison le
    # croyait, le dictionnaire non.
    "le prix est correct",
    "la souris est cassée",
    "le temps passe vite",
    # « ce » commande un pluriel, contrairement aux autres pronoms sujets.
    "ce sont des choses qui arrivent",
    # Le sujet ne se limite pas au pronom qu'on voit.
    "lui et elle sont partis",
    # « restaurant » n'a pas de feminin : ce n'est pas un adjectif.
    "des tickets restaurant",
    # « les » y est un pronom complement, pas un determinant.
    "je les mange tous les jours",
    # Une quantite suivie d'un nom indenombrable reste au singulier.
    "beaucoup de monde est venu",
])
def test_la_morphologie_fait_taire_aussi(correcteur, phrase):
    assert correcteur.corriger(phrase)[0] == phrase


def test_le_genre_du_nom_guide_l_adjectif_quand_il_est_connu(correcteur):
    """Le dictionnaire connait le genre des noms a deux genres, et d'eux seuls."""
    assert correcteur.corriger("des chattes gentil")[0] == "des chattes gentilles"
    assert correcteur.corriger("des chats gentil")[0] == "des chats gentils"


def test_l_accord_reste_dans_le_temps(correcteur):
    """« les gens finit » est un present : sa 3e personne du pluriel aussi."""
    assert correcteur.corriger("les gens finit")[0] == "les gens finissent"
    assert correcteur.corriger("les gens pensait")[0] == "les gens pensaient"


# ---------------------------------------------------------------------------
# Les homophones dont les deux membres sont courants
#
# La table de `confusions.py` exige un ecart de frequence : elle ne peut rien
# pour « ou » / « où » ni « du » / « dû », aussi employes l'un que l'autre.
# Ceux-la demandent une regle, et une condition qui ne laisse pas de doute.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("avant, apres", [
    # « ou » relie deux choix : il lui faut quelque chose des deux cotes.
    ("tu vas ou", "tu vas où"),
    ("il est ou le fichier", "il est où le fichier"),
    ("je sais pas ou il est", "je sais pas où il est"),
    ("la ou on s'est vus", "là où on s'est vus"),
    ("ou est ce qu'on mange", "où est-ce qu'on mange"),
    # Un article ne precede jamais un infinitif.
    ("elle a du rentrer plus tot", "elle a dû rentrer plus tôt"),
    ("j'aurais du le faire avant", "j'aurais dû le faire avant"),
    # « sûr » se construit avec « de » ou « que » ; « sur » avec un lieu.
    ("je suis sur de moi", "je suis sûr de moi"),
    ("elle est sure de son coup", "elle est sûre de son coup"),
    ("bien sur que oui", "bien sûr que oui"),
    # Un adverbe ne gouverne pas d'infinitif.
    ("on peu passer ce soir", "on peut passer ce soir"),
    ("je peu pas venir", "je peux pas venir"),
    ("peu etre demain alors", "peut-être demain alors"),
    # « voire » est un adverbe : il ne suit pas un semi-auxiliaire.
    ("faut voire avec lui", "faut voir avec lui"),
    # Derriere un pronom sujet et devant un participe, c'est le pronominal.
    ("il c'est trompé de jour", "il s'est trompé de jour"),
    ("elle c'est bien débrouillée", "elle s'est bien débrouillée"),
    # « ces » determine un nom pluriel ; devant « pas » il n'y en a pas.
    ("ces pas faux ce que tu dis", "c'est pas faux ce que tu dis"),
    ("ses pas normal ce truc", "c'est pas normal ce truc"),
])
def test_les_homophones_courants(correcteur, avant, apres):
    assert correcteur.corriger(avant)[0] == apres


@pytest.mark.parametrize("phrase", [
    # Les memes paires, du bon cote. Une regle qui les abime coute plus
    # cher qu'elle ne rapporte.
    "café ou thé",
    "oui ou non ça m'est égal",
    "tu viens ou pas",
    "un ou deux jours de plus",
    "il a du pain et du fromage",
    "j'ai du mal à y croire",
    "il a du courage pour deux",
    "je suis sur la route",
    "pose ça sur la table",
    "un peu plus tard dans la journée",
    "il y a peu de chances",
    "voire même beaucoup mieux",
    "ses pas résonnaient dans le couloir",
    "ces pas perdus ne servent à rien",
    "lui c'est différent",
    "ces livres sont à moi",
    "il peut être là dans dix minutes",
    "c'est noir ou blanc",
])
def test_les_homophones_courants_ne_s_inventent_pas(correcteur, phrase):
    assert correcteur.corriger(phrase)[0] == phrase
