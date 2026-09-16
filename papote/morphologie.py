# -*- coding: utf-8 -*-
"""Ce qu'est chaque mot : personne, nombre, genre.

Le lexique sait si un mot existe. Il ne sait pas que « pensent » est une 3e
personne du pluriel, ni que « chevaux » est le pluriel de « cheval ». Les
regles d'accord devaient donc le deviner, chacune a sa facon :

    _pluriels(mot)          « cheval » -> « chevaux », par une regle ecrite
                            a la main, qui ratait « bijou » -> « bijoux »
    _est_pluriel(mot)       « finit par s ou x », qui prenait « le temps »,
                            « la souris » et « le prix » pour des pluriels
    infinitif_premier_groupe  ne voyait que les verbes en « -er », soit un
                            verbe sur six dans une phrase ordinaire

Tout cela est ecrit noir sur blanc dans le dictionnaire Hunspell, sous les
drapeaux qui decrivent les paradigmes. `outils/morphologie_hunspell.py`
explique comment on l'en extrait ; ce module se contente de le lire.

Deux tables, toutes deux triees et consultees par dichotomie, sans le moindre
index construit au demarrage :

    analyses_fr.txt.gz    ce qu'est une forme        pensent   3p    penser
    flexions_fr.txt.gz    le paradigme d'un lemme    penser  v  ...;...;...

Les traits tiennent en deux ou trois lettres :

    verbe     1s 2s 3s 1p 2p 3p   personne et nombre
              inf ppr             infinitif, participe present
              i2s i1p i2p         imperatif
              pms pmp pfs pfp     participe passe, accorde
    nom       ms mp fs fp         genre connu (« chat » / « chatte »)
              xs xp               genre inconnu (« affiche », « bateau »)

Le paradigme d'un verbe arrive **decoupe par temps**. C'est ce qui permet
d'accorder sans deplacer : dans « les gens finit », on cherche la 3e personne
du pluriel *dans le temps de « finit »*, ce qui donne « finissent » et non
« finirent », qui serait un passe simple parfaitement correct mais hors sujet.

Comme partout ici, le doute fait taire : deux lemmes qui ne repondent pas la
meme chose, et `accorder` ne rend rien.
"""

from __future__ import annotations

import bisect
import gzip
from pathlib import Path

from .chemins import dossier_donnees

# Les traits qui marquent un pluriel, et ceux qui marquent un singulier. Un
# mot peut porter les deux — « le prix », « les prix » — et c'est justement
# ce qu'il faut savoir pour ne pas le corriger.
PLURIELS = frozenset({"mp", "fp", "xp", "pmp", "pfp", "1p", "2p", "3p",
                      "i1p", "i2p"})
SINGULIERS = frozenset({"ms", "fs", "xs", "pms", "pfs", "1s", "2s", "3s",
                        "i2s"})

# Les traits d'une forme conjuguee — par opposition a un nom, un participe
# ou un infinitif.
CONJUGUES = frozenset({"1s", "2s", "3s", "1p", "2p", "3p"})

NOMINAUX = frozenset({"ms", "mp", "fs", "fp", "xs", "xp"})
NOMS_PLURIELS = frozenset({"mp", "fp", "xp"})
NOMS_SINGULIERS = frozenset({"ms", "fs", "xs"})

# Le participe passe, qui s'accorde comme un adjectif.
PARTICIPES = frozenset({"pms", "pmp", "pfs", "pfp"})

# Tel qu'il s'ecrit apres « avoir » quand rien ne l'accorde : « ils ont
# pris », « elle a fini ».
PARTICIPES_MASCULINS = frozenset({"pms", "pmp"})

# Le pluriel qui correspond a chaque singulier, genre garde.
PLURIEL_DE = {"ms": "mp", "fs": "fp", "xs": "xp",
              "pms": "pmp", "pfs": "pfp"}
SINGULIER_DE = {p: s for s, p in PLURIEL_DE.items()}


class Morphologie:
    """La grammaire de chaque mot, telle que le dictionnaire la connait."""

    def __init__(self, dossier: Path | None = None,
                 analyses: list[str] | None = None,
                 flexions: list[str] | None = None):
        """`analyses` et `flexions` permettent aux tests d'injecter une table."""
        self._dossier = dossier
        self._analyses = sorted(analyses) if analyses is not None else None
        self._flexions = sorted(flexions) if flexions is not None else None

    @classmethod
    def depuis_paradigmes(cls, paradigmes: dict) -> "Morphologie":
        """Construit une table a partir de `{lemme: [{forme: traits}, ...]}`.

        Reservee aux tests : elle evite d'avoir a ecrire le format a la main.
        """
        flexions, analyses = [], {}
        for lemme, groupes in paradigmes.items():
            categorie = "v" if any(t & CONJUGUES or t & {"inf"}
                                   for g in groupes for t in g.values()) else "n"
            flexions.append("{}\t{}\t{}".format(
                lemme, categorie,
                ";".join(" ".join(f"{f}:{','.join(sorted(t))}"
                                  for f, t in sorted(g.items()))
                         for g in groupes)))
            for groupe in groupes:
                for forme, traits in groupe.items():
                    connus, lemmes = analyses.setdefault(forme, (set(), set()))
                    connus |= set(traits)
                    lemmes.add(lemme)
        return cls(analyses=[f"{f}\t{','.join(sorted(t))}\t{' '.join(sorted(l))}"
                             for f, (t, l) in analyses.items()],
                   flexions=flexions)

    # -- chargement ---------------------------------------------------------

    def _lire(self, nom: str) -> list[str]:
        chemin = (self._dossier or dossier_donnees()) / nom
        if not chemin.is_file():
            # La morphologie est un supplement : sans elle les regles
            # d'accord se taisent, le reste du correcteur fonctionne.
            return []
        with gzip.open(chemin, "rt", encoding="utf-8") as f:
            return f.read().split("\n")

    @property
    def analyses(self) -> list[str]:
        if self._analyses is None:
            self._analyses = self._lire("analyses_fr.txt.gz")
        return self._analyses

    @property
    def flexions(self) -> list[str]:
        if self._flexions is None:
            self._flexions = self._lire("flexions_fr.txt.gz")
        return self._flexions

    def charger(self) -> None:
        """Force la lecture des fichiers, pour la faire au moment choisi."""
        self.analyses  # noqa: B018
        self.flexions  # noqa: B018

    @staticmethod
    def _ligne(lignes: list[str], cle: str) -> str | None:
        position = bisect.bisect_left(lignes, cle)
        if position >= len(lignes):
            return None
        ligne = lignes[position]
        return ligne if ligne.startswith(cle + "\t") else None

    # -- consultation -------------------------------------------------------

    def _entree(self, mot: str) -> tuple[frozenset[str], tuple[str, ...]]:
        if not mot:
            return frozenset(), ()
        ligne = self._ligne(self.analyses, mot)
        if ligne is None and mot[:1].isupper():
            # « Pense » en debut de phrase vaut « pense ».
            ligne = self._ligne(self.analyses, mot.lower())
        if ligne is None:
            return frozenset(), ()
        _forme, traits, lemmes = ligne.split("\t")
        return frozenset(traits.split(",")), tuple(lemmes.split(" "))

    def traits(self, mot: str) -> frozenset[str]:
        """Tout ce que ce mot peut etre. Vide si le dictionnaire l'ignore."""
        return self._entree(mot)[0]

    def lemmes(self, mot: str) -> tuple[str, ...]:
        """Les mots dont celui-ci est une forme : « pensent » -> « penser »."""
        return self._entree(mot)[1]

    def connait(self, mot: str) -> bool:
        return bool(self.traits(mot))

    def paradigme(self, lemme: str) -> list[dict[str, frozenset[str]]]:
        """Toutes les formes d'un lemme, un groupe par temps."""
        ligne = self._ligne(self.flexions, lemme)
        if ligne is None:
            return []
        _lemme, _categorie, corps = ligne.split("\t")
        groupes = []
        for morceau in corps.split(";"):
            groupe = {}
            for entree in morceau.split(" "):
                forme, _, traits = entree.rpartition(":")
                if forme:
                    groupe[forme] = frozenset(traits.split(","))
            groupes.append(groupe)
        return groupes

    # -- questions posees par les regles ------------------------------------

    def est(self, mot: str, *traits: str) -> bool:
        """Le mot peut-il porter l'un de ces traits ?"""
        return bool(self.traits(mot) & frozenset(traits))

    def seulement(self, mot: str, *traits: str) -> bool:
        """Le mot ne peut-il etre *que* cela ?

        C'est la question qui compte pour une regle d'accord : « pensent »
        n'est qu'une 3e personne du pluriel, alors que « pense » est aussi
        un imperatif, et « affiche » aussi un nom.
        """
        connus = self.traits(mot)
        return bool(connus) and connus <= frozenset(traits)

    def pluriel(self, mot: str) -> bool:
        """Ce mot est-il forcement un pluriel ?

        « les prix » et « le prix » s'ecrivent pareil : la question n'a pas
        de reponse, et la regle qui la pose doit s'abstenir.
        """
        connus = self.traits(mot)
        return bool(connus & PLURIELS) and not (connus & SINGULIERS)

    def singulier(self, mot: str) -> bool:
        connus = self.traits(mot)
        return bool(connus & SINGULIERS) and not (connus & PLURIELS)

    def nom(self, mot: str) -> bool:
        """Ce mot peut-il etre un nom ou un adjectif ?"""
        return self.est(mot, *NOMINAUX)

    def nom_pluriel(self, mot: str) -> bool:
        """Lu comme un nom, ce mot est-il forcement un pluriel ?

        La question ne porte que sur la lecture nominale : « choses » est
        aussi une 2e personne du verbe « choser », que personne n'emploie, et
        cela ne l'empeche pas d'etre un pluriel sans ambiguite. « souris »,
        lui, est un singulier autant qu'un pluriel — la question a donc pour
        reponse « non », et la regle qui la pose s'abstient.
        """
        connus = self.traits(mot) & NOMINAUX
        return bool(connus & NOMS_PLURIELS) and not (connus & NOMS_SINGULIERS)

    def verbe(self, mot: str) -> bool:
        """Ce mot peut-il etre un verbe conjugue ?"""
        return self.est(mot, *CONJUGUES)

    # -- accord -------------------------------------------------------------

    def accorder(self, mot: str, cibles) -> str | None:
        """La forme du meme mot qui porte l'un de ces traits.

        On cherche dans le groupe ou figure le mot ecrit — c'est-a-dire, pour
        un verbe, dans son temps. « finit » est un present : sa 3e personne
        du pluriel est « finissent », pas « finirent ».

        Rien n'est rendu si deux lemmes proposent des formes differentes :
        devant « pense », qui peut venir de « penser » comme de « pense »,
        on ne choisit pas a la place de l'utilisateur.
        """
        cibles = frozenset(cibles if not isinstance(cibles, str) else [cibles])
        if not cibles:
            return None

        reponses = set()
        for lemme in self.lemmes(mot):
            for groupe in self.paradigme(lemme):
                if mot not in groupe and mot.lower() not in groupe:
                    continue
                trouvees = {f for f, traits in groupe.items() if traits & cibles}
                trouvees.discard(mot)
                trouvees.discard(mot.lower())
                if not trouvees:
                    # Le mot figure aussi ailleurs : « pense » est un
                    # imperatif avant d'etre un present, et l'imperatif n'a
                    # pas de 3e personne.
                    continue
                if len(trouvees) > 1:
                    choisie = _la_plus_proche(mot, trouvees)
                    if choisie is None:
                        # Le temps offre deux formes egalement plausibles
                        # pour la meme personne : on ne tranche pas.
                        return None
                    trouvees = {choisie}
                reponses |= trouvees
                break

        if len(reponses) != 1:
            return None
        return reponses.pop()

    def forme(self, mot: str, cibles) -> str | None:
        """Comme `accorder`, mais sans rester dans le temps du mot ecrit.

        C'est ce qu'il faut pour un participe ou un infinitif, qui n'ont pas
        de temps : apres « ils ont », « prit » doit devenir « pris », et
        « pris » ne vit pas dans le passe simple ou « prit » se trouve.
        """
        cibles = frozenset(cibles if not isinstance(cibles, str) else [cibles])
        reponses = set()
        for lemme in self.lemmes(mot):
            trouvees = set()
            for groupe in self.paradigme(lemme):
                trouvees |= {f for f, traits in groupe.items()
                             if traits & cibles}
            trouvees.discard(mot)
            trouvees.discard(mot.lower())
            if len(trouvees) > 1:
                choisie = _la_plus_proche(mot, trouvees)
                if choisie is None:
                    return None
                trouvees = {choisie}
            reponses |= trouvees
        if len(reponses) != 1:
            return None
        return reponses.pop()

    def au_pluriel(self, mot: str) -> str | None:
        """« cheval » -> « chevaux », « bijou » -> « bijoux », genre garde."""
        cibles = {PLURIEL_DE[t] for t in self.traits(mot) if t in PLURIEL_DE}
        return self.accorder(mot, cibles) if cibles else None

    def au_singulier(self, mot: str) -> str | None:
        cibles = {SINGULIER_DE[t] for t in self.traits(mot) if t in SINGULIER_DE}
        return self.accorder(mot, cibles) if cibles else None


def _la_plus_proche(mot: str, formes: set[str]) -> str | None:
    """Celle qui prolonge le plus longtemps le mot ecrit.

    « pouvoir » a deux premieres personnes, « peux » et « puis », et les deux
    sont justes. Devant « je peut », c'est « peux » qu'on veut : il partage
    deux lettres avec ce qui est ecrit, « puis » une seule. Le radical commun
    designe la meme serie, c'est pourquoi ce depart n'est pas un hasard.

    A egalite, rien : deux formes aussi proches l'une que l'autre ne se
    departagent pas.
    """
    def commun(forme: str) -> int:
        n = 0
        for a, b in zip(mot.lower(), forme.lower()):
            if a != b:
                break
            n += 1
        return n

    classees = sorted(formes, key=lambda f: (-commun(f), len(f), f))
    if len(classees) > 1 and commun(classees[0]) == commun(classees[1]):
        return None
    return classees[0]
