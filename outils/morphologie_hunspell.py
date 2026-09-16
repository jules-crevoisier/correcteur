# -*- coding: utf-8 -*-
"""Lire la grammaire cachee dans le dictionnaire Hunspell.

Le fichier `fr.dic` ne contient pas de mots flechis : il contient des
radicaux suivis de drapeaux, et `fr.aff` decrit ce que chaque drapeau
fabrique. « afficher/a0p+ » veut dire « conjugue-moi ce verbe selon le
modele a0, et donne-lui les participes p+ ».

    SFX a0 er ons/n'q'l't'   er      ->  affichons
    SFX a0 er ez/n'q'l'm'    er      ->  affichez

`outils/construire_lexique.py` se contentait jusqu'ici de derouler ces
regles et de jeter la liste a plat. Or la regle qui fabrique « affichons »
dit aussi **ce qu'est** « affichons » — et c'est exactement ce qui manque au
correcteur pour accorder un verbe avec son sujet.

Rien n'est devine ici : tout se lit dans le fichier d'affixes, par deux
signes que Dicollecte y a laisses.

**Les elisions.** Chaque regle indique les mots elides qui peuvent la
preceder, et cette liste est une empreinte de la personne :

    j'  « j'affiche »          -> 1re personne du singulier
    s'  « il s'affiche »       -> 3e personne
    m'  absent de « affichons » : on ne dit pas « nous m'affichons »
    t'  absent de « affichez » : on ne dit pas « vous t'affichez »
    q'  absent de l'imperatif  : on ne dit pas « qu'affiche ! »
    d'  present a l'infinitif  : « d'afficher »

Reste a departager « il affiche » de « ils affichent », qui portent la meme
empreinte, et « tu vas » de « ils vont », qui n'en portent aucune — « aller »
n'etant pas pronominal, il n'a pas de « s' ». La terminaison ne suffit pas :
« il vient » finit par « ent ». Mais **l'ordre** des regles, lui, est fiable.
Le francais se conjugue toujours dans le meme sens — je, tu, il, nous, vous,
ils — et un creneau ambigu place juste apres un creneau « vous » est
forcement un pluriel.

**Le « L' ».** Du cote des noms et des adjectifs, les regles portent « L' »
quand leur resultat accepte l'article elide. Or « l' » ne precede qu'un
singulier : « l'affiche » se dit, « l'affiches » non. Le drapeau donne donc
le nombre, gratuitement et sans exception.

Le genre se lit ensuite dans la forme du paradigme lui-meme : le radical est
le masculin singulier, et le feminin pluriel est toujours le feminin
singulier suivi d'un « s ». Quand le paradigme ne se laisse pas lire aussi
proprement — « beau » donne « bel » en plus de « belle » — le genre reste
inconnu. C'est le principe de la maison : mieux vaut ne rien dire.

Ce que ce module **ne sait pas**, et ne peut pas savoir :

- le genre des noms. « affiche » est feminin, le dictionnaire l'ignore : il
  ne connait que les paradigmes a deux genres (« chat »/« chatte ») ;
- la nature des mots. « rouge » peut etre un nom ou un adjectif, rien ne les
  distingue ici ;
- le **nom** des temps. On sait separer l'imparfait du futur, on ne sait pas
  lequel est lequel. Cela suffit : pour accorder un verbe, il faut rester
  dans son temps, pas savoir comment il s'appelle.

Ce dernier point se lit lui aussi dans l'ordre des regles. Le francais se
conjugue toujours dans le meme sens — je, tu, il, nous, vous, ils — et chaque
temps reprend au debut. Un creneau qui recule dans cet ordre ouvre donc un
nouveau temps, et l'on decoupe le modele sans avoir a compter :

    pense pensesx pensons pensez pensent | pensais pensait pensions ...
                                         ^ « je » apres « ils » : on change

Sans ce decoupage, « les gens finit » deviendrait « les gens finirent » —
une 3e personne du pluriel parfaitement correcte, au passe simple, alors que
la phrase etait au present.
"""

from __future__ import annotations

import collections

# Les elisions verbales s'ecrivent en minuscules dans `fr.aff`, les
# nominales en majuscules. Ce seul detail separe les 138 modeles de
# conjugaison des 21 modeles de nom.
ELISIONS_VERBALES = frozenset("jnqdlmts") | {"c"}

# Traits employes par le reste de l'application.
#
#   verbe     1s 2s 3s 1p 2p 3p        personne et nombre
#             inf ppr                  infinitif, participe present
#             i2s i1p i2p              imperatif
#             pms pmp pfs pfp          participe passe, accorde
#   nom       ms mp fs fp              genre connu
#             xs xp                    genre inconnu
NOMBRE_PLURIEL = frozenset({"mp", "fp", "xp", "pmp", "pfp",
                            "1p", "2p", "3p", "i1p", "i2p"})
NOMBRE_SINGULIER = frozenset({"ms", "fs", "xs", "pms", "pfs",
                              "1s", "2s", "3s", "i2s"})

# L'ordre dans lequel le francais se conjugue. Un creneau qui recule dans
# cet ordre annonce un nouveau temps.
ORDRE_DES_PERSONNES = {"1s": 0, "2s": 1, "3s": 2, "1p": 3, "2p": 4, "3p": 5}


def _elisions(drapeaux) -> set[str]:
    """Les elisions d'une regle, reduites a leur initiale : « j' » -> « j »."""
    return {d[0] for d in drapeaux if len(d) == 2 and d[1] == "'"}


def drapeaux_verbaux(aff) -> frozenset[str]:
    """Les modeles de conjugaison, reconnus a leurs elisions minuscules."""
    return frozenset(
        drapeau for drapeau, regles in aff.SFX.items()
        if any(lettre.islower()
               for regle in regles for d in regle.flags for lettre in d[:1])
    )


def appliquer(forme: str, affixe, prefixe: bool = False) -> str | None:
    """Applique un affixe, ou None si sa condition n'est pas remplie."""
    if prefixe:
        if affixe.strip and not forme.startswith(affixe.strip):
            return None
        if not affixe.cond_regexp.search(forme):
            return None
        return affixe.add + forme[len(affixe.strip):]

    if affixe.strip and not forme.endswith(affixe.strip):
        return None
    if not affixe.cond_regexp.search(forme):
        return None
    base = forme[: len(forme) - len(affixe.strip)] if affixe.strip else forme
    return base + affixe.add


# ---------------------------------------------------------------------------
# Les verbes
# ---------------------------------------------------------------------------

def _creneau(elisions: set[str]) -> str:
    """La personne qu'annonce une empreinte d'elisions.

    « 3 » vaut pour les deux 3es personnes, que l'empreinte ne separe pas :
    « il affiche » et « ils affichent » acceptent les memes elisions. C'est
    la place de la regle dans le modele qui tranchera.
    """
    if "j" in elisions:
        return "1s"
    if "s" in elisions or "c" in elisions:
        return "3s"
    if "m" not in elisions and "t" in elisions:
        return "1p"
    if "t" not in elisions and "m" in elisions:
        return "2p"
    if "m" in elisions and "t" in elisions:
        return "2s"
    return "?"


def _voisinages(regles) -> dict[int, tuple[str, str]]:
    """Pour chaque regle, la personne du creneau d'avant et de celui d'apres.

    Un creneau, c'est une suite de regles qui portent la meme empreinte : les
    trois facons d'ecrire le participe present (« -ant », « -cant »,
    « -geant ») n'en forment qu'un. C'est l'unite qui suit l'ordre de la
    conjugaison — je, tu, il, nous, vous, ils — et qui permet de distinguer
    « il vient » de « ils viennent ».
    """
    creneaux: list[tuple[frozenset, list]] = []
    for regle in regles:
        empreinte = frozenset(regle.flags)
        if creneaux and creneaux[-1][0] == empreinte:
            creneaux[-1][1].append(regle)
        else:
            creneaux.append((empreinte, [regle]))

    voisinages = {}
    for rang, (_empreinte, groupe) in enumerate(creneaux):
        avant = _creneau(_elisions(creneaux[rang - 1][0])) if rang else "?"
        suivant = creneaux[rang + 1][0] if rang + 1 < len(creneaux) else frozenset()
        apres = _creneau(_elisions(suivant))
        for regle in groupe:
            voisinages[id(regle)] = (avant, apres)
    return voisinages


def _participe(forme: str, singulier: bool | None = None) -> set[str]:
    """« venu », « venue », « venus », « venues » -> genre et nombre.

    Un participe passe s'accorde comme un adjectif, et Dicollecte le marque
    comme tel : ses regles portent les elisions nominales, « L' » compris.
    Quand ce drapeau est la, il donne le nombre ; sinon la terminaison suffit.
    """
    feminin = forme.endswith("e") or forme.endswith("es")
    if singulier is None:
        pluriel = forme.endswith("es") if feminin else forme.endswith(("s", "x"))
    else:
        pluriel = not singulier
    if feminin:
        return {"pfp" if pluriel else "pfs"}
    if pluriel:
        return {"pmp"}
    # « pris », « mis », « clos » : un participe masculin en « s » ou « x » ne
    # change pas au pluriel.
    return {"pms", "pmp"} if forme.endswith(("s", "x")) else {"pms"}


def traits_verbe(aff, radical: str, drapeau: str) -> list[dict[str, set[str]]]:
    """Le paradigme d'un verbe, un groupe par temps.

    Le premier groupe rassemble ce qui n'a pas de personne — infinitif,
    participes, imperatif ; viennent ensuite les temps, dans l'ordre du
    modele. Accorder un verbe, c'est chercher dans son groupe a lui.
    """
    voisinages = _voisinages(aff.SFX[drapeau])
    hors_temps: dict[str, set[str]] = collections.defaultdict(set)
    temps: list[dict[str, set[str]]] = []
    precedent = None

    for regle in aff.SFX[drapeau]:
        forme = appliquer(radical, regle)
        if not forme:
            continue
        elisions = _elisions(regle.flags)
        avant, apres = voisinages[id(regle)]

        # Un participe passe irregulier s'accorde comme un adjectif, et
        # porte donc les elisions nominales : « pris/D'L'Q' ». D'autres
        # n'acceptent aucune elision de pronom du tout — « eu », « ete ».
        # Dans les deux cas, aucune elision verbale : c'est leur signature.
        if elisions and elisions <= set("DLQ"):
            hors_temps[forme] |= _participe(forme, singulier="L" in elisions)
            continue
        if elisions <= {"q"}:
            hors_temps[forme] |= _participe(forme)
            continue

        # « d' » ne precede qu'une forme nominale du verbe : « d'afficher »,
        # « d'affichant ». Aucune forme conjuguee ne l'accepte.
        if "d" in elisions:
            hors_temps[forme].add("ppr" if forme.endswith("ant") else "inf")
            continue

        # « qu' » precede toute forme conjuguee, sauf l'imperatif : on ne dit
        # pas « qu'affiche ! ».
        if "q" not in elisions:
            fin = ("1p" if forme.endswith("ons")
                   else "2p" if forme.endswith("ez") else "2s")
            hors_temps[forme].add("i" + fin)
            continue

        traits = set()
        if "j" in elisions:
            traits.add("1s")
        if "s" in elisions or "c" in elisions:
            # Le creneau d'avant tranche : apres « vous », c'est « ils ».
            traits.add("3p" if avant == "2p" else "3s")
        if "m" not in elisions and "t" in elisions:
            traits.add("1p")
        if "t" not in elisions and "m" in elisions:
            traits.add("2p")
        if not traits and "m" in elisions and "t" in elisions:
            # Ni « je », ni « il s' » : l'empreinte ne distingue plus « tu
            # vas » de « ils vont », parce qu'« aller » n'est pas
            # pronominal. La place du creneau tranche, comme plus haut :
            # apres « vous », c'est « ils ».
            traits.add("3p" if avant == "2p" else "2s")
        if not traits:
            continue

        # Dicollecte ne dedouble pas les creneaux ou « je » et « tu »
        # s'ecrivent pareil : « je pensais », « tu pensais ». On les rend
        # tous deux, sauf quand le modele donne bien un « tu » a part —
        # « je suis » ne doit pas devenir une 2e personne.
        if "1s" in traits and forme.endswith(("s", "x")) and apres != "2s":
            traits.add("2s")

        rang = min((ORDRE_DES_PERSONNES[trait] for trait in traits
                    if trait in ORDRE_DES_PERSONNES), default=len(ORDRE_DES_PERSONNES))
        if not temps or (precedent is not None and rang < precedent):
            temps.append(collections.defaultdict(set))
        precedent = rang
        temps[-1][forme] |= traits

    return [dict(hors_temps)] + [dict(t) for t in temps]


# ---------------------------------------------------------------------------
# Les noms et les adjectifs
# ---------------------------------------------------------------------------

def traits_nom(aff, radical: str, drapeaux, verbaux) -> dict[str, set[str]]:
    """Le paradigme d'un nom ou d'un adjectif : nombre, et genre si lisible."""
    singuliers: set[str] = set()
    pluriels: set[str] = set()
    flechi = False

    for drapeau in drapeaux:
        if drapeau in verbaux or drapeau not in aff.SFX:
            continue
        for regle in aff.SFX[drapeau]:
            forme = appliquer(radical, regle)
            if not forme:
                continue
            flechi = True
            # « l'affiche » se dit, « l'affiches » non : le drapeau « L' »
            # ne survit qu'au singulier.
            (singuliers if "L'" in regle.flags else pluriels).add(forme)

    if not flechi:
        return _sans_paradigme(radical, drapeaux)

    genre = _lire_le_genre(radical, singuliers, pluriels)
    paradigme: dict[str, set[str]] = collections.defaultdict(set)
    if genre is None:
        for forme in singuliers:
            paradigme[forme].add("xs")
        for forme in pluriels:
            paradigme[forme].add("xp")
        return paradigme

    masculin_s, feminin_s, masculins_p, feminins_p = genre
    paradigme[masculin_s].add("ms")
    paradigme[feminin_s].add("fs")
    for forme in masculins_p:
        paradigme[forme].add("mp")
    for forme in feminins_p:
        paradigme[forme].add("fp")
    return paradigme


def _lire_le_genre(radical, singuliers, pluriels):
    """Separe le masculin du feminin, ou rend None si le paradigme hesite.

    Deux appuis, tous deux sans exception en francais : le radical d'une
    entree Hunspell est le masculin singulier, et le feminin pluriel est le
    feminin singulier suivi d'un « s ». Des que le paradigme ne se plie pas
    a cette lecture — « beau » fabrique « bel » en plus de « belle » — on
    prefere ne pas savoir.
    """
    if len(singuliers) != 2 or radical not in singuliers:
        return None
    feminin_s = (singuliers - {radical}).pop()
    feminin_p = feminin_s + "s"
    if feminin_p not in pluriels:
        return None
    return radical, feminin_s, pluriels - {feminin_p}, {feminin_p}


def _sans_paradigme(radical: str, drapeaux) -> dict[str, set[str]]:
    """Un mot qui ne se flechit pas : « gens », « temps », « auparavant ».

    Son entree porte tout de meme les elisions qu'il accepte, et « L' » y dit
    encore le nombre : « le temps » le prend, « les gens » non.
    """
    if not drapeaux & {"D'", "Q'"}:
        return {}
    if "L'" not in drapeaux:
        return {radical: {"xp"}}
    # Un singulier deja termine par « s », « x » ou « z » n'a pas de regle de
    # pluriel parce qu'il n'en change pas : « le prix », « les prix ».
    if radical.endswith(("s", "x", "z")):
        return {radical: {"xs", "xp"}}
    return {radical: {"xs"}}


# ---------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------

def paradigmes(dictionnaire) -> list[tuple[str, str, list[dict[str, set[str]]]]]:
    """Tous les paradigmes : (lemme, categorie, groupes de formes).

    Un groupe par temps pour les verbes, un seul pour les noms.
    """
    aff = dictionnaire.aff
    verbaux = drapeaux_verbaux(aff)

    entrees: dict[str, set] = {}
    for mot in dictionnaire.dic.words:
        if mot.stem:
            entrees.setdefault(mot.stem, set()).update(mot.flags)

    # Les drapeaux de participe passe ne s'accrochent qu'a des verbes. C'est
    # ce qui les distingue des vrais paradigmes de nom, qui, eux, servent
    # partout.
    ailleurs = set()
    for drapeaux in entrees.values():
        if not drapeaux & verbaux:
            ailleurs |= drapeaux
    participiaux = frozenset(
        d for d in aff.SFX if d not in verbaux and d not in ailleurs)

    resultat = []
    for radical, drapeaux in entrees.items():
        conjugaisons = drapeaux & verbaux
        if conjugaisons:
            groupes: list[dict[str, set[str]]] = []
            for drapeau in sorted(conjugaisons):
                groupes += traits_verbe(aff, radical, drapeau)
            # Les participes passes reguliers vivent dans un drapeau a part
            # (« p+ »), accroche au meme verbe : ils rejoignent le groupe
            # sans personne.
            for drapeau in sorted(drapeaux & participiaux):
                for regle in aff.SFX[drapeau]:
                    forme = appliquer(radical, regle)
                    if forme:
                        traits = _participe(forme, singulier="L'" in regle.flags)
                        groupes[0].setdefault(forme, set()).update(traits)
            # « un être », « des êtres » : un verbe peut aussi porter un
            # paradigme de nom, qui n'a rien d'un participe.
            for forme, traits in traits_nom(
                    aff, radical, drapeaux - verbaux - participiaux, verbaux).items():
                groupes[0].setdefault(forme, set()).update(traits)
            resultat.append((radical, "v", [g for g in groupes if g]))
        else:
            formes = traits_nom(aff, radical, drapeaux, verbaux)
            if formes:
                resultat.append((radical, "n", [formes]))
    return resultat
