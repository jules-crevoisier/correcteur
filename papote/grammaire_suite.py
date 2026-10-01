# -*- coding: utf-8 -*-
"""Les fautes de tous les jours que la grammaire laissait passer.

Ce module prolonge `grammaire.py` : memes regles, meme mecanisme, mais des
fautes qu'une sonde sur du francais de messagerie a montrees intactes — et
qui sont parmi les plus courantes.

    je ai, que il, de accord     l'elision oubliee, avec une espace
    c est, j ai, qu est ce       l'apostrophe remplacee par une espace
    ce mec la, ces gens la       le trait d'union de « -là »
    est til                      « est-il », « a-t-il »
    tu m'a dit                   « m'as » : le sujet commande l'auxiliaire
    mon ami et venu              « et » pour « est »
    quand a moi                  « quant à moi »
    ils leurs ont dit            « leur » devant un verbe
    a demain, a plus tard        « à », en tete de phrase
    c'est pas sa                 « sa » ne finit jamais une phrase
    elle est tres joli           l'accord passe par-dessus « très »

Comme partout ailleurs, le doute fait taire : chaque regle prefere ne rien
faire que corriger a tort.
"""

from __future__ import annotations

from .grammaire import (
    PRONOMS_COMPLEMENTS, CONJUGUES,
    AUXILIAIRES, CONJUGUES, DETERMINANTS, MOTS_INVARIABLES, PRONOMS_SUJETS,
    TRAITS_ETRE, _accord_sujet_nominal_etre, _est_adjectif, _est_pluriel,
    _sujet_avant_le_pronom,
    appliquer_casse, ACCORDS_ETRE, regle,
)

VOYELLES = "aeiouyàâäéèêëîïôöùûüœ"

# Les mots en « h » muet les plus courants : devant eux, l'elision est
# obligatoire comme devant une voyelle. Les autres « h » sont aspires ou
# douteux, et on n'y touche pas.
H_MUET = {
    "heure", "heures", "homme", "hommes", "hôtel", "hôtels", "histoire",
    "histoires", "hôpital", "habitude", "habitudes", "habite",
    "habites", "habitent", "hiver", "humeur", "honneur", "hésite", "hésites",
    "humain", "humaine", "humains", "horreur", "hypothèse", "herbe",
}

# « d'hier », « qu'hier » : l'adverbe s'elide, mais « la hier » ne devient
# jamais « l'hier ». Le mot n'est donc admis que derriere « de » et « que ».
H_MUET_ADVERBES = {"hier"}

# Ceux-la commencent par une voyelle mais refusent l'elision : « le onze »,
# « de ouf », « le oui ».
SANS_ELISION = {
    "onze", "onzième", "oui", "ouais", "ouf", "ouiche", "ouistiti", "yaourt",
    "yoga", "yeti", "yen", "whisky", "ok", "ah", "oh", "euh", "ouh",
}

# Apres « le » ou « la », ces mots ne sont jamais elides : ce sont des
# conjonctions, des chiffres, ou l'on hesite entre plusieurs lectures.
SANS_ELISION_ARTICLE = SANS_ELISION | {
    "et", "ou", "où", "est", "a", "à", "un", "une", "on", "en", "y",
}


def _voyelle_initiale(mot: str, adverbes: bool = False) -> bool:
    if not mot or mot in SANS_ELISION:
        return False
    return (mot[0] in VOYELLES or mot in H_MUET
            or (adverbes and mot in H_MUET_ADVERBES))


# -- l'elision oubliee ------------------------------------------------------

ELISIONS = {
    "je": "j'", "me": "m'", "te": "t'", "se": "s'", "ne": "n'",
    "que": "qu'", "de": "d'", "le": "l'", "la": "l'", "ce": "c'",
    "jusque": "jusqu'", "lorsque": "lorsqu'", "puisque": "puisqu'",
    "quoique": "quoiqu'",
}

# « ce » ne s'elide que devant la forme du verbe etre.
APRES_CE = {"est", "était", "étaient", "eût", "étoit"}


@regle("ELISION_MANQUANTE", "devant une voyelle, l'apostrophe remplace l'espace")
def _elision_manquante(ctx, i: int):
    """« je ai » -> « j'ai », « que il » -> « qu'il », « de accord » -> « d'accord »."""
    mot = ctx.mot(i)
    suivant = ctx.mot(i + 1)
    if not suivant or ctx.separateur(i) != " ":
        return None
    # « Dois-je enregistrer » : le pronom inverse ne s'elide pas.
    if i > 0 and ctx.separateur(i - 1).endswith("-"):
        return None

    if mot == "si":
        # « s'il » : la seule elision de « si ».
        if suivant in ("il", "ils"):
            return (appliquer_casse(ctx.brut(i), "s'") + ctx.brut(i + 1), 2)
        return None

    elision = ELISIONS.get(mot)
    if elision is None or not _voyelle_initiale(suivant,
                                                adverbes=mot in ("de", "que")):
        return None
    if not ctx.connait(suivant):
        return None
    if mot == "ce" and suivant not in APRES_CE:
        return None
    if mot in ("le", "la") and suivant in SANS_ELISION_ARTICLE:
        return None
    if mot in ("que", "de") and suivant in ("et", "ou", "où", "oui", "à"):
        return None
    if mot == "je" and suivant in ("et", "ou", "où", "est"):
        return None
    # « me off », « me environ » : un pronom complement annonce un verbe.
    if mot in ("me", "te", "se", "ne") and suivant not in ("y", "en") \
            and not ctx.morphologie.verbe(suivant) \
            and not ctx.morphologie.est(suivant, "inf"):
        return None
    return (appliquer_casse(ctx.brut(i), elision) + ctx.brut(i + 1), 2)


# « c est bon », « j ai faim », « qu est ce que » : l'apostrophe a ete
# tapee comme une espace.
LETTRES_ELIDEES = {
    "c": "c'", "j": "j'", "l": "l'", "d": "d'", "n": "n'", "m": "m'",
    "s": "s'", "t": "t'", "qu": "qu'",
}


@regle("APOSTROPHE_EN_ESPACE", "l'apostrophe a ete tapee comme une espace")
def _apostrophe_en_espace(ctx, i: int):
    """« c est » -> « c'est », « j ai » -> « j'ai »."""
    mot = ctx.mot(i)
    elision = LETTRES_ELIDEES.get(mot)
    if elision is None or ctx.separateur(i) != " ":
        return None
    # « militant-e-s », « la fonction L a » : une lettre accrochee a un mot,
    # ou une variable mathematique, pas une elision.
    if not ctx.brut(i).islower() or (i > 0 and not ctx.separateur(i - 1).endswith(" ")):
        return None
    suivant = ctx.mot(i + 1)
    if not _voyelle_initiale(suivant) or not ctx.connait(suivant):
        return None
    # Devant « n », « m », « t », « s », « j », il faut un verbe (ou « y »,
    # « en ») : « n entier naturel » est une variable suivie d'un adjectif.
    if mot in ("n", "m", "t", "s", "j") and suivant not in ("y", "en") \
            and not ctx.morphologie.verbe(suivant) \
            and not ctx.morphologie.est(suivant, "inf"):
        return None
    if suivant in ("et", "ou", "où", "oui"):
        return None
    # « c a », « s a » ne sont jamais des elisions.
    if suivant == "a" and mot in ("c", "s", "j", "d", "qu"):
        return None
    if mot == "qu" and suivant not in ("est", "il", "elle", "on", "ils",
                                       "elles", "un", "une", "y", "en"):
        return None
    return (appliquer_casse(ctx.brut(i), elision) + ctx.brut(i + 1), 2)


# -- "sen", "jen" : les mots colles qui existent ailleurs ----------------------

SUJETS_AVANT_SEN = {"on", "il", "elle", "ils", "elles", "ça", "qui", "me",
                    "te", "nous", "vous", "je", "tu", "ne"}


@regle("APOSTROPHE_COLLEE_EN", "« s'en » : il manque l'apostrophe")
def _sen_jen(ctx, i: int):
    """« on sen fout » -> « on s'en fout »."""
    mot = ctx.mot(i)
    if mot == "sen" and ctx.mot(i - 1) in SUJETS_AVANT_SEN:
        return appliquer_casse(ctx.brut(i), "s'en")
    if mot == "jen" and ctx.debut_de_segment(i) and ctx.mot(i + 1):
        return appliquer_casse(ctx.brut(i), "j'en")
    return None


# -- le trait d'union de « -là » --------------------------------------------

DEMONSTRATIFS = {"ce", "cet", "cette", "ces"}

# Ce qui peut suivre « ce mec la » sans que « la » soit un pronom.
APRES_LA_LOCALISANT = {
    "est", "sont", "était", "étaient", "sera", "seront", "va", "vont",
    "me", "m'", "te", "t'", "nous", "vous", "qui", "que", "qu'", "c'", "ça",
    "fait", "font", "peut", "peuvent", "a", "ont",
}


@regle("TRAIT_UNION_LA", "« -là » se relie au nom par un trait d'union")
def _trait_union_la(ctx, i: int):
    """« ces gens la sont fous » -> « ces gens-là sont fous ».

    On se place sur le nom : c'est lui qui recoit le trait d'union.
    """
    if ctx.mot(i - 1) not in DEMONSTRATIFS or ctx.separateur(i) != " ":
        return None
    nom = ctx.mot(i)
    localisant = ctx.mot(i + 1)
    if localisant not in ("la", "là", "ci"):
        return None
    if not ctx.morphologie.nom(nom) or nom in MOTS_INVARIABLES:
        return None
    # Le pronom « la » se trouve devant un verbe : « ce mec la voit ». On
    # n'ecrit « -là » que lorsque rien de tel ne suit.
    if not (ctx.fin_de_segment(i + 1) or ctx.mot(i + 2) in APRES_LA_LOCALISANT):
        return None
    if ctx.mot(i + 2) in ("a", "ont", "fait", "font", "peut", "peuvent") \
            and localisant == "la":
        # « ce mec la a vu » : plus probablement « l'a vu ».
        return None
    marque = "-ci" if localisant == "ci" else "-là"
    return (ctx.brut(i) + marque, 2)


# -- "est-il", "a-t-il" ---------------------------------------------------------

PRONOMS_INVERSES = {"til": "il", "tils": "ils"}


@regle("TRAIT_UNION_TIL", "l'inversion du sujet s'écrit avec des traits d'union")
def _trait_union_til(ctx, i: int):
    """« est til » -> « est-il », « a til » -> « a-t-il »."""
    pronom = PRONOMS_INVERSES.get(ctx.mot(i + 1))
    if pronom is None or ctx.separateur(i) != " ":
        return None
    verbe = ctx.mot(i)
    if not ctx.morphologie.verbe(verbe) and verbe not in AUXILIAIRES:
        return None
    if verbe.endswith(("a", "e")):
        return (f"{ctx.brut(i)}-t-{pronom}", 2)
    if verbe.endswith(("t", "d")):
        return (f"{ctx.brut(i)}-{pronom}", 2)
    return None


# -- l'auxiliaire, et son sujet ---------------------------------------------

@regle("AUXILIAIRE_TU_CLITIQUE",
       "avec « tu », l'auxiliaire est « as », même derrière « m' » ou « t' »")
def _auxiliaire_tu_clitique(ctx, i: int):
    """« tu m'a dit » -> « tu m'as dit »."""
    if ctx.noyau(i) != "a" or ctx.elision(i) not in ("m'", "t'", "l'", "n'", "s'"):
        return None
    if ctx.elision(i) == "s'":
        return None
    if ctx.mot(i - 1) == "tu" or (ctx.mot(i - 1) in ("ne", "me", "te", "le", "la")
                                  and ctx.mot(i - 2) == "tu"):
        return appliquer_casse(ctx.brut(i), ctx.elision(i) + "as")
    return None


@regle("A_ACCENT_APRES_TU", "avec « tu », le verbe avoir est « as »")
def _tu_a_accent(ctx, i: int):
    """« tu à raison » -> « tu as raison »."""
    if ctx.mot(i) == "à" and ctx.mot(i - 1) == "tu" and ctx.mot(i + 1):
        return appliquer_casse(ctx.brut(i), "as")
    return None


# « rien » n'y figure pas : « rien a » est trop ambigu pour qu'on tranche.
ANTE_A = {"chose", "choses", "beaucoup", "plein", "assez", "trop",
          "tant", "autant"}


@regle("A_ACCENT_APRES_QUANTITE", "devant un infinitif, c'est la préposition « à »")
def _a_accent_avant_infinitif(ctx, i: int):
    """« quelque chose a te dire » -> « quelque chose à te dire »."""
    if ctx.mot(i) != "a" or ctx.mot(i - 1) not in ANTE_A:
        return None
    for saut in (1, 2):
        suivant = ctx.mot(i + saut)
        if ctx.morphologie.est(suivant, "inf"):
            return appliquer_casse(ctx.brut(i), "à")
        if suivant not in ("te", "me", "se", "vous", "nous", "le", "la",
                           "les", "lui", "leur", "y", "en"):
            return None
    return None


DEBUT_A_ACCENT = {
    "plus", "tout", "demain", "bientôt", "bientot", "ce", "tantôt", "lundi",
    "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
    "après", "tous", "la",
}


@regle("A_ACCENT_EN_TETE", "en tête de phrase, « à » est la préposition")
def _a_accent_en_tete(ctx, i: int):
    """« a demain », « a plus tard » -> « à demain », « à plus tard »."""
    if ctx.mot(i) != "a" or not ctx.debut_de_segment(i):
        return None
    suivant = ctx.mot(i + 1)
    if suivant == "la":
        # « a la prochaine » : seulement si « prochaine » suit.
        if ctx.mot(i + 2) in ("prochaine", "semaine", "revoyure"):
            return appliquer_casse(ctx.brut(i), "à")
        return None
    if suivant in DEBUT_A_ACCENT:
        return appliquer_casse(ctx.brut(i), "à")
    return None


@regle("QUANT_A", "« quant à » : il s'agit de la quantité, pas du moment")
def _quant_a(ctx, i: int):
    """« quand a moi » -> « quant à moi »."""
    if ctx.mot(i) != "quand" or ctx.mot(i + 1) not in ("a", "à"):
        return None
    if ctx.mot(i + 2) not in ("moi", "toi", "lui", "elle", "nous", "vous",
                              "eux", "elles", "ce", "mon", "ma", "ton", "ta"):
        return None
    if ctx.separateur(i) != " ":
        return None
    return (appliquer_casse(ctx.brut(i), "quant à"), 2)


PARTICIPES_ETRE = {
    "venu", "venue", "venus", "venues", "parti", "partie", "partis",
    "parties", "arrivé", "arrivée", "arrivés", "arrivées", "tombé",
    "tombée", "tombés", "tombées", "allé", "allée", "allés", "allées",
    "né", "née", "nés", "nées", "mort", "morte", "morts", "mortes",
    "resté", "restée", "restés", "restées", "devenu", "devenue", "devenus",
    "devenues", "sorti", "sortie", "sortis", "sorties", "entré", "entrée",
    "entrés", "entrées", "revenu", "revenue", "rentré", "rentrée",
}


@regle("ET_EST_AVANT_PARTICIPE", "devant ce participe, c'est le verbe « est »")
def _et_est_avant_participe(ctx, i: int):
    """« mon ami et venu » -> « mon ami est venu »."""
    if ctx.mot(i) != "et" or ctx.mot(i + 1) not in PARTICIPES_ETRE:
        return None
    precedent = ctx.mot(i - 1)
    if not precedent or ctx.debut_de_segment(i):
        return None
    # « il est parti et venu » : deux participes coordonnes.
    if precedent in PARTICIPES_ETRE or ctx.est_participe(precedent):
        return None
    if precedent in ("et", "puis", "mais", "ou", "ni"):
        return None
    return appliquer_casse(ctx.brut(i), "est")


@regle("LEUR_DEVANT_VERBE", "devant un verbe, « leur » est invariable")
def _leur_devant_verbe(ctx, i: int):
    """« ils leurs ont dit » -> « ils leur ont dit »."""
    if ctx.mot(i) != "leurs" or ctx.elision(i):
        return None
    if ctx.mot(i - 1) not in PRONOMS_SUJETS | {"ne", "n'", "qui", "on"}:
        return None
    suivant = ctx.mot(i + 1)
    if suivant in ("en", "y", "le", "la", "les", "ont", "avaient", "avait",
                   "a", "disent", "donnent", "faut", "parle", "parlent",
                   "dit", "dis", "rend", "envoie", "envoient", "apporte"):
        return appliquer_casse(ctx.brut(i), "leur")
    if ctx.morphologie.seulement(suivant, *CONJUGUES):
        return appliquer_casse(ctx.brut(i), "leur")
    return None


@regle("SA_FIN_DE_PHRASE", "« sa » ne termine jamais une phrase : c'est « ça »")
def _sa_en_fin_de_phrase(ctx, i: int):
    """« c'est pas sa » -> « c'est pas ça »."""
    if ctx.mot(i) != "sa" or not ctx.fin_de_segment(i):
        return None
    if ctx.mot(i - 1) in ("de", "d'", "à", "avec", "sans"):
        # « il parle de sa. » : la phrase est coupee, pas terminee.
        return None
    if ctx.separateur(i - 1) != " " and i > 0:
        return None
    return appliquer_casse(ctx.brut(i), "ça")


@regle("SA_DEVANT_VERBE_CONJUGUE", "devant un verbe, c'est « ça »")
def _sa_devant_verbe(ctx, i: int):
    """« sa marchait pas » -> « ça marchait pas »."""
    if ctx.mot(i) != "sa":
        return None
    suivant = ctx.mot(i + 1)
    if not suivant or ctx.elision(i + 1):
        return None
    traits = ctx.morphologie.traits(suivant)
    if not traits or not traits <= CONJUGUES:
        return None
    # Un imparfait ou un conditionnel n'est jamais un nom : « marchait »,
    # « pourrait ». Au present, « marche » peut etre les deux.
    if suivant.endswith(("ait", "aient", "erait", "irait")):
        return appliquer_casse(ctx.brut(i), "ça")
    return None


# -- les accords que « très » cachait ---------------------------------------

INTENSIFS = {"très", "trop", "assez", "vraiment", "super", "si", "tellement",
             "plutôt", "bien", "aussi", "hyper", "ultra", "complètement",
             "totalement", "un peu", "tout"}


@regle("ACCORD_ADJECTIF_ATTRIBUT",
       "l'adjectif attribut s'accorde avec le sujet, même derrière « très »")
def _accord_adjectif_attribut(ctx, i: int):
    """« elle est très joli » -> « elle est très jolie »,
    « les gens sont bizarre » -> « les gens sont bizarres »."""
    mot = ctx.mot(i)
    if ctx.elision(i) or not mot or mot in MOTS_INVARIABLES:
        return None
    # « nous sommes le plus vulnérable », « ils étaient, semble-t-il » : ni
    # un article ni un verbe ne s'accordent comme un adjectif.
    if mot in DETERMINANTS or mot in PRONOMS_COMPLEMENTS \
            or ctx.morphologie.verbe(mot):
        return None
    if not (_est_adjectif(ctx, mot) or ctx.est_participe(mot)):
        return None
    # « elles sont source de débats » : un nom attribut, qui garde son
    # nombre.
    if ctx.apercu(i + 1) in ("de", "d'") or ctx.apercu(i + 1).startswith("d'"):
        return None

    decalage = 1 if ctx.mot(i - 1) in INTENSIFS else 0
    auxiliaire = ctx.noyau(i - 1 - decalage)
    if auxiliaire not in ("est", "sont", "sommes", "était", "étaient",
                          "étions", "sera", "seront", "serait", "seraient"):
        return None

    position = i - decalage
    sujet = ctx.mot(position - 2)
    terminaison = ACCORDS_ETRE.get((sujet, auxiliaire))
    if terminaison is None and auxiliaire in ("étaient", "était", "serait",
                                              "seraient", "sera", "seront",
                                              "étions"):
        terminaison = {("elle", "était"): "e", ("elles", "étaient"): "es",
                       ("ils", "étaient"): "s", ("elle", "sera"): "e",
                       ("elles", "seront"): "es", ("ils", "seront"): "s",
                       ("elle", "serait"): "e", ("elles", "seraient"): "es",
                       ("ils", "seraient"): "s"}.get((sujet, auxiliaire))
    if terminaison is None:
        terminaison = _accord_sujet_nominal_etre(ctx, position)
    if terminaison is None:
        return None

    if mot.endswith("e"):
        # « bizarre », « rouge » : le feminin est deja la, seul le pluriel
        # s'ajoute.
        if terminaison in ("s", "es") and ctx.connait(mot + "s") \
                and not _deja_pluriel(ctx, mot):
            return appliquer_casse(ctx.brut(i), mot + "s")
        return None
    if mot.endswith(("s", "x")):
        return None
    if decalage == 0:
        # Sans intensif, `ACCORD_PARTICIPE_ETRE` a deja son mot a dire.
        return None
    accorde = ctx.morphologie.forme(mot, TRAITS_ETRE[terminaison])
    if accorde is None:
        accorde = mot + terminaison
    if accorde == mot or not ctx.connait(accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


def _deja_pluriel(ctx, mot: str) -> bool:
    return ctx.morphologie.pluriel(mot) or _est_pluriel(ctx, mot) and \
        mot.endswith("s")


# -- « ma », « ces », « ce » : les homophones devant un verbe ----------------

SUJETS_DE_M_A = {"il", "elle", "on", "ça", "qui", "tu", "ils", "elles"}


@regle("MA_APRES_SUJET", "après un sujet, « ma » est « m'a » : le possessif est exclu")
def _ma_apres_sujet(ctx, i: int):
    """« il ma rien dit » -> « il m'a rien dit », « tu ma manquer » -> « tu m'as manqué ».

    Un possessif ne suit jamais directement un pronom sujet. Derriere lui,
    « ma » ne peut etre que le pronom et l'auxiliaire colles : le verbe
    suivant est alors un participe, ou une negation.
    """
    mot = ctx.mot(i)
    if mot not in ("ma", "ta") or ctx.elision(i):
        return None
    sujet = ctx.mot(i - 1)
    if sujet in ("ne", "n'"):
        sujet = ctx.mot(i - 2)
    if sujet not in SUJETS_DE_M_A:
        return None
    suivant = ctx.mot(i + 1)
    if not suivant:
        return None
    pronom = "m'" if mot == "ma" else "t'"
    auxiliaire = {"tu": "as", "ils": "ont", "elles": "ont"}.get(sujet, "a")
    if suivant in ("rien", "pas", "jamais", "plus", "déjà", "toujours",
                   "bien"):
        return appliquer_casse(ctx.brut(i), pronom + auxiliaire)
    if ctx.est_participe(ctx.noyau(i + 1)):
        return appliquer_casse(ctx.brut(i), pronom + auxiliaire)
    # « tu ma manquer » : un infinitif du premier groupe. On ne l'accepte que
    # s'il ne s'ecrit pas aussi comme un nom.
    if (suivant.endswith("er") and ctx.morphologie.est(suivant, "inf")
            and not ctx.morphologie.nom(suivant)):
        return appliquer_casse(ctx.brut(i), pronom + auxiliaire)
    return None


MODAUX = {"peut", "peux", "veut", "veux", "doit", "dois", "va", "vais",
          "vas", "faut", "vont", "allons", "pouvons", "voulons", "devons",
          "pourrait", "pourra", "pourrais", "voudrait", "voudrais",
          "devrait", "devrais", "aller", "pouvoir", "vouloir", "devoir",
          "allez", "pouvez", "voulez", "devez", "veulent", "peuvent",
          "doivent"}


@regle("CE_SE_APRES_MODAL", "devant un infinitif pronominal, c'est « se »")
def _ce_se_apres_modal(ctx, i: int):
    """« on peut ce voir » -> « on peut se voir »."""
    if ctx.mot(i) != "ce" or ctx.mot(i - 1) not in MODAUX:
        return None
    suivant = ctx.mot(i + 1)
    if not suivant or not ctx.morphologie.est(suivant, "inf"):
        return None
    # Un nom de meme forme (« ce dîner ») ecarte la regle.
    if ctx.morphologie.nom(suivant):
        return None
    return appliquer_casse(ctx.brut(i), "se")


@regle("CES_S_EST", "après un sujet, « ces » est « s'est »")
def _ces_s_est(ctx, i: int):
    """« il ces passé » -> « il s'est passé »."""
    if ctx.mot(i) != "ces" or ctx.mot(i - 1) not in ("il", "elle", "on"):
        return None
    if ctx.est_participe(ctx.noyau(i + 1)):
        return appliquer_casse(ctx.brut(i), "s'est")
    return None


@regle("LA_FIN_DE_PHRASE", "en fin de phrase, après « de » ou « par », c'est « là »")
def _la_en_fin_de_phrase(ctx, i: int):
    """« il est pres de la » -> « il est près de là »."""
    if ctx.mot(i) != "la" or not ctx.fin_de_segment(i):
        return None
    if ctx.mot(i - 1) not in ("de", "par", "jusque"):
        return None
    if ctx.separateur(i - 1) != " ":
        return None
    return appliquer_casse(ctx.brut(i), "là")


# -- nous et vous, et leur verbe --------------------------------------------

FORMES_EN_VOUS = {
    "faite": "faites", "fait": "faites", "fais": "faites",
    "dite": "dites", "dit": "dites", "dis": "dites",
}


@regle("VOUS_FAITES_DITES", "avec « vous », « faites » et « dites »")
def _vous_faites(ctx, i: int):
    """« vous faite quoi » -> « vous faites quoi »."""
    if ctx.mot(i - 1) != "vous" or ctx.elision(i):
        return None
    correcte = FORMES_EN_VOUS.get(ctx.mot(i))
    if correcte is None:
        return None
    # « il vous dit », « ça vous fait mal » : ici « vous » est complement.
    if _sujet_avant_le_pronom(ctx, i):
        return None
    if ctx.mot(i) in ("faite", "dite"):
        # Un participe feminin ne suit jamais « vous » sujet ; il peut suivre
        # « vous a » (« elle vous a faite »), d'ou la garde.
        if ctx.mot(i - 2) in AUXILIAIRES or ctx.mot(i - 2) in ("n'", "ne", "y"):
            return None
        return appliquer_casse(ctx.brut(i), correcte)
    # « vous fait », « vous dit » n'ont qu'une lecture de sujet en tete de
    # phrase ; ailleurs, « ça vous fait mal » interdit de trancher.
    if not (ctx.debut_de_segment(i - 1)
            or ctx.mot(i - 2) in ("et", "mais", "donc", "alors", "puis")):
        return None
    if ctx.mot(i + 1) in ("que", "qu'"):
        return None
    return appliquer_casse(ctx.brut(i), correcte)


@regle("NOUS_AVONS", "avec « nous », le verbe se termine par « -ons »")
def _nous_ons(ctx, i: int):
    """« nous avont » -> « nous avons »."""
    mot = ctx.mot(i)
    if ctx.mot(i - 1) != "nous" or not mot.endswith("ont") or ctx.connait(mot):
        return None
    candidat = mot[:-3] + "ons"
    if ctx.connait(candidat) and ctx.morphologie.verbe(candidat):
        return appliquer_casse(ctx.brut(i), candidat)
    return None


# -- concordance : « il a dit qu'il viendrait » ------------------------------

DIRE_AU_PASSE = {"dit", "disait", "disais", "pensait", "pensais", "croyait",
                 "croyais", "savait", "savais", "promis", "promettait",
                 "espérait", "espérais", "annoncé", "annonçait", "pensé",
                 "cru", "su", "jurait", "jurais", "répondu", "répondait",
                 "prévenu", "assuré", "assurait", "expliqué", "écrit"}


@regle("CONDITIONNEL_APRES_DIT", "après un verbe au passé, le futur devient conditionnel")
def _conditionnel_apres_dit(ctx, i: int):
    """« il a dit qu'il viendrai » -> « il a dit qu'il viendrait »."""
    mot = ctx.mot(i)
    if not mot.endswith("rai") or ctx.elision(i):
        return None
    sujet = ctx.noyau(i - 1)
    if sujet not in ("il", "elle", "on"):
        return None
    if ctx.elision(i - 1) != "qu'" and ctx.mot(i - 2) != "que":
        return None
    # Le verbe de parole est juste avant « que » : « a dit que », « disait
    # que ». Un peu de marge pour l'auxiliaire et un complement.
    debut = i - 2 if ctx.elision(i - 1) == "qu'" else i - 3
    if not any(ctx.mot(k) in DIRE_AU_PASSE for k in range(debut - 3, debut + 1)):
        return None
    conditionnel = mot + "t"
    if ctx.connait(conditionnel):
        return appliquer_casse(ctx.brut(i), conditionnel)
    return None


@regle("VOUDRAIS", "« je voudrais » : la politesse s'écrit au conditionnel")
def _je_voudrais(ctx, i: int):
    """« je voudrai un café » -> « je voudrais un café »."""
    if ctx.mot(i) != "voudrai" or ctx.mot(i - 1) != "je":
        return None
    # « quand je voudrai un café, je le dirai » : le futur est juste.
    if ctx.mot(i - 2) in ("quand", "lorsque", "lorsqu'", "si", "dès", "dès que",
                          "aussitôt", "tant", "que", "qu'", "où", "comme",
                          "puisque", "après", "avant"):
        return None
    if ctx.mot(i + 1) in DETERMINANTS | {"que", "qu'", "savoir", "bien",
                                          "juste", "de", "d'", "te", "vous",
                                          "lui", "y", "demander", "prendre",
                                          "un", "une"}:
        return appliquer_casse(ctx.brut(i), "voudrais")
    return None


def _en_tete_de_liste(nom: str) -> None:
    """Fait passer la regle nommee avant toutes les autres.

    L'ordre de declaration est l'ordre d'application, et certaines regles
    d'ici corrigent un verbe que l'accord general aurait deja touche : le
    futur « viendra » l'emporterait sur le conditionnel « viendrait ».
    """
    from .grammaire import REGLES

    for k, r in enumerate(REGLES):
        if r.nom == nom:
            REGLES.insert(0, REGLES.pop(k))
            return


_en_tete_de_liste("CONDITIONNEL_APRES_DIT")


# ===========================================================================
# Ce que le banc LanguageTool a montre : les fautes les plus courantes qui
# passaient. Voir « outils/banc_languagetool.py ».
# ===========================================================================

from .grammaire import (  # noqa: E402
    CHARNIERES, DETERMINANTS_PLURIELS, accorder_le_verbe, sujet_avant,
    PERSONNE_DU_SUJET,
)

# -- le subjonctif : « il faut que tu viens » --------------------------------

# Ce qui, devant « que », appelle le subjonctif.
APPELLENT_LE_SUBJONCTIF = {
    "faut", "faudrait", "fallait", "faudra", "veux", "veut", "voulons",
    "voulez", "veulent", "voudrais", "voudrait", "voudrions", "voudriez",
    "voudraient", "aimerais", "aimerait", "souhaite", "souhaites",
    "souhaitons", "souhaitez", "souhaiterais", "souhaiterait", "préfère",
    "préfères", "préférerais", "préférerait", "avant", "pour", "afin", "sans",
    "condition", "attends", "attendre", "exige", "exiges", "peur", "dommage",
    "important", "nécessaire", "essentiel", "possible", "impossible",
    "temps", "bien", "quoique", "jusqu'à", "sorte", "ordonne", "veille",
}


def subjonctif(ctx, mot: str, personne: str) -> str | None:
    """La forme du subjonctif present qui correspond a ce present de l'indicatif.

    Le dictionnaire range le paradigme par temps : le present de l'indicatif
    est le deuxieme groupe, le subjonctif present le septieme quand il
    existe. Les verbes du premier groupe n'en ont pas a part : leur
    subjonctif se confond avec le present, sauf a « nous » et « vous », ou
    il emprunte l'imparfait (« que nous mangions »).
    """
    reponses = set()
    for lemme in ctx.morphologie.lemmes(mot):
        groupes = ctx.morphologie.paradigme(lemme)
        # « que vous alliez » : imparfait d'aller autant que present
        # d'allier. Un mot qui vit dans un autre temps n'est pas a changer.
        if any(mot in g for k, g in enumerate(groupes) if k not in (0, 1)):
            return None
        if len(groupes) < 7 or mot not in groupes[1]:
            continue
        if len(groupes) >= 8:
            cible = groupes[6]
        elif personne in ("1p", "2p"):
            cible = groupes[2]
        else:
            cible = groupes[1]
        formes = [f for f, t in cible.items() if personne in t]
        if formes:
            reponses.add(formes[0])
    if len(reponses) != 1:
        return None
    return reponses.pop()


@regle("SUBJONCTIF", "après « il faut que », « pour que »… le verbe est au subjonctif")
def _subjonctif(ctx, i: int):
    """« il faut que tu viens » -> « il faut que tu viennes »."""
    if ctx.elision(i):
        return None
    sujet = sujet_avant(ctx, i)
    personne = PERSONNE_DU_SUJET.get(sujet)
    if personne is None or sujet == "ça":
        return None
    # Ou est le sujet ? Juste avant, ou derriere des pronoms complements.
    k = i - 1
    while ctx.noyau(k) != sujet and k > i - 4:
        k -= 1
    if ctx.noyau(k) != sujet:
        return None
    # Le « que » : colle au sujet (« qu'il ») ou juste devant.
    if ctx.elision(k) == "qu'":
        avant_que = k - 1
    elif ctx.mot(k - 1) in ("que", "qu'"):
        avant_que = k - 2
    else:
        return None
    declencheur = ctx.mot(avant_que)
    if declencheur not in APPELLENT_LE_SUBJONCTIF:
        # « à condition que », « bien que » : un mot plus loin.
        if ctx.mot(avant_que) not in ("à", "en", "de") or \
                ctx.mot(avant_que + 1) not in APPELLENT_LE_SUBJONCTIF:
            return None
    # « pour que » et « sans que » ne valent que comme conjonctions : « pour »
    # ou « sans » juste devant « que ».
    mot = ctx.mot(i)
    if personne not in ctx.morphologie.traits(mot):
        return None
    voulu = subjonctif(ctx, mot, personne)
    if voulu is None or voulu == mot:
        return None
    return appliquer_casse(ctx.brut(i), voulu)


# -- « c'est moi qui est » ---------------------------------------------------

PERSONNE_DE_L_ANTECEDENT = {"moi": "1s", "toi": "2s", "nous": "1p", "vous": "2p"}


@regle("QUI_ACCORD_ANTECEDENT", "après « moi qui », le verbe s'accorde avec « moi »")
def _qui_antecedent(ctx, i: int):
    """« c'est moi qui est » -> « c'est moi qui suis »."""
    k = i - 1
    while ctx.mot(k) in ("me", "te", "lui", "leur", "nous", "vous", "le",
                         "la", "les", "y", "en", "ne", "n'") and k > i - 3:
        k -= 1
    if ctx.mot(k) != "qui":
        return None
    personne = PERSONNE_DE_L_ANTECEDENT.get(ctx.mot(k - 1))
    if personne is None:
        return None
    # Seulement « c'est moi qui », « c'était toi qui », ou « moi qui » en tete :
    # « l'animal en moi qui le veut », « lui ou moi qui a gagné », « savez-vous
    # qui est » ne mettent pas le pronom en sujet.
    presentatif = ctx.elision(k - 2) in ("c'", "ç'") or ctx.mot(k - 2) in (
        "est", "était", "sera", "suis", "es")
    if not (presentatif or (ctx.debut_de_segment(k - 1)
                            and not ctx.separateur(k - 2).endswith("-"))):
        return None
    if ctx.mot(k - 2) in ("ou", "et", "ni"):
        return None
    # « c'est moi qui », « toi qui », mais pas « chez moi qui » (rare) ni
    # « à vous qui » (on s'adresse, le verbe suit la 2e personne aussi).
    return accorder_le_verbe(ctx, i, personne)


# -- l'inversion du sujet ----------------------------------------------------

@regle("ACCORD_INVERSION", "le pronom inversé s'accorde avec son verbe")
def _accord_inversion(ctx, i: int):
    """« sont-il » -> « sont-ils », « pouvait-ils » -> « pouvait-il »."""
    pronom = ctx.mot(i)
    if pronom not in ("il", "ils", "elle", "elles") or i == 0:
        return None
    if not ctx.separateur(i - 1).endswith("-"):
        return None
    verbe = ctx.mot(i - 1)
    if verbe == "t":
        verbe = ctx.mot(i - 2)
    traits = ctx.morphologie.traits(verbe)
    if not traits & CONJUGUES:
        return None
    if pronom in ("il", "elle") and "3p" in traits and "3s" not in traits:
        return appliquer_casse(ctx.brut(i), pronom + "s")
    if pronom in ("ils", "elles") and "3s" in traits and "3p" not in traits:
        return appliquer_casse(ctx.brut(i), pronom[:-1])
    return None


PRONOMS_INVERSIBLES = {"tu", "vous", "il", "elle", "on", "nous", "ils", "elles"}
INTERROGATIFS_DEVANT = {"où", "quand", "comment", "pourquoi", "que", "qu'",
                        "combien", "quel", "quelle", "quels", "quelles"}


@regle("INVERSION_SANS_TRAIT", "dans une question inversée, le verbe et le pronom se lient")
def _inversion_sans_trait(ctx, i: int):
    """« peut tu venir » -> « peux-tu venir », « a il fini » -> « a-t-il fini »."""
    pronom = ctx.mot(i + 1)
    if pronom not in PRONOMS_INVERSIBLES or ctx.separateur(i) != " ":
        return None
    if not (ctx.debut_de_segment(i) or ctx.mot(i - 1) in INTERROGATIFS_DEVANT):
        return None
    verbe = ctx.mot(i)
    if ctx.elision(i) or not ctx.morphologie.verbe(verbe) \
            or ctx.morphologie.nom(verbe) or verbe in MOTS_INVARIABLES:
        return None
    # « attends tu vas voir », « regarde il pleut » : un imperatif suivi
    # d'une nouvelle proposition. Ce qui suit le pronom ne doit pas etre un
    # verbe conjugue.
    k = i + 2
    while ctx.mot(k) in ("y", "en", "ne", "n'", "le", "la", "les", "me", "te",
                         "se", "lui", "leur", "nous", "vous") and k < i + 5:
        k += 1
    apres = ctx.noyau(k)
    if not apres or (ctx.morphologie.verbe(apres)
                     and not ctx.morphologie.est(apres, "inf")
                     and not ctx.est_participe(apres)):
        return None
    personne = PERSONNE_DU_SUJET[pronom]
    if personne not in ctx.morphologie.traits(verbe):
        # On n'ajuste le verbe qu'a « je » et « tu » : « peut tu » est
        # « peux-tu ». Devant « nous » ou « elles », c'est le pronom qui
        # est le plus souvent complement (« venez nous aider », « à elles
        # d'assumer »).
        if pronom != "tu":
            return None
        accorde = ctx.morphologie.accorder(verbe, personne)
        if accorde is None:
            return None
        verbe_ecrit = appliquer_casse(ctx.brut(i), accorde)
    else:
        verbe_ecrit = ctx.brut(i)
    liaison = "-t-" if (pronom in ("il", "elle", "on")
                        and verbe_ecrit.lower().endswith(("a", "e", "c"))) else "-"
    return (verbe_ecrit + liaison + ctx.brut(i + 1), 2)


# -- « j'eu », « je pu » : l'auxiliaire oublie ---------------------------------

PARTICIPES_SANS_AUXILIAIRE = {
    "eu", "pu", "su", "vu", "bu", "lu", "cru", "dû", "voulu", "reçu",
    "connu", "vécu", "perdu", "attendu", "entendu", "répondu", "vendu",
    "rendu", "fallu", "plu", "couru", "pris", "mis", "appris", "compris",
    "promis", "permis", "écrit", "ouvert", "offert", "souffert",
}
AUXILIAIRE_DE = {"je": "ai", "tu": "as", "il": "a", "elle": "a", "on": "a",
                 "nous": "avons", "vous": "avez", "ils": "ont", "elles": "ont"}


@regle("AUXILIAIRE_OUBLIE", "il manque l'auxiliaire avant ce participe")
def _auxiliaire_oublie(ctx, i: int):
    """« j'eu la chance » -> « j'ai eu la chance », « je pu » -> « j'ai pu »."""
    mot = ctx.noyau(i)
    if mot not in PARTICIPES_SANS_AUXILIAIRE or ctx.morphologie.verbe(mot):
        return None
    if ctx.elision(i) == "j'":
        # « j'eu » : le sujet est colle au participe.
        return appliquer_casse(ctx.brut(i), "j'ai " + mot)
    return None


def _sujet_est_inverse(ctx, k: int) -> bool:
    return k > 0 and (ctx.separateur(k - 1).endswith("-") or ctx.mot(k - 1) == "t")


@regle("AUXILIAIRE_OUBLIE_APRES_SUJET", "il manque l'auxiliaire avant ce participe")
def _auxiliaire_oublie_apres_sujet(ctx, i: int):
    """« je pu venir » -> « j'ai pu venir », « il vu » -> « il a vu ».

    On se place sur le pronom sujet, qui recoit l'auxiliaire.
    """
    sujet = ctx.mot(i)
    auxiliaire = AUXILIAIRE_DE.get(sujet)
    if auxiliaire is None or ctx.separateur(i) != " ":
        return None
    if ctx.mot(i + 1) not in PARTICIPES_SANS_AUXILIAIRE or _sujet_est_inverse(ctx, i):
        return None
    # « je pris une douche », « on écrit » : un passe simple ou un present
    # qui s'ecrit comme le participe.
    if ctx.morphologie.verbe(ctx.mot(i + 1)):
        return None
    # « nous » et « vous » complements : « il nous vu » n'est pas « nous avons ».
    if sujet in ("nous", "vous") and not ctx.debut_de_segment(i) \
            and ctx.mot(i - 1) not in CHARNIERES:
        return None
    if sujet == "je":
        return (appliquer_casse(ctx.brut(i), "j'ai"), 1)
    return (ctx.brut(i) + " " + auxiliaire, 1)


# -- l'accord avec un sujet nominal singulier --------------------------------

DETERMINANTS_SINGULIERS_SUJET = {
    "le", "la", "un", "une", "ce", "cet", "cette", "mon", "ma", "ton", "ta",
    "son", "sa", "notre", "votre", "leur", "chaque",
}


@regle("ACCORD_SUJET_NOMINAL_SINGULIER", "le verbe s'accorde avec son sujet au singulier")
def _accord_sujet_nominal_singulier(ctx, i: int):
    """« l'enfant dis merci » -> « l'enfant dit merci »."""
    mot = ctx.mot(i)
    if ctx.elision(i) or not mot:
        return None
    traits = ctx.morphologie.traits(mot)
    # Seulement une forme qui ne peut pas etre la 3e personne : « dis »,
    # « fais », « viens », « es ». « mange » est aussi une 3e personne et
    # n'a rien a corriger.
    if not traits or "3s" in traits or not traits & {"1s", "2s"}:
        return None
    if traits & NOMINAUX_SUITE or mot in MOTS_INVARIABLES:
        return None
    k = i - 1
    while ctx.mot(k) in ("me", "te", "lui", "leur", "nous", "vous", "le",
                         "la", "les", "y", "en", "ne", "n'", "qui") and k > i - 4:
        k -= 1
    nom = ctx.noyau(k)
    if not nom or not ctx.morphologie.nom(nom) or not ctx.morphologie.singulier(nom):
        return None
    if ctx.elision(k) == "l'":
        ouvrant = k
    elif ctx.mot(k - 1) in DETERMINANTS_SINGULIERS_SUJET:
        ouvrant = k - 1
    else:
        return None
    if not (ctx.debut_de_segment(ouvrant) or ctx.mot(ouvrant - 1) in CHARNIERES):
        return None
    return accorder_le_verbe(ctx, i, "3s")


from .morphologie import NOMINAUX as NOMINAUX_SUITE  # noqa: E402


# -- les confusions de mots, avec leur contexte ------------------------------

AVANT_COTE = {"à", "a", "de", "du", "aux", "ses", "mes", "tes", "nos", "vos",
              "leurs", "son", "mon", "ton", "notre", "votre", "leur", "un",
              "chaque", "l'autre", "autre"}


@regle("CONFUSIONS_EN_CONTEXTE", "ce mot existe, mais le contexte en appelle un autre")
def _confusions_en_contexte(ctx, i: int):
    """« à coté » -> « à côté », « des que » -> « dès que », « mauvaise foie »."""
    mot = ctx.mot(i)
    precedent = ctx.mot(i - 1)
    suivant = ctx.mot(i + 1)
    brut = ctx.brut(i)

    if mot in ("coté", "cotés", "cote", "cotes") and precedent in AVANT_COTE:
        if mot.startswith("cote") and precedent not in ("à", "a", "de", "du", "aux"):
            # « ses cotes » (cotations), « mes cotes » : douteux.
            if not mot.endswith("s") or ctx.mot(i - 2) not in ("à", "a", "de"):
                return None
        return appliquer_casse(brut, "côtés" if mot.endswith("s") else "côté")

    if mot == "des" and (suivant in ("que", "lors", "aujourd'hui", "demain",
                                     "maintenant")
                         or ctx.elision(i + 1) == "qu'"
                         or (suivant == "le" and ctx.mot(i + 2) in (
                             "début", "départ", "lendemain", "matin"))):
        return appliquer_casse(brut, "dès")

    if mot in ("fois", "foie") and precedent in ("bonne", "mauvaise") \
            and suivant not in ("pour", "de", "que", "qu'"):
        return appliquer_casse(brut, "foi")
    if mot in ("fois", "foie") and suivant == "en" and ctx.mot(i + 2) in (
            "dieu", "toi", "moi", "lui", "elle", "eux", "vous", "nous", "l'avenir"):
        return appliquer_casse(brut, "foi")

    if mot in ("pêché", "pêchés") and precedent in (
            "un", "le", "les", "ses", "mes", "tes", "des", "nos", "vos",
            "leurs", "son", "mon", "ton", "ce", "ces", "du", "au", "aux"):
        return appliquer_casse(brut, "péché" + ("s" if mot.endswith("s") else ""))

    if mot == "prés" and (suivant in ("de", "du", "des") or ctx.elision(i + 1) == "d'") \
            and precedent not in DETERMINANTS | DETERMINANTS_PLURIELS \
            and not (ctx.morphologie.nom(precedent)
                     and not ctx.morphologie.verbe(precedent)):
        # « les prés du prieuré », « de vastes prés » : les prairies.
        return appliquer_casse(brut, "près")

    if mot == "mêmes" and suivant in ("si", "s'il", "s'ils", "pas", "quand"):
        return appliquer_casse(brut, "même")
    if mot == "mêmes" and ctx.elision(i + 1) == "s'":
        return appliquer_casse(brut, "même")

    if mot == "tout" and suivant in ("deux", "trois", "quatre") \
            and precedent in ("sont", "étaient", "ils", "elles", "nous", "vous",
                              "seront", "êtes", "sommes"):
        return appliquer_casse(brut, "tous")

    if mot == "soit" and precedent == "chez":
        return appliquer_casse(brut, "soi")

    if mot in ("marrons", "oranges") and _est_pluriel(ctx, precedent) \
            and precedent not in ("des", "les", "ces", "mes", "tes", "ses") \
            and ctx.morphologie.nom(precedent):
        return appliquer_casse(brut, mot[:-1])

    if mot == "j'est":
        return appliquer_casse(brut, "j'ai")
    return None


@regle("OU_LIEU_TEMPS", "après un nom de lieu ou de moment, « où » est le relatif")
def _ou_lieu_temps(ctx, i: int):
    """« au moment ou elle est sortie » -> « au moment où », « d'ou viens-tu »."""
    if ctx.noyau(i) != "ou":
        return None
    if ctx.elision(i) in ("d'", "jusqu'"):
        return appliquer_casse(ctx.brut(i), ctx.elision(i) + "où")
    if ctx.elision(i):
        return None
    precedent = ctx.mot(i - 1)
    if precedent in ("par", "d'ici", "jusque"):
        if ctx.mot(i + 1) in PRONOMS_SUJETS or ctx.morphologie.verbe(ctx.mot(i + 1)):
            return appliquer_casse(ctx.brut(i), "où")
        return None
    if precedent not in ("moment", "instant", "jour", "époque", "heure",
                         "année", "soir", "matin", "période", "endroit",
                         "lieu", "minute", "seconde", "nuit"):
        return None
    if ctx.mot(i - 2) not in ("le", "la", "l'", "au", "à", "ce", "cet",
                              "cette", "du", "un", "une", "dès", "depuis") \
            and ctx.elision(i - 1) != "l'":
        return None
    # Un sujet doit suivre : « au moment où il part ». « Un jour ou
    # l'autre », « un soir ou deux » gardent leur conjonction.
    suivant = ctx.mot(i + 1)
    if suivant in PRONOMS_SUJETS or suivant in ("ça", "tout") \
            or ctx.elision(i + 1) in ("j'", "c'", "t'", "s'", "m'", "n'"):
        return appliquer_casse(ctx.brut(i), "où")
    return None


@regle("A_ACCENT_RELATIF", "devant « laquelle », « lequel », c'est la préposition « à »")
def _a_accent_relatif(ctx, i: int):
    """« l'adresse a laquelle » -> « l'adresse à laquelle »."""
    if ctx.mot(i) != "a":
        return None
    if ctx.mot(i + 1) in ("laquelle", "lequel", "lesquels", "lesquelles"):
        return appliquer_casse(ctx.brut(i), "à")
    if ctx.mot(i - 1) in ("dû", "due", "dus", "dues", "grâce", "jusqu'"):
        return appliquer_casse(ctx.brut(i), "à")
    return None


@regle("CE_SONT_EN_TETE", "en tête de phrase, « se sont » est « ce sont »")
def _ce_sont_en_tete(ctx, i: int):
    """« Se sont des histoires » -> « Ce sont des histoires »."""
    if ctx.mot(i) != "se" or not ctx.debut_de_segment(i):
        return None
    if ctx.mot(i + 1) == "sont" and \
            ctx.mot(i + 2) in DETERMINANTS | DETERMINANTS_PLURIELS:
        return appliquer_casse(ctx.brut(i), "ce")
    return None


# ===========================================================================
# Le modele statistique, en dernier recours. Voir « statistique.py ».
# ===========================================================================

from . import statistique as _stat  # noqa: E402

# L'ecart de score exige pour corriger, et le minimum de contextes vus qui
# soutiennent le candidat. Regles sur la part du corpus mise de cote, pour
# qu'un mot juste ne soit touche que tres rarement.
MARGE_STATISTIQUE = 5.0
PREUVES_STATISTIQUE = 3

# Ces ensembles-la se trompent plus souvent que les autres sur le corpus mis
# de cote : on leur demande davantage.
MARGES_PARTICULIERES = {
    "mes": 7.0, "mais": 7.0, "met": 7.0, "mets": 7.0,
    "ces": 6.5, "ses": 6.5, "c'est": 6.5, "s'est": 6.5, "sais": 6.5, "sait": 6.5,
    "on": 6.0, "ont": 6.0,
    "et": 6.0, "est": 6.0,
}

_modele = None
_modele_charge = False


def modele_statistique():
    """Le modele, charge au premier besoin. None s'il n'est pas livre."""
    global _modele, _modele_charge
    if not _modele_charge:
        _modele_charge = True
        try:
            from .chemins import dossier_donnees
            _modele = _stat.Modele.charger(dossier_donnees() / "modele_fr.bin.gz")
        except Exception:                          # noqa: BLE001
            _modele = None
    return _modele


def _suite_du_contexte(ctx):
    """La suite de mots et de ponctuation de la phrase, calculee une fois."""
    suite = getattr(ctx, "_suite_statistique", None)
    if suite is None:
        textes = [j.texte for j in ctx.jetons]
        separateurs = [ctx.texte[ctx.jetons[k].fin:ctx.jetons[k + 1].debut]
                       for k in range(len(ctx.jetons) - 1)]
        if ctx.fin_ouverte:
            separateurs.append("")
        else:
            separateurs.append(ctx.texte[ctx.jetons[-1].fin:] if ctx.jetons else "")
        suite = _stat.sequence(textes, separateurs)
        ctx._suite_statistique = suite
    return suite


@regle("MODELE_STATISTIQUE", "l'usage tranche : c'est ce mot-là qu'on écrit ici")
def _modele_statistique(ctx, i: int):
    """« il a manger » -> « il a mangé », « on va a la plage » -> « à la plage »."""
    modele = modele_statistique()
    if modele is None:
        return None
    mot = ctx.mot(i)
    normal = _stat.normaliser(mot)
    if normal in _stat.ENSEMBLE_DE:
        candidats, classe = _stat.ENSEMBLE_DE[normal], None
    else:
        classe = _stat.classe_verbale(ctx.morphologie, normal)
        if classe is None:
            return None
        candidats = _stat.CLASSES_VERBALES
        normal = classe[0]
    # Le modele lit deux mots de chaque cote. Pendant la frappe, ceux de
    # droite ne sont peut-etre pas encore ecrits : les demander par `mot`
    # le signale, et la proposition est alors ecartee.
    ctx.mot(i + 1)
    ctx.mot(i + 2)
    suite, place = _suite_du_contexte(ctx)
    marge = MARGES_PARTICULIERES.get(normal, MARGE_STATISTIQUE)
    choix = modele.trancher(suite, place[i], normal, candidats,
                            marge, PREUVES_STATISTIQUE)
    if choix is None or _veto_statistique(ctx, i, normal, choix):
        return None
    if classe is not None:
        forme = _stat.forme_de_classe(ctx.morphologie, classe[1], choix, mot)
        if forme is None or forme == mot:
            return None
        return appliquer_casse(ctx.brut(i), forme)
    return appliquer_casse(ctx.brut(i), choix)


def _sujet_possible(ctx, k: int) -> bool:
    """Le mot en position k peut-il etre le sujet du verbe qui suit ?"""
    mot = ctx.noyau(k)
    if not mot:
        return False
    if mot in PRONOMS_SUJETS or mot in ("ça", "cela", "qui", "on", "tout",
                                        "personne", "rien", "chacun"):
        return True
    if ctx.brut(k)[:1].isupper():
        return True
    return ctx.morphologie.nom(mot) and not ctx.morphologie.verbe(mot)


def _veto_statistique(ctx, i: int, ecrit: str, choix: str) -> bool:
    """Ce que deux mots de contexte ne voient pas, dit par la grammaire.

    Le modele ne lit que deux mots de chaque cote. « Paul a la clé » et « on
    va a la plage » lui paraissent pareils ; c'est le mot d'avant — un sujet,
    ou un verbe — qui les distingue. Chaque veto ici vient d'une erreur vue
    sur le banc LanguageTool.
    """
    suivant = ctx.mot(i + 1)
    precedent_sep = ctx.separateur(i - 1) if i > 0 else ""
    if ecrit == "a" and choix == "à":
        # « Paul a la clé », « chaque photo a son histoire » : un sujet devant.
        if _sujet_possible(ctx, i - 1):
            return True
        # « puis a jailli », « n'a rien » : ce qui suit est celui d'avoir.
        if ctx.est_participe(suivant) or suivant in ("rien", "pas", "plus",
                                                      "jamais", "été", "eu"):
            return True
        # « sa voix enregistrée a la sensation » : la fin du groupe sujet.
        precedent = ctx.mot(i - 1)
        if ctx.est_participe(precedent) and not ctx.morphologie.verbe(precedent):
            return True
        # « si a existe », « a≥b », « a) » : une lettre, pas une preposition.
        if len(suivant) <= 1 or ctx.separateur(i) != " ":
            return True
    if ecrit == "ou" and choix == "où":
        # « il a existé ou il existe encore » : deux verbes coordonnes.
        if suivant in PRONOMS_SUJETS and (
                ctx.est_participe(ctx.mot(i - 1))
                or ctx.morphologie.verbe(ctx.mot(i - 1))
                or ctx.morphologie.est(ctx.mot(i - 1), "inf")):
            return True
    if ecrit == "se" and choix == "ce":
        # « qui se ressemble se gène » : « se » devant un verbe est a sa place.
        if ctx.morphologie.verbe(suivant) or ctx.morphologie.est(suivant, "inf"):
            return True
    if ecrit == "sont" and choix == "son":
        # « le repentir sont frère et sœur », « sont exceptés » : un sujet
        # devant, ou un participe derriere.
        if _sujet_possible(ctx, i - 1) or ctx.est_participe(suivant) \
                or ctx.debut_de_segment(i):
            return True
    if ecrit == "et" and choix == "est":
        # « connectés et lancée », « mémorable et amusant » : une
        # coordination d'adjectifs ou de participes.
        precedent = ctx.mot(i - 1)
        if ctx.est_participe(precedent) or _est_adjectif(ctx, precedent):
            return True
    if ecrit == "la" and choix == "là":
        # « supportez-la », « mange la » : le pronom apres un verbe.
        precedent = ctx.mot(i - 1)
        if (ctx.morphologie.verbe(precedent) or "i2p" in ctx.morphologie.traits(precedent)
                or "i2s" in ctx.morphologie.traits(precedent)) \
                and precedent not in ("est", "sont", "suis", "es", "était", "sera"):
            return True
    if ecrit in ("mets", "met") and choix == "mais":
        # « mets la bouilloire » : un imperatif devant son complement.
        if suivant in DETERMINANTS or suivant in DETERMINANTS_PLURIELS:
            return True
    if "-" in precedent_sep or "/" in precedent_sep:
        # « grimpeur/se », « peut-être » : un morceau de mot compose.
        return True
    return False
