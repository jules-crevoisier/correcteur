# -*- coding: utf-8 -*-
"""Les mots justes qui en cachent un autre.

Le correcteur ne regarde que les mots absents du dictionnaire. C'est ce qui
le rend sur — mais cela le rend aveugle a toute une famille de fautes, la
plus penible de toutes :

    commet c'est passé ta ounré ?

« commet » existe : c'est le verbe commettre, douze-milliemme mot du
francais. Le dictionnaire le connait, donc le correcteur passe son chemin —
alors que « comment », cent-vingt-huitieme, est cent fois plus probable a
cette place.

Deviner tout seul demanderait un modele de langue qu'on n'embarque pas. Mais
ces fautes ne sont pas innombrables : quelques dizaines de paires couvrent
l'essentiel de ce qu'on ecrit vite. Chacune vient donc avec **sa condition**,
qui dit quand la substitution est certaine — et elle ne se fait jamais
autrement.

Deux garde-fous tenus pour chaque entree :

1. le mot ecrit doit etre nettement plus rare que celui propose. Sinon le
   contexte ne suffit pas a trancher, et l'on invente une faute ;
2. la condition doit porter sur ce qui **entoure** le mot, pas sur le mot
   lui-meme. « il commet une erreur » et « commet ça va » ne se distinguent
   que par ce qui precede.

Une entree sans condition serait un remplacement aveugle : c'est ce que fait
deja le dictionnaire personnel, et l'utilisateur l'a choisi. Ici, non.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Ces mots annoncent un verbe conjugue : apres eux, une forme verbale est a
# sa place et ne doit pas etre touchee.
SUJETS_DE_VERBE = {
    "il", "elle", "on", "qui", "celui", "celle", "chacun", "chacune",
    "quelqu'un", "personne", "nul", "tout", "ça", "ce", "cela",
}

# Ceux-la annoncent un nom : apres eux, une forme verbale est suspecte.
DETERMINANTS_DE_NOM = {
    "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cet", "cette",
    "ces", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
    "notre", "nos", "votre", "vos", "leur", "leurs", "quel", "quelle",
}


@dataclass(frozen=True)
class Confusion:
    """Un mot juste, celui qu'il cache, et quand preferer le second."""

    ecrit: str
    voulu: str
    quand: Callable[["Contexte", int], bool]  # noqa: F821
    pourquoi: str


# ---------------------------------------------------------------------------
# Les conditions
#
# Elles recoivent le contexte et la position du mot suspect. Ecrites une fois,
# elles servent a plusieurs entrees.
# ---------------------------------------------------------------------------

def _precedents(ctx, i: int) -> set[str]:
    """Ce qui precede, sous toutes ses formes.

    « j'ai » compte a la fois comme « j'ai », comme « j' » et comme « ai » :
    une condition qui cherche l'auxiliaire doit le trouver, et une condition
    qui cherche le sujet aussi.
    """
    mot = ctx.mot(i - 1)
    return {mot, ctx.elision(i - 1), ctx.noyau(i - 1)} - {""}


def _precedent(ctx, i: int) -> str:
    """Le mot d'avant, elision comprise : « qu'il » rend « qu' »."""
    return ctx.elision(i - 1) or ctx.mot(i - 1)


def sans_sujet_devant(ctx, i: int) -> bool:
    """Rien devant qui puisse conjuguer ce verbe.

    « il commet une erreur » garde son verbe ; « commet ça va », en tete de
    phrase, n'a personne pour commettre quoi que ce soit.
    """
    if ctx.debut_de_segment(i):
        return True
    precedent = _precedent(ctx, i)
    return (precedent not in SUJETS_DE_VERBE
            and precedent not in {"ne", "n'", "y", "en", "se", "s'",
                                  "me", "m'", "te", "t'", "le", "l'",
                                  "la", "les", "lui", "leur"})


def devant_un_verbe_ou_un_pronom(ctx, i: int) -> bool:
    """Ce qui suit reclame un mot interrogatif ou une conjonction."""
    suivant = ctx.mot(i + 1)
    return (suivant in {"tu", "il", "elle", "on", "nous", "vous", "ils",
                        "elles", "ça", "ca", "c'est", "va", "vas", "allez"}
            or ctx.elision(i + 1) in {"c'", "t'", "qu'", "j'", "n'", "s'"})


def apres(*mots: str) -> Callable:
    """Le mot precedent est l'un de ceux-la, elision comprise."""
    attendus = set(mots)

    def condition(ctx, i: int) -> bool:
        return bool(_precedents(ctx, i) & attendus)
    return condition


def apres_determinant(ctx, i: int) -> bool:
    return _precedent(ctx, i) in DETERMINANTS_DE_NOM


def toujours_en_tete(ctx, i: int) -> bool:
    """Seulement en tete de phrase ou de membre de phrase."""
    return ctx.debut_de_segment(i)


def _suit_un_article(ctx, i):
    from .grammaire import _peut_suivre_un_article

    return _peut_suivre_un_article(ctx, i)


def _et(*conditions: Callable) -> Callable:
    def condition(ctx, i: int) -> bool:
        return all(c(ctx, i) for c in conditions)
    return condition


def _ou(*conditions: Callable) -> Callable:
    def condition(ctx, i: int) -> bool:
        return any(c(ctx, i) for c in conditions)
    return condition


# ---------------------------------------------------------------------------
# La table
#
# Le commentaire de chaque groupe dit ce qui rend la paire sure. Une entree
# qu'on ne sait pas justifier n'a rien a faire ici.
# ---------------------------------------------------------------------------

CONFUSIONS = (
    # « commet » est le verbe commettre (12 837e). « comment » est le 128e
    # mot du francais. Sans sujet devant, le verbe n'a personne pour agir.
    Confusion("commet", "comment",
              _ou(toujours_en_tete, devant_un_verbe_ou_un_pronom),
              "« commet » est le verbe commettre ; ici c'est « comment »"),

    # « sui » existe (rare, juridique). « je sui » ne peut etre que « suis ».
    Confusion("sui", "suis", apres("je", "j'"),
              "avec « je », le verbe être s'écrit « suis »"),

    # « fau » n'existe pas seul en francais courant ; « il faut » si.
    Confusion("fau", "faut", apres("il", "qu'", "ne", "n'"),
              "« il faut » prend un « t »"),

    # « tou » est une interjection rarissime. Devant un determinant ou un
    # verbe, c'est « tout ».
    Confusion("tou", "tout", lambda ctx, i: True,
              "« tout » prend un « t »"),

    # « pri » est un nom (le pri d'un tissu). Apres un auxiliaire, c'est le
    # participe « pris ».
    Confusion("pri", "pris", apres("ai", "as", "a", "avons", "avez", "ont",
                                   "avais", "avait", "avaient"),
              "après l'auxiliaire, c'est le participe « pris »"),

    # « mai » est le mois. En tete de phrase et suivi d'une proposition,
    # c'est la conjonction.
    Confusion("mai", "mais", _et(toujours_en_tete,
                                 lambda ctx, i: ctx.mot(i + 1) not in
                                 {"prochain", "dernier", "juin", "avril",
                                  "2024", "2025", "2026"}),
              "ici « mais » est la conjonction"),

    # « donne » / « donné » : hors de portee sans morphologie. Non traite.

    # « quand » et « quant » : « quant » n'existe que devant « à ».
    Confusion("quant", "quand",
              lambda ctx, i: ctx.mot(i + 1) not in {"à", "a", "au", "aux"},
              "« quant » ne s'emploie que devant « à »"),
    Confusion("quand", "quant",
              lambda ctx, i: ctx.mot(i + 1) in {"à", "au", "aux"}
              and ctx.mot(i + 2) in {"moi", "toi", "lui", "elle", "nous",
                                     "vous", "eux"},
              "devant « à moi », « à lui », c'est « quant »"),

    # « ou » sans accent relie deux choix ; « où » designe le lieu. La regle
    # OU_ACCENT couvre deja le cas general ; celle-ci prend l'interrogation
    # en tete de phrase, qu'elle laissait passer.
    Confusion("ou", "où", _et(toujours_en_tete,
                              lambda ctx, i: ctx.mot(i + 1) in
                              {"est", "sont", "es", "était", "vas", "va",
                               "allez", "tu", "il", "elle", "on"}),
              "« où » désigne le lieu"),

    # « la » article et « là » adverbe : idem, complement de LA_ACCENT. La
    # condition est la meme — rien derriere que « la » puisse determiner.
    Confusion("la", "là", _et(lambda ctx, i: not _suit_un_article(ctx, i + 1),
                              apres("est", "suis", "es", "sommes", "êtes",
                                    "sont", "était", "étais", "sera",
                                    "serai", "seras", "reste", "restes")),
              "« là » désigne le lieu"),

    # « hate » est un mot anglais protege, et « hâte » un mot francais
    # courant. La protection empeche le correcteur de deviner ; ici il ne
    # devine pas, il lit l'auxiliaire : « j'ai hate » n'est pas de l'anglais.
    Confusion("hate", "hâte", apres("ai", "as", "a", "avons", "avez", "ont",
                                    "j'", "avais", "avait", "aurai"),
              "« j'ai hâte » : le mot français prend un accent"),

    # « ces » demonstratif et « ses » possessif. Seul le contexte tranche, et
    # il ne tranche que rarement : on s'en tient au cas ou un possesseur
    # vient d'etre nomme.
    Confusion("ces", "ses", apres("avec", "dans", "sur", "pour", "de", "à"),
              "« ses » marque la possession"),
)


# Index par mot ecrit, pour que la regle ne parcoure pas la table a chaque
# jeton. Plusieurs entrees peuvent viser le meme mot : on les garde toutes,
# dans l'ordre, et la premiere dont la condition est vraie l'emporte.
PAR_MOT: dict[str, list[Confusion]] = {}
for _confusion in CONFUSIONS:
    PAR_MOT.setdefault(_confusion.ecrit, []).append(_confusion)
del _confusion


# Ecart de frequence minimal entre le mot ecrit et celui propose. Une paire
# dont les deux membres sont aussi courants l'un que l'autre ne se tranche
# pas sur un contexte de deux mots.
ECART_MINIMAL = 4


def trouver(ctx, i: int, lexique) -> Confusion | None:
    """La confusion qui s'applique ici, s'il y en a une.

    Le test de frequence est refait a l'execution plutot qu'inscrit dans la
    table : la liste de frequences peut changer, la table ne doit pas avoir a
    suivre.
    """
    mot = ctx.mot(i)
    for confusion in PAR_MOT.get(mot, ()):
        rang_ecrit = lexique.rang(confusion.ecrit)
        rang_voulu = lexique.rang(confusion.voulu)
        if rang_voulu * ECART_MINIMAL > rang_ecrit:
            continue
        if confusion.quand(ctx, i):
            return confusion
    return None
