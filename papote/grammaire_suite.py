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
    suivant = ctx.mot(i + 1)
    if not _voyelle_initiale(suivant) or not ctx.connait(suivant):
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
    if not (_est_adjectif(ctx, mot) or ctx.est_participe(mot)):
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
