# -*- coding: utf-8 -*-
"""Qui est le sujet de quel verbe.

Les regles d'accord regardaient deux ou trois mots autour du verbe. Elles
voyaient « les gens pense », mais pas :

    les enfants dans le jardin joue          un complement s'intercale
    le prix des maisons baissent             le nom le plus proche n'est pas le sujet
    l'enfant que j'accompagne ... arrivent   une relative s'intercale
    ils semblent avoir été attaqué           l'attribut est loin du sujet
    cette femme et cet homme sont courtois   deux sujets coordonnes

Ce module remonte du verbe jusqu'a son sujet, en sautant ce qui se glisse
entre eux : pronoms complements, groupes prepositionnels, relatives. Ce
n'est pas un analyseur complet de la phrase : il ne repond que quand le
chemin est sans ambiguite, et se tait sinon. Une regle d'accord qui se tait
laisse une faute ; une regle qui se trompe en fabrique une.

Deux questions, et deux regles qui s'en servent (en bas du fichier) :

- `sujet_du_verbe(ctx, i)` : le sujet du verbe conjugue en position i ;
- `sujet_de_l_attribut(ctx, i)` : le sujet auquel s'accorde l'adjectif ou
  le participe en position i (« elles semblent être **parties** »).
"""

from __future__ import annotations

from dataclasses import dataclass

from .grammaire import (
    CHARNIERES, COULEURS, INVARIABLES_ADJECTIFS, MOTS_INVARIABLES, NOMBRES_PLURIELS,
    OUVRANTS, PRONOMS_SUJETS, QUANTITES, Contexte, _adjectif_antepose,
    _apres_preposition, _couleur_composee, _est_adjectif, _sujet_inverse, accorder_le_verbe, appliquer_casse,
    regle,
)
from .morphologie import CONJUGUES, NOMINAUX


@dataclass(frozen=True)
class Sujet:
    personne: str            # « 1s » ... « 3p »
    genre: str | None        # « m », « f », ou None quand rien ne le dit
    debut: int               # premier mot du sujet
    pronom: bool = False     # un pronom personnel (« il »), pas un groupe

    @property
    def nombre(self) -> str:
        return self.personne[1]


PERSONNES = {"je": "1s", "tu": "2s", "il": "3s", "elle": "3s", "on": "3s",
             "nous": "1p", "vous": "2p", "ils": "3p", "elles": "3p"}
GENRES_PRONOMS = {"il": "m", "ils": "m", "elle": "f", "elles": "f"}

# Les pronoms qui se glissent entre le sujet et le verbe.
CLITIQUES = {"ne", "n'", "me", "m'", "te", "t'", "se", "s'", "le", "la", "les",
             "l'", "lui", "leur", "y", "en", "nous", "vous"}

# Sujets a la 3e personne qui ne sont pas des groupes nominaux.
SUJETS_SINGULIERS = {"ça", "cela", "ceci", "rien", "chacun", "chacune",
                     "quelqu'un", "personne", "tout", "celui-ci", "celle-ci",
                     "celui-là", "celle-là"}
SUJETS_PLURIELS = {"certains": "m", "certaines": "f", "plusieurs": None,
                   "ceux-ci": "m", "celles-ci": "f",
                   "ceux-là": "m", "celles-là": "f"}

# Les antecedents de « qui » qui ne sont pas des groupes nominaux.
ANTECEDENTS = {"moi": ("1s", None), "toi": ("2s", None), "lui": ("3s", "m"),
               "elle": ("3s", "f"), "nous": ("1p", None), "vous": (None, None),
               "eux": ("3p", "m"), "elles": ("3p", "f"), "ce": ("3s", None),
               "celui": ("3s", "m"), "celle": ("3s", "f"), "ceux": ("3p", "m"),
               "celles": ("3p", "f")}

DETERMINANTS_SINGULIERS = {
    "le": "m", "la": "f", "l'": None, "un": "m", "une": "f", "ce": "m",
    "cet": "m", "cette": "f", "mon": None, "ton": None, "son": None,
    "ma": "f", "ta": "f", "sa": "f", "notre": None, "votre": None,
    "leur": None, "chaque": None, "aucun": "m", "aucune": "f", "nul": "m",
    "nulle": "f", "du": "m", "au": "m",
}
# « Quels gestes accomplit un humaniste ? », « Du tronc poussent les
# branches » : ces groupes-la ne sont pas des sujets, le vrai sujet suit.
DETERMINANTS_HORS_SUJET = {"du", "au", "aux", "quel", "quelle", "quels",
                           "quelles"}
PREDETERMINANTS = {"tout", "toute", "tous", "toutes"}
DETERMINANTS_PLURIELS_GENRES = {
    "les": None, "des": None, "ces": None, "mes": None, "tes": None,
    "ses": None, "nos": None, "vos": None, "leurs": None, "aux": None,
    "plusieurs": None, "quelques": None, "certains": "m", "certaines": "f",
    "différents": "m", "différentes": "f", "divers": "m", "diverses": "f",
    "quels": "m", "quelles": "f", "quel": "m", "quelle": "f",
    "nombreux": "m", "nombreuses": "f",
}

# Ce qui rattache un complement au nom qui le precede : « les enfants **dans**
# le jardin », « le prix **des** maisons ».
LIENS = {"de", "d'", "du", "des", "à", "au", "aux", "en", "dans", "sur",
         "sous", "pour", "avec", "sans", "entre", "chez", "contre", "vers",
         "parmi", "par", "près", "auprès", "envers", "après", "avant",
         "devant", "derrière", "selon", "depuis", "pendant"}
# Parmi eux, ceux qui sont aussi des articles : « des » ouvre un groupe.
LIENS_ARTICLES = {"du", "des", "au", "aux"}

# Les noms de quantite dont l'accord hesite : « une foule de gens est venue »
# et « sont venus » sont justes tous les deux. On ne tranche pas.
COLLECTIFS = {"nombre", "foule", "groupe", "majorité", "minorité", "moitié",
              "tiers", "quart", "partie", "reste", "ensemble", "totalité",
              "dizaine", "douzaine", "quinzaine", "vingtaine", "trentaine",
              "quarantaine", "cinquantaine", "centaine", "millier", "million",
              "milliard", "masse", "multitude", "tas", "série", "poignée",
              "infinité", "plupart", "bande", "troupe", "équipe", "famille",
              "couple", "paire", "pourcentage", "proportion", "type", "sorte",
              "genre", "espèce", "variété", "majeure", "part", "nombreux",
              "kyrielle", "flopée", "ribambelle", "foultitude", "lot"}

# Ce qui peut ouvrir une proposition avant son sujet.
OUVERTURES = OUVRANTS | CHARNIERES | {
    "lorsqu'", "puisqu'", "quoique", "bien", "tandis", "pendant", "dès",
    "aussitôt", "afin", "pour", "sans", "avant", "après", "depuis", "ainsi",
    "d'ailleurs", "aussi", "néanmoins", "cependant", "toutefois", "or",
    "hier", "aujourd'hui", "demain", "maintenant", "désormais", "parfois",
    "souvent", "soudain", "ensuite", "finalement", "heureusement",
    "malheureusement", "évidemment", "certes", "peut-être", "sûrement",
}
# Parmi elles, celles qui ne sont des ouvertures que suivies de « que » : « pour
# que les gens viennent », mais « pour les gens » est un complement.
OUVERTURES_AVEC_QUE = {"bien", "tandis", "pendant", "dès", "aussitôt", "afin",
                       "pour", "sans", "avant", "après", "depuis", "parce"}

DUREES = {"jour", "journée", "nuit", "matin", "matinée", "soir", "soirée",
          "semaine", "mois", "année", "an", "heure", "minute", "seconde",
          "fois", "temps", "été", "hiver", "printemps", "automne", "siècle",
          "moment", "instant", "période", "saison", "week-end", "décennie"}

RELATIFS = {"qui", "que", "qu'", "dont", "où", "lequel", "laquelle",
            "lesquels", "lesquelles", "auquel", "auxquels", "auxquelles",
            "duquel", "desquels", "desquelles"}

PERSONNES_FINIES = frozenset({"1s", "2s", "3s", "1p", "2p", "3p"})


# ---------------------------------------------------------------------------
# Le groupe nominal
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Groupe:
    debut: int
    tete: int
    nombre: str | None       # « s », « p », ou None si on ne sait pas
    genre: str | None


def _nominal(ctx: Contexte, mot: str) -> bool:
    return bool(ctx.morphologie.traits(mot) & NOMINAUX)


def _nombre_du_mot(ctx: Contexte, mot: str) -> str | None:
    traits = ctx.morphologie.traits(mot) & NOMINAUX
    singulier = bool(traits & {"ms", "fs", "xs"})
    pluriel = bool(traits & {"mp", "fp", "xp"})
    if singulier and not pluriel:
        return "s"
    if pluriel and not singulier:
        return "p"
    return None


def _nombre_cardinal(mot: str) -> str | None:
    if mot.isdigit():
        return "s" if mot in ("0", "1") else "p"
    if mot in NOMBRES_PLURIELS or (
            "-" in mot and mot.split("-")[-1] in NOMBRES_PLURIELS | {"un", "deux"}):
        return "p"
    return None


MOTS_OUTILS = (set(DETERMINANTS_SINGULIERS) | set(DETERMINANTS_PLURIELS_GENRES)
               | set(ANTECEDENTS) | RELATIFS | OUVERTURES | CLITIQUES
               | {"ce", "ça", "cela", "ceci", "se", "si", "tout", "tous"})


def _nom_propre(ctx: Contexte, k: int) -> bool:
    """« Marie », « Dominique », « la Corée » : un mot a majuscule qui
    n'est pas le premier mot de la phrase, ou que le dictionnaire ignore
    en minuscules."""
    brut = ctx.brut(k)
    if not brut[:1].isupper() or ctx.mot(k) in PRONOMS_SUJETS:
        return False
    if ctx.mot(k) in MOTS_OUTILS or ctx.noyau(k) in MOTS_OUTILS \
            or ctx.elision(k) not in ("", "l'"):
        return False
    if not ctx.debut_de_segment(k):
        return True
    return not ctx.morphologie.connait(ctx.mot(k)) and not ctx.connait(ctx.mot(k))


def groupe_finissant(ctx: Contexte, k: int) -> Groupe | None:
    """Le groupe nominal simple qui se termine en position k.

        [determinant] [adjectifs] nom [adjectifs]

    ou un nom propre. Un seul groupe, sans ses complements : c'est
    `chaine_finissant` qui les assemble.
    """
    mot = ctx.mot(k)
    if not mot or ctx.elision(k) not in ("", "l'", "d'"):
        return None
    noyau = ctx.noyau(k)
    if _nom_propre(ctx, k):
        debut = k
        # « Jean Dupont », « la Corée », « le Père Noël ».
        while debut - 1 >= 0 and _nom_propre(ctx, debut - 1) \
                and not ctx.separateur(debut - 1).strip():
            debut -= 1
        precedent = ctx.mot(debut - 1)
        if precedent in DETERMINANTS_SINGULIERS and not ctx.separateur(debut - 1).strip():
            return Groupe(debut - 1, k, "s", DETERMINANTS_SINGULIERS[precedent])
        if precedent in DETERMINANTS_PLURIELS_GENRES and precedent not in ("des", "aux"):
            return Groupe(debut - 1, k, "p", None)
        if ctx.elision(debut) == "l'":
            return Groupe(debut, k, "s", None)
        return Groupe(debut, k, "s", None)
    if not _nominal(ctx, noyau) or noyau in MOTS_INVARIABLES:
        return None

    # Le nom est-il en position k, ou un adjectif qui le suit ?
    tete = k
    j = k
    if ctx.elision(k) == "l'":
        return Groupe(k, k, "s", _genre_du_groupe(ctx, k, None))
    # Les adjectifs postposes : on remonte tant que le mot d'avant est un nom
    # ou un adjectif sans determinant entre eux.
    while True:
        precedent = ctx.mot(j - 1)
        if not precedent or ctx.separateur(j - 1).strip():
            break
        if precedent in DETERMINANTS_SINGULIERS or precedent in DETERMINANTS_PLURIELS_GENRES \
                or _nombre_cardinal(precedent) or ctx.elision(j - 1) == "l'":
            break
        if not _nominal(ctx, ctx.noyau(j - 1)) or precedent in MOTS_INVARIABLES \
                or ctx.elision(j - 1):
            return None
        # « le temps passe », « des sociétés nouvellement » : un verbe ou un
        # adverbe n'est pas un adjectif du groupe.
        dernier = ctx.noyau(j)
        if ctx.morphologie.traits(dernier) & PERSONNES_FINIES or dernier.endswith("ment"):
            return None
        j -= 1
        if k - j > 3:
            return None
    # j est le premier mot nominal du groupe ; il faut un determinant devant
    # (ou une elision « l' » sur j).
    debut = j
    if ctx.elision(j) == "l'":
        nombre, genre_det = "s", None
    else:
        det = ctx.mot(j - 1)
        if det in DETERMINANTS_SINGULIERS and det not in ("du", "au"):
            nombre, genre_det = "s", DETERMINANTS_SINGULIERS[det]
            debut = j - 1
        elif det in ("quel", "quelle"):
            nombre, genre_det = "s", DETERMINANTS_PLURIELS_GENRES[det]
            debut = j - 1
        elif det in DETERMINANTS_PLURIELS_GENRES:
            nombre, genre_det = "p", DETERMINANTS_PLURIELS_GENRES[det]
            debut = j - 1
        elif _nombre_cardinal(det):
            nombre, genre_det = _nombre_cardinal(det), None
            debut = j - 1
            if ctx.mot(j - 2) in DETERMINANTS_PLURIELS_GENRES:
                debut = j - 2
        elif det in ("du", "au"):
            nombre, genre_det = "s", "m"
            debut = j - 1
        else:
            return None
        if ctx.separateur(j - 1).strip():
            return None
        # « tous ces caractères » : le predeterminant fait partie du groupe.
        if ctx.mot(debut - 1) in PREDETERMINANTS and not ctx.separateur(debut - 1).strip():
            debut -= 1

    # La tete : le premier mot du groupe qui n'est pas un adjectif antepose.
    tete = j
    while tete < k and _adjectif_antepose(ctx.noyau(tete)):
        tete += 1
    nom = ctx.noyau(tete)
    # Le nombre du nom doit confirmer celui du determinant, quand il le dit.
    nombre_nom = _nombre_du_mot(ctx, nom)
    if nombre_nom and nombre_nom != nombre and not (nom in ("gens",)):
        return None
    genre = _genre_du_groupe(ctx, tete, genre_det)
    return Groupe(debut, tete, nombre, genre)


def _genre_du_groupe(ctx: Contexte, tete: int, genre_det: str | None) -> str | None:
    traits = ctx.morphologie.traits(ctx.noyau(tete)) & NOMINAUX
    if traits & {"ms", "mp"} and not traits & {"fs", "fp", "xs", "xp"}:
        return "m"
    if traits & {"fs", "fp"} and not traits & {"ms", "mp", "xs", "xp"}:
        return "f"
    if genre_det:
        return genre_det
    from .genres import genre

    lemmes = ctx.morphologie.lemmes(ctx.noyau(tete))
    return genre(lemmes[0] if lemmes else ctx.noyau(tete))


def chaine_finissant(ctx: Contexte, k: int) -> Groupe | None:
    """Le groupe nominal complet qui finit en k, complements compris.

    « le prix des maisons » : le groupe qui finit en « maisons » est « des
    maisons » ; devant lui, « prix » qu'il complete. On remonte jusqu'au
    premier nom de la chaine, qui en est la tete, et c'est elle qui accorde
    le verbe.
    """
    groupe = groupe_finissant(ctx, k)
    if groupe is None:
        # « beaucoup de gens », « trop de bruit » : la quantite tient lieu
        # de determinant.
        if ctx.mot(k - 1) in ("de", "d'") or ctx.elision(k) == "d'":
            avant = k - 1 if ctx.elision(k) == "d'" else k - 2
            nombre = _nombre_du_mot(ctx, ctx.noyau(k))
            if ctx.mot(avant) in QUANTITES and nombre \
                    and ctx.mot(avant) not in ("plupart", "combien", "plus", "moins") \
                    and ctx.noyau(k) not in MOTS_OUTILS:
                return Groupe(avant, k, nombre, _genre_du_groupe(ctx, k, None))
        return None
    tete_initiale = groupe.tete
    for _ in range(4):
        debut = groupe.debut
        lien = ctx.mot(debut)
        if lien in LIENS_ARTICLES:
            # « des maisons » : « des » est a la fois lien et article.
            avant = debut - 1
        else:
            lien = ctx.mot(debut - 1)
            if lien not in LIENS and ctx.elision(debut) != "d'":
                break
            avant = debut - 2 if ctx.elision(debut) != "d'" else debut - 1
            if ctx.elision(debut) == "d'":
                lien = "d'"
        if avant < 0 or ctx.separateur(avant).strip() \
                or ctx.separateur(debut - 1).strip():
            break
        precedent = groupe_finissant(ctx, avant)
        if precedent is None:
            # « beaucoup de gens », « la plupart des gens » : la quantite
            # donne le nombre du groupe qu'elle introduit.
            if lien in ("de", "d'", "des") and ctx.mot(avant) in QUANTITES \
                    and ctx.mot(avant) != "combien":
                return Groupe(avant, groupe.tete, groupe.nombre, groupe.genre)
            if lien == "des" and ctx.mot(avant) in ("un", "une") or \
                    ctx.noyau(avant) in ("un", "une") and ctx.elision(avant) == "l'":
                # « un des enfants », « l'une des filles » : singulier.
                return Groupe(avant, avant, "s", "f" if ctx.noyau(avant) == "une" else None)
            return None
        groupe = precedent
    if ctx.noyau(groupe.tete) in COLLECTIFS:
        return None
    if groupe.tete != tete_initiale and ctx.noyau(groupe.tete) in DUREES:
        # « Toute la journée des trains passent » : « des trains » est le
        # sujet, la duree est un complement de temps.
        return None
    return groupe


# Ce qui, devant « que », en fait une comparaison et non une subordonnee :
# « plus grand que les autres m'a offert », « en même temps que leur flair ».
COMPARATIFS = {"plus", "moins", "aussi", "autant", "mieux", "pire", "même",
               "autre", "autres", "tel", "telle", "tels", "telles", "si",
               "tant", "davantage", "plutôt", "ainsi", "avant", "sinon", "rien",
               "ne", "n'"}

# Les abreviations qui finissent par un point sans finir la phrase.
ABREVIATIONS = {"m", "mm", "mme", "mmes", "mlle", "mlles", "dr", "pr", "me",
                "st", "ste", "cf", "etc", "p", "vol", "chap", "art", "no", "n"}


def _que_subordonnant(ctx: Contexte, k: int) -> bool:
    """« que » en k ouvre-t-il une proposition ? Pas apres un comparatif."""
    for recul in range(1, 5):
        mot = ctx.noyau(k - recul)
        if not mot or ctx.separateur(k - recul).strip():
            return True
        if mot in COMPARATIFS:
            return False
    return True


def _ouvre_une_proposition(ctx: Contexte, debut: int) -> bool:
    """Le groupe qui commence en `debut` est-il en tete de proposition ?"""
    if ctx.debut_de_segment(debut):
        return _vraie_tete(ctx, debut)
    if ctx.elision(debut) == "qu'":
        return _que_subordonnant(ctx, debut)
    precedent = ctx.mot(debut - 1)
    if precedent in ("que", "qu'") or (ctx.elision(debut - 1) in ("qu'", "lorsqu'", "puisqu'")
                                      and not ctx.noyau(debut - 1)):
        return _que_subordonnant(ctx, debut - 1)
    if precedent in OUVERTURES_AVEC_QUE or precedent in PREDETERMINANTS:
        return False
    if precedent in OUVERTURES:
        # « hier les enfants » : l'adverbe doit lui-meme ouvrir la phrase.
        if precedent in OUVRANTS or precedent in CHARNIERES:
            return precedent not in ("et", "ou") or ctx.debut_de_segment(debut - 1)
        return ctx.debut_de_segment(debut - 1)
    return False


def _vraie_tete(ctx: Contexte, debut: int) -> bool:
    """Le groupe ouvre un segment ; est-ce bien le debut d'une proposition ?

    « L'amour, l'amitié, la vie sont là » : apres une virgule, un groupe peut
    etre le dernier d'une enumeration. « M. Sénèque » : le point d'une
    abreviation ne finit pas la phrase.

    Apres une virgule, on n'accepte que ce qu'on sait lire devant elle : un
    complement introduit par une preposition (« Après son régime, »), une
    subordonnee (« Quand il pleut, »), un adverbe (« Ensuite, »).
    """
    if debut == 0:
        return True
    separateur = ctx.separateur(debut - 1)
    avant = ctx.mot(debut - 1)
    if "." in separateur and avant in ABREVIATIONS:
        return False
    if any(c in separateur for c in ",;(—«\"“"):
        if "," not in separateur or any(c in separateur for c in ";(—«\"“"):
            return False
    else:
        return True
    for recul in range(1, 4):
        if ctx.mot(debut - recul) in ("et", "ou", "ni", "puis"):
            return False
    # Le debut du segment precedent.
    s0 = debut - 1
    while s0 > 0 and not ctx.debut_de_segment(s0):
        s0 -= 1
    premier = ctx.mot(s0)
    if ctx.elision(s0) in ("qu'", "lorsqu'", "puisqu'", "jusqu'"):
        return True
    if premier in LIENS | OUVERTURES | {"malgré", "lors", "grâce", "quant",
                                         "suite", "faute", "contrairement"}:
        return True
    return False


# ---------------------------------------------------------------------------
# Le sujet d'un verbe
# ---------------------------------------------------------------------------

def _sujet_au_bout(ctx: Contexte, k: int) -> Sujet | None:
    """Le sujet qui se termine en position k, juste avant le verbe."""
    mot = ctx.mot(k)
    noyau = ctx.noyau(k)
    if not mot:
        return None

    if noyau in PERSONNES and ctx.elision(k) in ("", "qu'", "lorsqu'", "puisqu'"):
        if _sujet_inverse(ctx, k):
            return None
        if ctx.elision(k) == "" and ctx.mot(k - 1) in ("et", "ou", "ni") \
                and not ctx.separateur(k - 1).strip():
            # « lui et elle sont partis » : le pronom est coordonne.
            return None
        if _apres_preposition(ctx, k) or (ctx.elision(k) == "" and ctx.mot(k - 1) in LIENS):
            # « avec elles », « l'une d'entre elles » : complement, pas sujet.
            return None
        return Sujet(PERSONNES[noyau], GENRES_PRONOMS.get(noyau), k, pronom=True)

    if mot in SUJETS_SINGULIERS:
        if not _ouvre_une_proposition(ctx, k):
            return None
        return Sujet("3s", None, k, pronom=True)
    if mot in SUJETS_PLURIELS and ctx.debut_de_segment(k):
        if not _vraie_tete(ctx, k):
            return None
        return Sujet("3p", SUJETS_PLURIELS[mot], k, pronom=True)

    if mot == "qui":
        return _antecedent(ctx, k)

    groupe = chaine_finissant(ctx, k)
    if groupe is None:
        return None
    return _sujet_du_groupe(ctx, groupe, exiger_la_tete=True)


def _sujet_du_groupe(ctx: Contexte, groupe: Groupe, exiger_la_tete: bool) -> Sujet | None:
    """Le groupe, et ce qui lui est coordonne devant : « cette femme et cet
    homme », « lui et son staff ». Le genre d'un sujet coordonne n'est dit
    que s'il comporte un masculin."""
    if groupe.nombre is None or ctx.mot(groupe.debut) in DETERMINANTS_HORS_SUJET \
            or ctx.elision(groupe.debut) == "d'":
        return None
    # « Leur taux sont arrivés » : « leur » se confond avec « leurs ».
    if ctx.mot(groupe.debut) == "leur":
        return None
    debut, nombre, genre = groupe.debut, groupe.nombre, groupe.genre
    if ctx.mot(debut - 1) == "et" and not ctx.separateur(debut - 1).strip():
        autre = _membre_coordonne(ctx, debut - 2)
        if autre is None:
            return None
        if "chaque" in (ctx.mot(debut), ctx.mot(autre.debut)):
            # « Chaque service et chaque application est unique. »
            return None
        debut, nombre = autre.debut, "p"
        genre = "m" if "m" in (genre, autre.genre) else None
    elif ctx.mot(debut - 1) in ("ou", "ni", "puis", "comme", "avec") \
            and not ctx.debut_de_segment(debut - 1):
        # « le Minitel puis Internet », « les gens comme Tom ».
        return None
    if ctx.mot(debut) in DETERMINANTS_HORS_SUJET:
        return None
    if exiger_la_tete and not _ouvre_une_proposition(ctx, debut):
        return None
    return Sujet("3" + nombre, genre, debut)


def _membre_coordonne(ctx: Contexte, k: int) -> Groupe | None:
    """Le premier membre d'une coordination : un groupe simple, sans
    complement. « une nation avec une armée et une volonté » : « une armée »
    complete « nation », il n'est pas sujet."""
    mot = ctx.mot(k)
    if mot in ANTECEDENTS and mot not in ("ce", "vous", "nous"):
        personne, genre = ANTECEDENTS[mot]
        if ctx.mot(k - 1) in LIENS:
            return None
        return Groupe(k, k, personne[1], genre)
    groupe = groupe_finissant(ctx, k)
    if groupe is None or groupe.nombre is None:
        return None
    chaine = chaine_finissant(ctx, k)
    if chaine is None or chaine.debut != groupe.debut:
        return None
    if ctx.mot(groupe.debut - 1) in LIENS or ctx.elision(groupe.debut) == "d'":
        return None
    return groupe


def _antecedent(ctx: Contexte, k: int) -> Sujet | None:
    """Le sujet de « qui » : ce qu'il reprend."""
    if k == 0:
        return None
    separateur = ctx.separateur(k - 1).strip()
    if separateur not in ("", ","):
        return None
    precedent = ctx.mot(k - 1)
    if precedent in ANTECEDENTS:
        personne, genre = ANTECEDENTS[precedent]
        if personne is None or separateur or ctx.mot(k - 2) in DETERMINANTS_SINGULIERS:
            # « un moi qui lui est propre » : un nom, pas le pronom.
            return None
        if ctx.mot(k - 2) in LIENS or ctx.mot(k - 2).startswith("d'") \
                or ctx.mot(k - 2) in ("et", "ou", "ni", "que"):
            # « l'animal en moi qui le veut », « Christine et moi qui ».
            return None
        return Sujet(personne, genre, k - 1)
    groupe = groupe_finissant(ctx, k - 1)
    if groupe is None or groupe.nombre is None:
        return None
    # « le fils de la voisine qui ... » : l'antecedent peut etre l'un ou
    # l'autre. On ne repond que si la chaine n'a qu'un groupe, ou que tous
    # ses noms ont le meme nombre et le meme genre.
    chaine = chaine_finissant(ctx, k - 1)
    if chaine is None:
        return None
    if chaine.debut != groupe.debut and (chaine.nombre != groupe.nombre
                                          or chaine.genre != groupe.genre):
        return None
    if ctx.mot(chaine.debut - 1) in ("et", "ou", "ni", ","):
        # « Tesla et Westinghouse qui » : on ne sait pas jusqu'ou remonte
        # la coordination.
        return None
    if ctx.mot(chaine.debut) in DETERMINANTS_HORS_SUJET:
        return None
    # « un hôtel 3 étoiles qui », « mon père, 79 ans qui » : le nombre
    # mesure le nom d'avant, qui est l'antecedent.
    if _nombre_cardinal(ctx.mot(chaine.debut)):
        return None
    # « ceux qui nient son existence qui contribuent » : un groupe objet
    # d'une relative n'est pas sur d'etre l'antecedent du « qui » suivant.
    if ctx.mot(chaine.debut - 2) == "qui" and _verbe_fini_sur(ctx, chaine.debut - 1):
        return None
    if separateur and ctx.mot(chaine.debut - 1) in ("et", "ou"):
        return None
    return Sujet("3" + groupe.nombre, groupe.genre, chaine.debut)


def _verbe_fini_sur(ctx: Contexte, k: int) -> bool:
    """Un verbe conjugue qui ne peut pas etre un nom : « voile » ne compte
    pas, « dissimule » si — ni « as », sauf derriere « tu »."""
    traits = ctx.morphologie.traits(ctx.noyau(k))
    if not traits & PERSONNES_FINIES:
        return False
    if not traits & NOMINAUX:
        return True
    precedent = ctx.noyau(k - 1)
    return precedent in PERSONNES and PERSONNES[precedent] in traits \
        and not ctx.separateur(k - 1).strip()


def _relative_avant(ctx: Contexte, k: int) -> Sujet | None:
    """« l'enfant que j'accompagne souvent à la bibliothèque arrivent » :
    une relative complete s'intercale entre le sujet et son verbe.

    On cherche, a moins de douze mots, un relatif precede d'un groupe en tete
    de proposition, et suivi d'un verbe conjugue sans ambiguite.
    """
    # Un sujet ne finit ni par une preposition ni par un article : « sur
    # n'importe qui » n'est pas la fin d'une relative.
    if ctx.mot(k) in LIENS or ctx.mot(k) in DETERMINANTS_SINGULIERS \
            or ctx.mot(k) in DETERMINANTS_PLURIELS_GENRES:
        return None
    for r in range(k, max(-1, k - 12), -1):
        if r != k and ctx.separateur(r).strip():
            return None
        mot = ctx.mot(r)
        if mot in ("qui", "que", "dont"):
            premier = r + 1
        elif ctx.elision(r) == "qu'" and ctx.noyau(r) in PERSONNES:
            premier = r + 1
        else:
            continue
        if mot == "que" and not _que_subordonnant(ctx, r):
            return None
        if not any(_verbe_fini_sur(ctx, v) for v in range(premier, k + 1)):
            return None
        antecedent = groupe_finissant(ctx, r - 1)
        if antecedent is None or antecedent.nombre is None:
            return None
        chaine = chaine_finissant(ctx, r - 1)
        if chaine is None:
            return None
        return _sujet_du_groupe(ctx, chaine, exiger_la_tete=True)
    return None


def sujet_du_verbe(ctx: Contexte, i: int) -> Sujet | None:
    """Le sujet du verbe conjugue en position i, ou None si on ne sait pas."""
    cache = ctx.__dict__.setdefault("_sujets", {})
    if i not in cache:
        cache[i] = _chercher_sujet(ctx, i)
    return cache[i]


CLITIQUES_ELIDES = {"n'y", "n'en", "m'y", "m'en", "t'en", "t'y", "s'en", "s'y",
                    "l'y", "l'en"}


def _chercher_sujet(ctx: Contexte, i: int) -> Sujet | None:
    elision = ctx.elision(i)
    if elision == "j'":
        return Sujet("1s", None, i, pronom=True)
    if elision in ("c'", "ç'", "qu'", "d'"):
        return None
    if i == 0 or "-" in ctx.separateur(i - 1):
        return None
    if ctx.debut_de_segment(i):
        # « Les enfants, qui lui a dit cela, sont » : la relative entre
        # virgules est sautee.
        if ctx.separateur(i - 1).strip() == ",":
            return _apres_une_incise(ctx, i - 1)
        return None
    # Les pronoms complements et la negation : « ils ne le lui disent pas ».
    k = i - 1
    while k >= 0 and (ctx.mot(k) in CLITIQUES or ctx.mot(k) in CLITIQUES_ELIDES) \
            and not ctx.separateur(k).strip():
        if ctx.mot(k) in ("nous", "vous") and _peut_etre_sujet(ctx, k):
            break
        k -= 1
    if k < 0 or ctx.separateur(k).strip():
        return None
    sujet = _sujet_au_bout(ctx, k)
    if sujet is not None:
        return sujet
    return _relative_avant(ctx, k)


def _peut_etre_sujet(ctx: Contexte, k: int) -> bool:
    """« nous » ou « vous » en k sont-ils le sujet ?"""
    if ctx.debut_de_segment(k):
        return True
    precedent = ctx.mot(k - 1)
    return precedent in OUVRANTS or precedent in CHARNIERES or (
        ctx.elision(k - 1) == "qu'" and not ctx.noyau(k - 1))


def _apres_une_incise(ctx: Contexte, k: int) -> Sujet | None:
    """« Les enfants, qui lui a dit cela, sont » : on remonte l'incise."""
    for r in range(k - 1, max(-1, k - 15), -1):
        if ctx.separateur(r).strip():
            if ctx.separateur(r).strip() != ",":
                return None
            if ctx.mot(r + 1) not in ("qui", "que", "dont", "où") \
                    and ctx.elision(r + 1) != "qu'":
                return None
            groupe = chaine_finissant(ctx, r)
            if groupe is None:
                return None
            sujet = _sujet_du_groupe(ctx, groupe, exiger_la_tete=True)
            if sujet is None:
                return None
            return sujet
    return None


# ---------------------------------------------------------------------------
# L'attribut et son sujet
# ---------------------------------------------------------------------------

COPULES = {"être", "sembler", "paraître", "devenir", "redevenir", "rester",
           "demeurer"}
PARTICIPES_COPULES = {"été", "devenu", "devenus", "devenue", "devenues",
                      "redevenu", "redevenus", "redevenue", "redevenues",
                      "resté", "restés", "restée", "restées", "demeuré"}

ADVERBES = {
    "pas", "plus", "jamais", "point", "guère", "très", "trop", "si", "assez",
    "vraiment", "complètement", "totalement", "tout", "toute", "toutes",
    "bien", "aussi", "peu", "moins", "encore", "toujours", "déjà", "souvent",
    "presque", "tellement", "fort", "extrêmement", "particulièrement",
    "parfaitement", "entièrement", "absolument", "réellement", "plutôt",
    "vite", "enfin", "probablement", "certainement", "sûrement", "parfois",
    "rarement", "désormais", "ensuite", "alors", "donc", "même", "ainsi",
    "forcément", "visiblement", "apparemment", "manifestement", "sans",
    "cesse", "un", "à", "fait", "de", "en", "et", "là", "ici",
}
# Les locutions adverbiales qu'on saute d'un bloc, de la fin vers le debut.
LOCUTIONS = [("tout", "à", "fait"), ("de", "plus", "en", "plus"),
             ("de", "moins", "en", "moins"), ("bel", "et", "bien"),
             ("un", "peu"), ("sans", "cesse"), ("un", "peu", "plus"),
             ("un", "peu", "moins"), ("pas", "du", "tout"), ("de", "nouveau"),
             ("à", "nouveau"), ("pour", "toujours"), ("tout", "le", "temps")]
ADVERBES_SIMPLES = ADVERBES - {"sans", "cesse", "un", "à", "fait", "de", "en",
                               "et", "là", "ici", "tout", "toute", "toutes"}


def _sauter_adverbes(ctx: Contexte, j: int) -> int:
    """Remonte depuis j par-dessus les adverbes et la negation."""
    for _ in range(8):
        if ctx.separateur(j).strip():
            return j
        trouve = False
        for locution in LOCUTIONS:
            n = len(locution)
            if all(ctx.mot(j - n + 1 + m) == locution[m] for m in range(n)) \
                    and all(not ctx.separateur(j - n + 1 + m).strip() for m in range(n - 1)):
                j -= n
                trouve = True
                break
        if trouve:
            continue
        mot = ctx.mot(j)
        if mot in ADVERBES_SIMPLES or mot in ("tout",) or (
                mot.endswith("ment") and len(mot) > 6 and not ctx.elision(j)
                and not ctx.morphologie.traits(mot) & (NOMINAUX | CONJUGUES)):
            j -= 1
            continue
        if mot in ("ne", "n'"):
            j -= 1
            continue
        return j
    return j


def _lemme_copule(ctx: Contexte, k: int) -> str | None:
    for lemme in ctx.morphologie.lemmes(ctx.noyau(k)):
        if lemme in COPULES:
            return lemme
    return None


def sujet_de_l_attribut(ctx: Contexte, i: int) -> Sujet | None:
    """Le sujet auquel s'accorde l'adjectif ou le participe en position i.

        elle est complètement ruinée               est -> elle
        ils semblent avoir été attaqués            été, avoir, semblent -> ils
        les hommes croyant être instruits          être, croyant -> les hommes
    """
    if ctx.debut_de_segment(i):
        return None
    j = _sauter_adverbes(ctx, i - 1)
    if j < 0 or ctx.separateur(j).strip():
        return None
    mot = ctx.noyau(j)
    if ctx.elision(j) in ("c'", "ç'"):
        return None

    # Un participe de copule : « a été », « sont devenus ».
    if mot in PARTICIPES_COPULES:
        if mot != "été" and not mot.startswith(("devenu", "redevenu", "resté")):
            return None
        k = _sauter_adverbes(ctx, j - 1)
        auxiliaire = ctx.noyau(k)
        lemmes = ctx.morphologie.lemmes(auxiliaire)
        if mot == "été" and "avoir" not in lemmes:
            return None
        if mot != "été" and "être" not in lemmes:
            return None
        return _sujet_de_la_forme(ctx, k)

    lemme = _lemme_copule(ctx, j)
    if lemme is None:
        return None
    return _sujet_de_la_forme(ctx, j)


def _sujet_de_la_forme(ctx: Contexte, k: int,
                      passe_par_infinitif: bool = False) -> Sujet | None:
    """Le sujet d'une forme verbale : conjuguee, infinitive ou participe."""
    if ctx.separateur(k).strip():
        return None
    mot = ctx.noyau(k)
    traits = ctx.morphologie.traits(mot)
    if not traits:
        return None
    if traits & PERSONNES_FINIES and not traits & {"inf", "ppr"} and mot != "été":
        # Un verbe pronominal (« elles se sont lavé ») : l'accord depend
        # de l'objet, que les autres regles examinent.
        if ctx.mot(k - 1) in ("se", "s'", "me", "m'", "te", "t'", "nous", "vous") \
                or ctx.elision(k) in ("s'", "m'", "t'"):
            return None
        sujet = sujet_du_verbe(ctx, k)
        if sujet is not None and sujet.personne not in traits:
            # « Il étaient grands », « C'est elles qui est venue » : le verbe
            # et le sujet se contredisent ; on ne sait pas lequel croire.
            return None
        if sujet is not None and passe_par_infinitif and (
                ctx.mot(sujet.debut - 1) in ("que", "qu'") or ctx.elision(sujet.debut) == "qu'"):
            # « ce qu'ils savent être efficace » : l'attribut est celui de
            # « ce », objet du verbe, pas celui du sujet.
            return None
        return sujet
    if "inf" in traits:
        # « peut être », « semblent avoir été », « croit être ».
        j = _sauter_adverbes(ctx, k - 1)
        if ctx.separateur(j).strip() or j < 0:
            return None
        if ctx.mot(j) in ("de", "d'", "à", "pour", "sans", "par", "après"):
            return None
        return _sujet_de_la_forme(ctx, j, passe_par_infinitif=True)
    if "ppr" in traits:
        # « les hommes croyant être », « les ouvriers ayant été ».
        j = k - 1
        if ctx.separateur(j).strip():
            return None
        sujet = _sujet_au_bout(ctx, j)
        if sujet is None or sujet.pronom:
            return None
        return sujet
    return None



# ---------------------------------------------------------------------------
# Les regles
# ---------------------------------------------------------------------------

# Ni des adjectifs ni des participes, malgre leurs traits.
EXCLUS_ATTRIBUTS = (set(DETERMINANTS_SINGULIERS) | set(DETERMINANTS_PLURIELS_GENRES)
                    | {"un", "une", "tel", "telle", "tels", "telles", "même",
                       "mêmes", "autre", "autres", "seul", "seule", "fol",
                       "tout", "toute", "tous", "toutes", "nul", "nulle",
                       # des adverbes qui ont la forme d'un adjectif
                       "droit", "fort", "point", "feu", "pile", "net", "court",
                       "bas", "haut", "clair", "faux", "dur", "ferme", "juste",
                       "dû", "mi", "demi", "possible", "debout", "ensemble",
                       "plein", "sûr", "quelque", "quelques", "chaque",
                       "plusieurs", "certain", "certains", "certaine",
                       "certaines", "aucun", "aucune"})

ATTRIBUTS = frozenset({"ms", "fs", "mp", "fp", "xs", "xp", "pms", "pfs", "pmp", "pfp"})
PARTICIPES = frozenset({"pms", "pfs", "pmp", "pfp"})


def _cibles(genre: str | None, nombre: str, traits: frozenset) -> frozenset | None:
    """Les traits que l'attribut doit porter, compte tenu de ce qu'il porte."""
    genres = [genre] if genre else sorted({t[-2] for t in traits & ATTRIBUTS} - {"x"})
    cibles = set()
    for g in genres or ["x"]:
        cibles |= {g + nombre, "p" + g + nombre} if g != "x" else set()
    cibles.add("x" + nombre)
    return frozenset(cibles)


def _adjectif(ctx: Contexte, mot: str) -> bool:
    """« contents » est un adjectif si « content » en est un."""
    if _est_adjectif(ctx, mot):
        return True
    for cible in ("ms", "fs"):
        forme = ctx.morphologie.accorder(mot, cible)
        if forme and forme != mot and _est_adjectif(ctx, forme):
            return True
    return False


def _genre_fixe(ctx: Contexte, mot: str, traits: frozenset) -> bool:
    """« bouche », « cause », « somme » n'ont qu'un genre : ce sont des noms,
    meme derriere une copule (« bouche bée », « sont cause que »)."""
    genres = {t[0] for t in traits & {"ms", "fs", "mp", "fp"}}
    if len(genres) != 1 or traits & {"xs", "xp"}:
        return False
    genre = genres.pop()
    autre = "f" if genre == "m" else "m"
    # « contents » : son feminin se lit depuis « content ».
    for forme in (mot, ctx.morphologie.accorder(mot, genre + "s")):
        if forme and (ctx.morphologie.accorder(forme, autre + "s")
                      or ctx.morphologie.accorder(forme, autre + "p")):
            return False
    return True


def _compatible(traits: frozenset, genre: str | None, nombre: str) -> bool:
    for t in traits & ATTRIBUTS:
        g, n = t[-2], t[-1]
        if n != nombre:
            continue
        if genre is None or g in (genre, "x"):
            return True
    return False


@regle("ACCORD_ATTRIBUT_SUJET", "l'attribut s'accorde avec le sujet du verbe")
def _accord_attribut_sujet(ctx: Contexte, i: int):
    """« elle semble être totalement ruiné » -> « ruinée »."""
    mot = ctx.mot(i)
    if not mot or ctx.elision(i) or mot in MOTS_INVARIABLES:
        return None
    traits = ctx.morphologie.traits(mot)
    if not traits & ATTRIBUTS:
        return None
    if traits & {"inf", "ppr"}:
        return None
    # « elles sont source de débats », « il est temps de » : un nom attribut.
    suivant = ctx.apercu(i + 1)
    if suivant in ("de", "d'", "du", "des") or suivant.startswith("d'"):
        return None
    if traits & PARTICIPES:
        # « partis » est aussi le pluriel du nom « parti » : derriere une
        # copule, c'est le participe qui compte.
        traits = traits & PARTICIPES
    elif not _adjectif(ctx, mot) or _genre_fixe(ctx, mot, traits):
        return None
    if mot in EXCLUS_ATTRIBUTS or mot in INVARIABLES_ADJECTIFS \
            or _couleur_composee(ctx, i):
        return None
    # « elles sont bleu saphir », « nous sommes frère et sœur ».
    if suivant in ("et", "ou") or mot in COULEURS and suivant \
            and ctx.morphologie.nom(suivant):
        return None
    # « elle était tout feu », « ils sont bien sûr ressortis », « nous nous
    # étions fait prendre » : l'attribut n'est pas ce mot-la.
    if ctx.mot(i - 1) in ("tout", "toute") or "-" in ctx.separateur(i - 1) \
            or "-" in ctx.separateur(i):
        return None
    traits_suivant = ctx.morphologie.traits(suivant) if suivant else frozenset()
    if traits_suivant & (PARTICIPES | {"inf"}) and not traits_suivant & CONJUGUES:
        return None
    sujet = sujet_de_l_attribut(ctx, i)
    if sujet is None or sujet.personne in ("2p",) or sujet.personne == "3s" and \
            ctx.noyau(sujet.debut) in ("on",):
        return None
    nombre = sujet.nombre
    genre = sujet.genre
    if _compatible(traits, genre, nombre):
        return None
    cibles = _cibles(genre, nombre, traits)
    if traits <= PARTICIPES:
        # Un participe ne prend que des formes de participe : « parti »
        # devient « parties », pas « partis », pluriel du nom.
        cibles = frozenset(t for t in cibles if t in PARTICIPES)
    accorde = ctx.morphologie.accorder(mot, cibles) or ctx.morphologie.forme(mot, cibles)
    if accorde is None and nombre == "p" and genre:
        # « courtois », « heureux » : le dictionnaire n'a que le singulier,
        # qui sert aussi de pluriel.
        singulier = ctx.morphologie.accorder(mot, {genre + "s", "p" + genre + "s"})
        if singulier and singulier.endswith(("s", "x", "z")):
            accorde = singulier
    if accorde is None:
        # « calme » : nom, adjectif et verbe a la fois, le dictionnaire hesite
        # entre ses paradigmes. Le pluriel regulier tranche.
        for forme in ((mot + "s", mot + "x") if nombre == "p" else
                      ((mot[:-1],) if mot.endswith(("s", "x")) else ())):
            if ctx.morphologie.traits(forme) & cibles:
                accorde = forme
                break
    if accorde is None or accorde == mot or not ctx.connait(accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("ACCORD_SUJET_ELOIGNE", "le verbe s'accorde avec son sujet, même éloigné")
def _accord_sujet_eloigne(ctx: Contexte, i: int):
    """« les enfants dans le jardin joue » -> « jouent »."""
    mot = ctx.noyau(i)
    if not mot or ctx.elision(i) in ("j'", "c'", "qu'"):
        return None
    traits = ctx.morphologie.traits(mot)
    if not traits & PERSONNES_FINIES or traits & (PARTICIPES | {"inf", "ppr"}):
        return None
    # « ces choses nous les partageons », « c'est vous qui l'avez écrit » :
    # une 1re ou 2e personne du pluriel a presque toujours son pronom quelque
    # part, meme quand on ne le voit pas.
    if traits & {"1p", "2p"} or "-" in ctx.separateur(i) or "-" in ctx.separateur(i - 1):
        return None
    # « Votre site précèdent peut apparaître » : deux verbes conjugues de
    # suite, le premier n'en est sans doute pas un.
    if _verbe_fini_sur(ctx, i + 1) and not ctx.separateur(i).strip():
        return None
    sujet = sujet_du_verbe(ctx, i)
    # Les sujets pronoms ont leurs propres regles, plus fines : celle-ci ne
    # s'occupe que des groupes nominaux.
    if sujet is None or sujet.pronom or sujet.personne in traits:
        return None
    if traits & NOMINAUX and not _verbe_sans_doute(ctx, i):
        return None
    # « La première chose qu'on apprend sont des jurons » : avec « être »,
    # l'attribut pluriel peut emporter l'accord.
    if "être" in ctx.morphologie.lemmes(mot) and sujet.nombre == "s" and (
            ctx.apercu(i + 1) in DETERMINANTS_PLURIELS_GENRES):
        return None
    if ctx.elision(i):
        accorde = ctx.morphologie.accorder(mot, sujet.personne)
        if accorde is None or accorde == mot or accorde[0] not in "aeiouyéèêâîôûh":
            # « les enfants t'est choqué » : « t'sont » n'existe pas.
            return None
        brut = ctx.brut(i)
        coupe = len(brut) - len(mot)
        return brut[:coupe] + appliquer_casse(brut[coupe:], accorde)
    return accorder_le_verbe(ctx, i, sujet.personne)


def _verbe_sans_doute(ctx: Contexte, i: int) -> bool:
    """« joue », « porte », « bois » sont aussi des noms. Derriere « ne » ou
    un pronom qui ne peut pas etre un article, ce sont des verbes ; partout
    ailleurs, le doute demeure — « les cuillères en bois », « leur place »."""
    if ctx.elision(i) in ("n'", "m'", "t'", "s'"):
        return True
    return ctx.mot(i - 1) in ("ne", "me", "te", "se", "lui", "nous", "vous", "n'y",
                              "n'en", "s'en", "s'y", "m'en", "t'en")
