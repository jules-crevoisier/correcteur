# -*- coding: utf-8 -*-
"""Regles de grammaire contextuelles.

Le lexique corrige les mots pris un a un. Il ne voit donc pas les fautes les
plus frequentes du francais, celles ou les deux graphies existent :

    je sais pas si sa va      « sa » est un mot, « ça » aussi
    ils on mangé              « on » est un mot, « ont » aussi
    j'ai manger               « manger » est un mot, « mangé » aussi

Ce module regarde les mots voisins pour trancher. Chaque regle est une petite
fonction qui repond « voila ce qu'il faut ecrire ici » ou ne repond rien.

Deux principes, les memes que partout ailleurs dans le projet :

1. On ne corrige jamais le registre. Aucune regle n'ajoute le « ne » d'une
   negation, ne remplace « ça » par « cela » ni « y a » par « il y a ».
2. Devant le moindre doute, on se tait. Une regle ne se declenche que sur un
   contexte ou l'autre lecture est impossible : « ils on » est toujours une
   faute, « elle et contente » aussi. Les cas ambigus — « il a la flemme »
   contre « je vais a la gare » — sont laisses tels quels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .politique import PARLE, SOUTENU

# ---------------------------------------------------------------------------
# Decoupage en mots
# ---------------------------------------------------------------------------

# Un mot : des lettres ou des chiffres, avec ses apostrophes internes
# (« j'ai », « aujourd'hui ») et son eventuelle apostrophe finale (« qu' »).
_MOT = re.compile(r"[^\W_]+(?:['’][^\W_]+)*['’]?", re.UNICODE)

# Elisions placees devant un mot. Les isoler permet de traiter « j'ai » comme
# l'auxiliaire « ai », et « qu'il » comme le pronom « il ».
CLITIQUES = (
    "aujourd'", "jusqu'", "lorsqu'", "puisqu'", "quoiqu'", "presqu'", "entr'",
    "qu'", "c'", "ç'", "d'", "j'", "l'", "m'", "n'", "s'", "t'",
)


@dataclass(frozen=True)
class Jeton:
    texte: str
    debut: int
    fin: int


def decouper(texte: str) -> list[Jeton]:
    return [Jeton(m.group(), m.start(), m.end()) for m in _MOT.finditer(texte)]


def separer_clitique(mot: str) -> tuple[str, str]:
    """« c'est » -> (« c' », « est »). « bonjour » -> (« », « bonjour »)."""
    minuscule = mot.lower().replace("’", "'")
    for clitique in CLITIQUES:
        if minuscule.startswith(clitique) and len(minuscule) > len(clitique):
            # « aujourd'hui » n'est pas une elision : son noyau n'est pas un mot.
            if clitique == "aujourd'":
                return "", mot
            return mot[: len(clitique)], mot[len(clitique):]
    return "", mot


# ---------------------------------------------------------------------------
# Vocabulaire des regles
# ---------------------------------------------------------------------------

PRONOMS_SUJETS = {"je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles"}

# Sujets a la 3e personne du singulier : devant eux, « et » est un « est ».
SUJETS_SINGULIER = {
    "il", "elle", "on", "ça", "ce", "qui", "celui", "celle", "chacun",
    "quelqu'un", "personne", "tout", "ceci", "cela",
}

PRONOMS_PLURIEL = {"ils", "elles"}

# Auxiliaires : ce qui les suit est un participe, jamais un infinitif.
# « été » en est volontairement absent : « j'ai été manger » est correct.
AUXILIAIRES = {
    "ai", "as", "a", "avons", "avez", "ont",
    "avais", "avait", "avions", "aviez", "avaient",
    "aurai", "auras", "aura", "aurons", "aurez", "auront",
    "aurais", "aurait", "aurions", "auriez", "auraient",
    "suis", "es", "est", "sommes", "êtes", "sont",
    "étais", "était", "étions", "étiez", "étaient",
    "serai", "seras", "sera", "serons", "serez", "seront",
    "serais", "serait", "serions", "seriez", "seraient",
}

# Semi-auxiliaires et prepositions : ce qui les suit est un infinitif,
# jamais un participe.
SEMI_AUXILIAIRES = {
    "vais", "vas", "va", "allons", "allez", "vont",
    "peux", "peut", "pouvons", "pouvez", "peuvent", "pourrais", "pourrait",
    "dois", "doit", "devons", "devez", "doivent", "devrais", "devrait",
    "veux", "veut", "voulons", "voulez", "veulent", "voudrais", "voudrait",
    "faut", "faudrait", "sais", "savons", "savez", "savent",
    "aime", "aimes", "aimons", "aimez", "aiment", "adore", "adores",
    "déteste", "détestes", "préfère", "préfères", "espère", "espères",
    "essaie", "essaies", "essaye", "compte", "comptes", "ose", "oses",
    "viens", "vient", "venons", "venez", "viennent",
    "sans", "pour",
}

# Participes irreguliers frequents, que leur terminaison ne trahit pas.
PARTICIPES_IRREGULIERS = {
    "dit", "fait", "mis", "pris", "vu", "su", "pu", "voulu", "dû", "eu",
    "été", "venu", "tenu", "reçu", "connu", "cru", "bu", "lu", "écrit",
    "ouvert", "offert", "mort", "né", "allé", "compris", "appris", "permis",
    "promis", "assis", "surpris", "rendu", "perdu", "vendu", "attendu",
    "entendu", "répondu", "descendu", "battu", "vécu", "couru", "sorti",
    "parti", "senti", "dormi", "servi", "suivi", "fini", "choisi", "réussi",
}

# Noms en « -é » que leur terminaison fait passer pour des participes.
NOMS_EN_E = {
    "côté", "été", "café", "thé", "marché", "pré", "degré", "carré",
    "résumé", "employé", "invité", "député", "comité", "canapé", "blé",
    "clé", "congé", "cliché", "supermarché", "musée", "lycée", "défilé",
    "abbé", "curé", "gré", "pavé", "fossé", "traité", "procédé", "aîné",
}

DETERMINANTS_PLURIELS = {
    "des", "ces", "mes", "tes", "ses", "nos", "vos", "leurs",
    "plusieurs", "quelques", "certains", "certaines", "différents", "divers",
}

FIN_DE_SEGMENT = re.compile(r"^\s*($|[.!?,;:…\n)\]»\"])")
DEBUT_DE_SEGMENT = re.compile(r"[.!?,;:…\n]")

# Mots qui ouvrent un membre de phrase sans en etre le sujet.
CHARNIERES = {"mais", "et", "ou", "donc", "car", "puis", "alors", "bref",
              "franchement", "honnêtement", "perso", "après", "enfin"}


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Suggestion:
    """Un remplacement propose par une regle."""

    index: int        # premier jeton concerne
    portee: int       # nombre de jetons remplaces
    texte: str        # ce qu'il faut ecrire a la place
    regle: str
    message: str


Fonction = Callable[["Contexte", int], "str | tuple[str, int] | None"]


@dataclass(frozen=True)
class Regle:
    nom: str
    message: str
    fonction: Fonction
    # « tous » : la regle corrige une faute, quel que soit le ton.
    # « soutenu » : elle releve le registre, ce qui ne se fait que sur demande.
    registre: str = "tous"


REGLES: list[Regle] = []


def regle(nom: str, message: str, registre: str = "tous"):
    """Enregistre une regle. L'ordre de declaration est l'ordre d'application."""
    def decorateur(fonction: Fonction) -> Fonction:
        REGLES.append(Regle(nom, message, fonction, registre))
        return fonction
    return decorateur


class Contexte:
    """Le texte decoupe, plus les quelques services dont les regles ont besoin."""

    def __init__(self, texte: str, jetons: list[Jeton], lexique):
        self.texte = texte
        self.jetons = jetons
        self.lexique = lexique

    # -- lecture des mots ---------------------------------------------------

    def mot(self, i: int) -> str:
        """Le jeton entier, en minuscules : « C'est » -> « c'est »."""
        if 0 <= i < len(self.jetons):
            return self.jetons[i].texte.lower().replace("’", "'")
        return ""

    def noyau(self, i: int) -> str:
        """Le jeton prive de son elision : « c'est » -> « est »."""
        return separer_clitique(self.mot(i))[1]

    def elision(self, i: int) -> str:
        """L'elision du jeton : « c'est » -> « c' »."""
        return separer_clitique(self.mot(i))[0]

    def brut(self, i: int) -> str:
        return self.jetons[i].texte if 0 <= i < len(self.jetons) else ""

    # -- lecture de ce qui separe les mots ----------------------------------

    def separateur(self, i: int) -> str:
        """Le texte entre le jeton i et le suivant."""
        if i + 1 >= len(self.jetons):
            return self.texte[self.jetons[i].fin:] if 0 <= i < len(self.jetons) else ""
        return self.texte[self.jetons[i].fin:self.jetons[i + 1].debut]

    def debut_de_segment(self, i: int) -> bool:
        """Le jeton i ouvre-t-il une phrase ou un membre de phrase ?"""
        if i <= 0:
            return True
        return bool(DEBUT_DE_SEGMENT.search(self.separateur(i - 1)))

    def fin_de_segment(self, i: int) -> bool:
        """Le jeton i termine-t-il une phrase ou un membre de phrase ?"""
        if i >= len(self.jetons) - 1:
            return True
        return bool(FIN_DE_SEGMENT.match(self.separateur(i)))

    # -- services lexicaux --------------------------------------------------

    def connait(self, mot: str) -> bool:
        return self.lexique.connait(mot)

    def est_participe(self, mot: str) -> bool:
        """« mangé », « fini », « pris » — mais pas « clé » ni « nuit »."""
        if mot in PARTICIPES_IRREGULIERS:
            return True
        if mot in NOMS_EN_E:
            return False
        for terminaison, infinitif in (("ées", "er"), ("ée", "er"), ("és", "er"),
                                       ("é", "er"), ("is", "ir"), ("i", "ir"),
                                       ("us", "re"), ("u", "re")):
            if mot.endswith(terminaison):
                radical = mot[: -len(terminaison)]
                if radical and self.connait(radical + infinitif):
                    return True
        return False


def appliquer_casse(modele: str, mot: str) -> str:
    """Garde la majuscule du mot d'origine : « On » -> « Ont »."""
    if modele[:1].isupper():
        return mot[:1].upper() + mot[1:]
    return mot


# ---------------------------------------------------------------------------
# Les regles, dans leur ordre d'application
# ---------------------------------------------------------------------------

VERBES_APRES_CA = {
    "va", "vas", "vaut", "fait", "fera", "ferait", "marche", "marchera",
    "dépend", "dépendra", "suffit", "arrive", "arrivera", "existe", "veut",
    "peut", "pourrait", "doit", "sert", "change", "reste", "craint", "passe",
    "coûte", "coûtera", "ira", "irait", "sera", "serait", "était", "est",
    "donne", "rend", "commence", "finit", "prend", "tombe", "sent", "sonne",
    "ressemble", "aide", "gêne", "dérange", "regarde", "compte", "m'", "t'",
    "s'", "me", "te", "lui", "leur", "y", "en", "ne", "n'", "aurait", "a",
}


# Pronoms qui ne sont jamais le verbe attendu par les regles d'accord.
PRONOMS_COMPLEMENTS = {
    "me", "te", "se", "le", "la", "les", "lui", "leur", "y", "en", "ne",
    "que", "de", "ce", "une", "autre", "même", "pire",
}

# Formes de la 3e personne employees a tort avec « je » ou « tu ».
ACCORDS_SUJET = {
    "je": {"peut": "peux", "veut": "veux", "doit": "dois", "fait": "fais",
           "va": "vais", "a": "ai", "est": "suis", "sait": "sais",
           "dit": "dis", "prend": "prends", "met": "mets", "vient": "viens",
           "part": "pars", "sort": "sors", "vaut": "vaux", "voit": "vois"},
    "tu": {"peut": "peux", "veut": "veux", "doit": "dois", "fait": "fais",
           "va": "vas", "a": "as", "est": "es", "sait": "sais",
           "dit": "dis", "prend": "prends", "met": "mets", "vient": "viens",
           "part": "pars", "sort": "sors", "vaut": "vaux", "voit": "vois"},
}


@regle("ACCORD_SUJET_VERBE",
       "le verbe s'accorde avec « je » ou « tu »")
def _accord_sujet_verbe(ctx: Contexte, i: int):
    formes = ACCORDS_SUJET.get(ctx.noyau(i - 1))
    if formes is None:
        return None
    correcte = formes.get(ctx.mot(i))
    if correcte is None or ctx.elision(i):
        return None
    return appliquer_casse(ctx.brut(i), correcte)


@regle("ACCORD_JE_TU_S",
       "avec « je » ou « tu », le verbe se termine par « -s »")
def _accord_je_tu_s(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if ctx.noyau(i - 1) not in ("je", "tu") or ctx.elision(i):
        return None
    if mot in PRONOMS_COMPLEMENTS:
        return None
    if mot.endswith("d"):
        accorde = mot + "s"
    elif mot.endswith("t"):
        accorde = mot[:-1] + "s"
    else:
        return None
    if ctx.connait(accorde):
        return appliquer_casse(ctx.brut(i), accorde)
    return None


@regle("ACCORD_TU_S", "avec « tu », le verbe se termine par « -s »")
def _accord_tu_s(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if ctx.noyau(i - 1) != "tu" or ctx.elision(i):
        return None
    if not mot.endswith("e") or mot in PRONOMS_COMPLEMENTS:
        return None
    if ctx.connait(mot + "s"):
        return appliquer_casse(ctx.brut(i), mot + "s")
    return None


@regle("ACCORD_ILS_ENT", "avec « ils », le verbe se termine par « -nt »")
def _accord_ils_ent(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if ctx.mot(i - 1) not in PRONOMS_PLURIEL or ctx.elision(i):
        return None
    if not mot.endswith("e") or mot in PRONOMS_COMPLEMENTS:
        return None
    if ctx.connait(mot + "nt"):
        return appliquer_casse(ctx.brut(i), mot + "nt")
    return None


@regle("SA_CA", "« sa » est un possessif ; devant un verbe, c'est « ça »")
def _sa_ca(ctx: Contexte, i: int):
    if ctx.mot(i) != "sa":
        return None
    if ctx.mot(i + 1) in VERBES_APRES_CA or ctx.elision(i + 1) in VERBES_APRES_CA:
        return appliquer_casse(ctx.brut(i), "ça")
    return None


APOSTROPHES_AVANT_PARTICIPE = {
    "ma": "m'a", "ta": "t'a", "mas": "m'as", "tas": "t'as", "la": "l'a",
}

PRONOMS_AVANT_L_A = {"me", "te", "se", "nous", "vous", "lui", "leur"}

DETERMINANTS = {"un", "une", "le", "la", "les", "ce", "cet", "des", "du",
                "mon", "ton", "son", "quel", "ce"}


@regle("APOSTROPHE_AVANT_PARTICIPE",
       "« ma » est un possessif ; devant un participe, c'est « m'a »")
def _apostrophe_avant_participe(ctx: Contexte, i: int):
    remplacement = APOSTROPHES_AVANT_PARTICIPE.get(ctx.mot(i))
    if remplacement is None or ctx.elision(i):
        return None
    # « un tas fini » : precede d'un determinant, c'est un vrai nom.
    if ctx.mot(i - 1) in DETERMINANTS:
        return None
    # « la » est bien trop souvent un article : on ne le touche qu'apres un
    # pronom complement, ou « il me la dit » ne peut etre que « me l'a dit ».
    if ctx.mot(i) == "la" and ctx.mot(i - 1) not in PRONOMS_AVANT_L_A:
        return None
    if ctx.est_participe(ctx.noyau(i + 1)):
        return appliquer_casse(ctx.brut(i), remplacement)
    return None


@regle("IL_A", "apres un pronom sujet, « a » est le verbe avoir : pas d'accent")
def _il_a(ctx: Contexte, i: int):
    if ctx.mot(i) != "à":
        return None
    if ctx.noyau(i - 1) in SUJETS_SINGULIER or ctx.elision(i) in ("c'", "ç'"):
        return appliquer_casse(ctx.brut(i), "a")
    return None


# Mots apres lesquels « a » ne peut etre que la preposition « à ».
AVANT_A_ACCENT = {
    "vais", "vas", "va", "allons", "allez", "vont", "aller", "allé", "allée",
    "allés", "allées", "irai", "iras", "ira", "irons", "irez", "iront",
    "grâce", "quant", "face", "contrairement", "conformément", "jusqu'",
    "prêt", "prête", "prêts", "prêtes", "habitué", "habituée", "obligé",
    "obligée", "pense", "penses", "pensé", "penser", "réfléchir", "réfléchi",
    "commence", "commences", "commencé", "commencer", "continue", "continuer",
    "hésite", "hésites", "hésité", "hésiter", "aide", "aider", "aidé",
    "sert", "servir", "servi", "arrive", "arriver", "arrivé", "parle",
    "parler", "parlé", "parles", "demande", "demander", "demandé", "donne",
    "donner", "donné", "joue", "jouer", "joué", "réussi", "réussit",
    "apprendre", "apprends", "appris", "rapport", "retour", "suite",
    "aille", "ailles", "aillent", "viens", "vient", "venez", "venir", "venu",
    "reste", "rester", "resté", "retourne", "retourner", "retourné", "monte",
    "monter", "emmène", "emmener", "amène", "amener", "envoie", "envoyer",
    "envoyé", "habite", "habiter", "travaille", "travailler", "cherche",
    "chercher", "cherché", "tiens", "tient", "sers", "décide", "décidé",
    "décider", "oblige", "obligé", "invite", "invité", "inviter", "force",
}

# Mots apres lesquels « a » ne peut etre que la preposition « à ».
APRES_A_ACCENT = {
    "côté", "cause", "travers", "propos", "peine", "nouveau", "priori",
    "part", "moitié", "force", "fond", "volonté", "moi", "toi", "plus",
    "demain", "bientôt", "jamais", "toute", "nouveau", "condition", "défaut",
    "domicile", "l'heure", "l'aise", "l'avance", "l'époque", "l'écart",
}


@regle("A_ACCENT", "ici « a » est la preposition « à »")
def _a_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "a":
        return None
    if ctx.noyau(i - 1) in AVANT_A_ACCENT or ctx.mot(i - 1) in AVANT_A_ACCENT:
        return appliquer_casse(ctx.brut(i), "à")
    if ctx.mot(i + 1) in APRES_A_ACCENT:
        return appliquer_casse(ctx.brut(i), "à")
    return None


@regle("ET_EST", "apres un pronom sujet, c'est le verbe « est »")
def _et_est(ctx: Contexte, i: int):
    if ctx.noyau(i) != "et":
        return None
    # « lui et elle », « toi et moi » : une vraie coordination.
    if ctx.mot(i + 1) in PRONOMS_SUJETS | {"moi", "toi", "lui", "eux"}:
        return None
    if ctx.elision(i) in ("c'", "ç'") or ctx.noyau(i - 1) in SUJETS_SINGULIER:
        return appliquer_casse(ctx.brut(i), ctx.elision(i) + "est")
    return None


@regle("ILS_ONT", "« ils on » : le verbe avoir s'ecrit « ont »")
def _ils_ont(ctx: Contexte, i: int):
    if ctx.mot(i) == "on" and ctx.mot(i - 1) in PRONOMS_PLURIEL:
        return appliquer_casse(ctx.brut(i), "ont")
    return None


@regle("ILS_SONT", "« ils son » : le verbe etre s'ecrit « sont »")
def _ils_sont(ctx: Contexte, i: int):
    if ctx.mot(i) == "son" and ctx.mot(i - 1) in PRONOMS_PLURIEL:
        return appliquer_casse(ctx.brut(i), "sont")
    return None


# Terminaisons qu'un verbe conjugue ou un infinitif peut avoir. Un mot qui
# n'en a aucune (« truc », « film », « mec ») n'est pas un verbe, donc « se »
# ne peut pas le preceder.
TERMINAISONS_VERBALES = ("e", "s", "t", "d", "x", "r", "a", "i", "u", "é",
                         "ée", "ù", "û")

# Noms frequents dont la terminaison ressemble pourtant a celle d'un verbe.
NOMS_APRES_CE = {
    "soir", "matin", "midi", "jour", "moment", "week", "weekend", "coup",
    "gars", "truc", "machin", "bail", "délire", "monde", "genre", "temps",
    "niveau", "prix", "bruit", "message", "serveur", "salon", "projet",
    "sujet", "texte", "lien", "site", "compte", "groupe", "jeu", "type",
}


def _peut_etre_verbe(mot: str) -> bool:
    if mot in NOMS_APRES_CE:
        return False
    return mot.endswith(TERMINAISONS_VERBALES)


@regle("SE_CE", "« se » annonce un verbe ; ici c'est le demonstratif « ce »")
def _se_ce(ctx: Contexte, i: int):
    if ctx.mot(i) != "se":
        return None
    suivant = ctx.mot(i + 1)
    if suivant in ("qui", "que", "dont") or ctx.elision(i + 1) == "qu'":
        return appliquer_casse(ctx.brut(i), "ce")
    # « se truc » : ce qui suit n'est pas un verbe, « se » n'a rien a y faire.
    if suivant and ctx.connait(suivant) and not _peut_etre_verbe(suivant):
        return appliquer_casse(ctx.brut(i), "ce")
    return None


@regle("CE_SE", "devant un verbe pronominal, c'est « se »")
def _ce_se(ctx: Contexte, i: int):
    if ctx.mot(i) != "ce" or ctx.mot(i - 1) not in PRONOMS_SUJETS:
        return None
    # « il ce que » n'existe pas non plus, mais SE_CE s'en occupe.
    if ctx.mot(i + 1) in ("qui", "que", "dont", "soir", "matin") \
            or ctx.elision(i + 1) == "qu'":
        return None
    return appliquer_casse(ctx.brut(i), "se")


APRES_C_EST = {
    "un", "une", "le", "la", "les", "pas", "trop", "vrai", "vraiment", "bon",
    "bien", "ça", "cool", "chaud", "clair", "sûr", "mon", "ton", "son",
    "mes", "quoi", "comme", "beaucoup", "juste", "déjà", "possible",
    "impossible", "normal", "bizarre", "dur", "facile", "difficile", "nul",
    "génial", "cher", "grave", "moi", "toi", "lui", "eux", "nous", "vous",
    "peut", "toujours", "jamais", "rien", "tout", "mieux", "pire",
}


@regle("S_EST_C_EST", "« s'est » exige un verbe pronominal ; ici c'est « c'est »")
def _s_est_c_est(ctx: Contexte, i: int):
    if ctx.elision(i) != "s'" or ctx.noyau(i) != "est":
        return None
    # « on ne s'est pas vus », « il s'est pas rendu compte » : precede d'un
    # sujet, « s'est » est le pronominal attendu. La faute ne se produit
    # qu'en tete de phrase, la ou « c'est » etait le mot juste.
    if not ctx.debut_de_segment(i) and ctx.mot(i - 1) not in CHARNIERES:
        return None
    if ctx.mot(i + 1) in APRES_C_EST:
        return appliquer_casse(ctx.brut(i), "c'est")
    return None


@regle("OU_ACCENT", "« où » designe le lieu ; « ou » relie deux choix")
def _ou_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "ou":
        return None
    if ctx.mot(i + 1) in ("est", "sont", "es", "était", "étaient", "sera",
                          "seront", "ça"):
        return appliquer_casse(ctx.brut(i), "où")
    return None


AVANT_LA_ACCENT = {
    "suis", "es", "est", "sommes", "êtes", "sont", "étais", "était",
    "serai", "sera", "reste", "restes", "restons", "restez", "viens",
    "vient", "venez", "arrive", "arrives", "jusque", "par", "celui",
    "celle", "ceux", "celles", "mets", "assieds",
}


@regle("LA_ACCENT", "« là » designe le lieu ; « la » est un article")
def _la_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "la":
        return None
    if ctx.mot(i + 1) == "bas" and ctx.separateur(i) == " ":
        return (appliquer_casse(ctx.brut(i), "là-bas"), 2)
    if ctx.noyau(i - 1) in AVANT_LA_ACCENT and ctx.fin_de_segment(i):
        return appliquer_casse(ctx.brut(i), "là")
    return None


@regle("TOUT_TOUS", "devant un determinant pluriel, « tout » s'ecrit « tous »")
def _tout_tous(ctx: Contexte, i: int):
    if ctx.mot(i) != "tout":
        return None
    if ctx.mot(i + 1) in ("les", "ces", "mes", "tes", "ses", "nos", "vos",
                          "leurs", "ceux"):
        return appliquer_casse(ctx.brut(i), "tous")
    return None


@regle("MES_MAIS", "ici « mes » est la conjonction « mais »")
def _mes_mais(ctx: Contexte, i: int):
    if ctx.mot(i) != "mes":
        return None
    if ctx.mot(i + 1) in PRONOMS_SUJETS | {"ça", "bon", "bref", "quand"} \
            or ctx.mot(i + 1) in ("c'est", "j'ai", "j'y"):
        return appliquer_casse(ctx.brut(i), "mais")
    return None


@regle("PEUT_PEU", "« un peu » : l'adverbe ne prend pas de « t »")
def _peut_peu(ctx: Contexte, i: int):
    if ctx.mot(i) != "peut":
        return None
    if ctx.mot(i - 1) in ("un", "très", "trop", "si", "plus", "aussi",
                          "assez", "quelque"):
        return appliquer_casse(ctx.brut(i), "peu")
    return None


MOTS_INTERROGATIFS = {"qui", "où", "quand", "comment", "pourquoi", "combien",
                      "quel", "quelle", "quels", "quelles", "que"}


@regle("EST_CE", "« est-ce » s'ecrit avec un trait d'union")
def _est_ce(ctx: Contexte, i: int):
    if ctx.mot(i) != "est" or ctx.mot(i + 1) != "ce" or ctx.separateur(i) != " ":
        return None
    interroge = (
        i == 0
        or ctx.mot(i - 1) in MOTS_INTERROGATIFS
        or ctx.elision(i - 1) == "qu'"
        or ctx.mot(i + 2) == "que"
        or ctx.elision(i + 2) == "qu'"
    )
    if not interroge:
        return None
    return (appliquer_casse(ctx.brut(i), "est-ce"), 2)


@regle("PARTICIPE_APRES_AUXILIAIRE",
       "apres l'auxiliaire, le verbe prend « -é » et non « -er »")
def _participe_apres_auxiliaire(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if not mot.endswith("er") or ctx.elision(i):
        return None
    if ctx.noyau(i - 1) not in AUXILIAIRES:
        return None
    participe = mot[:-2] + "é"
    if ctx.connait(participe):
        return appliquer_casse(ctx.brut(i), participe)
    return None


@regle("INFINITIF_APRES_SEMI_AUXILIAIRE",
       "apres ce verbe, le suivant reste a l'infinitif : « -er »")
def _infinitif_apres_semi_auxiliaire(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if not mot.endswith("é") or mot in NOMS_EN_E or ctx.elision(i):
        return None
    if ctx.noyau(i - 1) not in SEMI_AUXILIAIRES:
        return None
    infinitif = mot[:-1] + "er"
    if ctx.connait(infinitif):
        return appliquer_casse(ctx.brut(i), infinitif)
    return None


# Sujet -> terminaison a ajouter au participe employe avec « etre ».
ACCORDS_ETRE = {
    ("elle", "est"): "e",
    ("elles", "sont"): "es",
    ("ils", "sont"): "s",
    ("nous", "sommes"): "s",
}


@regle("ACCORD_PARTICIPE_ETRE",
       "avec l'auxiliaire « etre », le participe s'accorde avec le sujet")
def _accord_participe_etre(ctx: Contexte, i: int):
    participe = ctx.mot(i)
    if ctx.elision(i) or not ctx.est_participe(participe):
        return None
    terminaison = ACCORDS_ETRE.get((ctx.mot(i - 2), ctx.noyau(i - 1)))
    if terminaison is None:
        return None
    accorde = participe + terminaison
    if participe.endswith(("s", "x", "e")) or not ctx.connait(accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


def _pluriels(mot: str) -> list[str]:
    """Les pluriels envisageables d'un nom singulier."""
    if mot.endswith("al"):
        return [mot[:-2] + "aux", mot + "s"]
    if mot.endswith(("eau", "eu")):
        return [mot + "x", mot + "s"]
    return [mot + "s"]


@regle("ACCORD_DETERMINANT_NOM",
       "le nom s'accorde avec son determinant pluriel")
def _accord_determinant_nom(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    determinant = ctx.mot(i - 1)

    if determinant not in DETERMINANTS_PLURIELS:
        # « les » est aussi un pronom : « je les mange » n'a pas de nom.
        if determinant != "les" or ctx.mot(i - 2) in PRONOMS_SUJETS:
            return None

    if ctx.elision(i) or mot.endswith(("s", "x", "z")) or not ctx.connait(mot):
        return None

    for pluriel in _pluriels(mot):
        if ctx.connait(pluriel):
            return appliquer_casse(ctx.brut(i), pluriel)
    return None


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

def analyser(texte: str, jetons: list[Jeton], lexique,
             regles_ignorees: set[str] = frozenset(),
             registre: str = PARLE) -> list[Suggestion]:
    """Passe toutes les regles sur le texte et renvoie leurs propositions."""
    ctx = Contexte(texte, jetons, lexique)
    applicables = [
        r for r in REGLES
        if r.registre == "tous" or (r.registre == SOUTENU and registre == SOUTENU)
    ]
    suggestions: list[Suggestion] = []
    couvert: set[int] = set()

    for i in range(len(jetons)):
        if i in couvert:
            continue
        for r in applicables:
            if r.nom in regles_ignorees:
                continue
            resultat = r.fonction(ctx, i)
            if resultat is None:
                continue
            remplacement, portee = (
                resultat if isinstance(resultat, tuple) else (resultat, 1)
            )
            if remplacement == texte[jetons[i].debut:jetons[i + portee - 1].fin]:
                continue
            suggestions.append(
                Suggestion(i, portee, remplacement, r.nom, r.message)
            )
            couvert.update(range(i, i + portee))
            break

    return suggestions


# ---------------------------------------------------------------------------
# Le registre soutenu
#
# Ces regles-la ne corrigent aucune faute : elles remontent le ton. Elles
# dorment donc tant qu'on ne les reclame pas, application par application ou
# d'un reglage. C'est exactement ce que Papote refuse de faire par defaut.
# ---------------------------------------------------------------------------

# « que » n'y figure pas : « faut que j'y aille » n'est pas une negation.
NEGATIONS = {"pas", "plus", "jamais", "rien", "personne", "guère", "aucun",
             "aucune", "nul", "nulle"}

# Pronoms qui s'intercalent entre le sujet et le verbe. Le « ne » se place
# devant eux, pas devant le verbe : « il n'y a pas », jamais « il y n'a pas ».
PRONOMS_INTERCALES = {"me", "te", "se", "le", "la", "les", "lui", "leur",
                      "y", "en", "nous", "vous"}

# Combien de mots peuvent separer le verbe de sa negation.
PORTEE_NEGATION = 3

# Sujets derriere lesquels on peut glisser un « ne » sans se tromper. Ni « y »
# ni « en » n'y figurent : ce sont des pronoms intercales, et le « ne » se
# place devant eux — « il n'y a pas », jamais « il y n'a pas ».
SUJETS_NEGATION = PRONOMS_SUJETS | {"ça", "ce", "qui", "celui", "celle",
                                    "chacun", "personne", "tout"}

# Elisions qui portent le sujet : « j'ai » -> « je n'ai ».
SUJETS_ELIDES = {"j'": "je", "c'": "ce", "ç'": "ce", "t'": "tu", "n'": None}

VOYELLES = "aeiouyàâäéèêëîïôöùûüh"


def _negation(verbe: str) -> str:
    """« ne » ou « n' », selon ce que le verbe commence."""
    return "n'" if verbe[:1].lower() in VOYELLES else "ne "


@regle("NEGATION_COMPLETE",
       "a l'ecrit soutenu, la negation garde son « ne »", registre=SOUTENU)
def _negation_complete(ctx: Contexte, i: int):
    """« j'ai pas » -> « je n'ai pas », « y a pas » -> « n'y a pas ».

    La regle se declenche sur le premier mot qui suit le sujet, et non sur le
    verbe : le « ne » se glisse devant les pronoms qui les separent.
    """
    debut = ctx.brut(i)
    if not debut:
        return None

    elision, noyau = separer_clitique(debut.lower())
    if not noyau:
        return None

    # Le sujet est-il juste avant, ou porte par l'elision du mot lui-meme ?
    sujet_elide = SUJETS_ELIDES.get(elision) if elision else None
    if sujet_elide is None and ctx.noyau(i - 1) not in SUJETS_NEGATION:
        return None
    if elision and sujet_elide is None:
        return None

    # Une negation suit-elle, a portee de vue ?
    if not any(ctx.mot(i + n) in NEGATIONS for n in range(1, PORTEE_NEGATION + 1)):
        return None

    # Deja niee ?
    if elision == "n'" or ctx.mot(i - 1) in ("ne", "n'"):
        return None
    if any(ctx.mot(i + n) in ("ne", "n'") or ctx.elision(i + n) == "n'"
           for n in range(0, PORTEE_NEGATION)):
        return None

    if sujet_elide is not None:
        return appliquer_casse(debut, f"{sujet_elide} {_negation(noyau)}{noyau}")
    return f"{_negation(noyau)}{debut}"


@regle("SUJET_IMPERSONNEL",
       "a l'ecrit soutenu, le sujet impersonnel s'ecrit", registre=SOUTENU)
def _sujet_impersonnel(ctx: Contexte, i: int):
    """« faut y aller » -> « il faut y aller », « y a » -> « il y a »."""
    if not ctx.debut_de_segment(i):
        return None
    mot = ctx.mot(i)
    if mot == "faut":
        return appliquer_casse(ctx.brut(i), "il faut")
    if mot == "y" and ctx.mot(i + 1) in ("a", "avait", "aura", "aurait"):
        return appliquer_casse(ctx.brut(i), "il y")
    return None


@regle("CA_CELA", "a l'ecrit soutenu, « ça » devient « cela »", registre=SOUTENU)
def _ca_cela(ctx: Contexte, i: int):
    if ctx.mot(i) != "ça" or ctx.elision(i):
        return None
    # « ça va ? » reste « ça va ? » : personne n'ecrit « cela va ? ».
    if ctx.mot(i + 1) in ("va", "vas", "allait"):
        return None
    return appliquer_casse(ctx.brut(i), "cela")
