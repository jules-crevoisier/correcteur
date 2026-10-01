# -*- coding: utf-8 -*-
"""Un banc d'essai que nous n'avons pas ecrit : les exemples de LanguageTool.

Nos deux corpus ont ete ecrits par ceux qui ecrivaient les regles. Meme le
corpus tenu a l'ecart partage leurs angles morts : on ne pense pas a tester
la faute a laquelle on n'a pas pense.

LanguageTool, le correcteur libre qu'utilisent de nombreux outils, documente
chacune de ses regles francaises par des exemples :

    <example correction="ont">Ils <marker>on</marker> mangé.</example>   une faute
    <example>Ils ont mangé.</example>                                    une phrase juste

Il y en a plus de quinze mille, ecrits par d'autres que nous, sur dix ans.
C'est un banc d'essai tout fait. Il a deux defauts qu'il faut garder en tete :

- il juge le francais **ecrit soutenu**. « je sais pas » y est une faute, et
  Papote la laisse volontairement. Les categories de pure norme (typographie,
  majuscules, ponctuation, tours « critiques ») sont donc ecartees, et
  le registre parle est filtre a la lecture ;
- ses exemples sont faits pour *declencher* une regle : ils sont plus
  difficiles que les messages de tous les jours.

Le fichier (LGPL) n'est pas copie dans le depot : il est telecharge a la
premiere utilisation, a une version figee pour que les chiffres restent
comparables d'un jour a l'autre.

Comme pour nos corpus, il est coupe en deux moities, regle par regle :

    developpement   on peut en lire le detail et s'en servir pour corriger ;
    tenu a l'ecart  on n'en lit que le score.

    python outils/banc_languagetool.py                les deux scores
    python outils/banc_languagetool.py --detail       le detail du developpement
    python outils/banc_languagetool.py --categories   le score par categorie
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

VERSION = "v6.7"
URL = ("https://raw.githubusercontent.com/languagetool-org/languagetool/"
       f"{VERSION}/languagetool-language-modules/fr/src/main/resources/"
       "org/languagetool/rules/fr/grammar.xml")
CACHE = RACINE / "outils" / "cache" / f"languagetool-fr-{VERSION}.xml"

# Ce que Papote ne cherche pas a corriger, par choix.
CATEGORIES_ECARTEES = {
    "CAT_TYPOGRAPHIE",        # espaces insecables, guillemets : en option
    "CAT_MAJUSCULES", "CASING",
    "PONCTUATION_VIRGULE", "PONCTUATION_POINT",
    "CAT_TOURS_CRITIQUES",    # « au jour d'aujourd'hui » : du style
    "CAT_MARQUES_DE_COMMERCE",
    "SEMANTICS",              # dates incoherentes, etc.
    "MULTITOKEN_SPELLING",
}

# La negation sans « ne », « y a », « faut que » : du francais parle, que
# LanguageTool corrige et que Papote laisse.
_REGISTRE_PARLE = re.compile(
    r"\b(ne|n['’])\b|\b(il y a|il faut)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Exemple:
    regle: str
    categorie: str
    fautif: str
    attendu: str


def telecharger() -> Path:
    if not CACHE.is_file():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"telechargement de LanguageTool {VERSION}...", file=sys.stderr)
        with urllib.request.urlopen(URL, timeout=120) as reponse:
            CACHE.write_bytes(reponse.read())
    return CACHE


def _texte(element: ET.Element) -> tuple[str, str | None]:
    """Le texte de l'exemple, et ce qui est entre les balises <marker>."""
    marque = None
    morceaux = [element.text or ""]
    for enfant in element:
        if enfant.tag == "marker":
            marque = "".join(enfant.itertext())
            morceaux.append("\x00")
        else:
            morceaux.append("".join(enfant.itertext()))
        morceaux.append(enfant.tail or "")
    return "".join(morceaux), marque


def _nettoyer(texte: str) -> str:
    return re.sub(r"\s+", " ", texte).strip()


def extraire(chemin: Path | None = None):
    """(fautes, phrases justes), chacune portant sa regle et sa categorie."""
    racine = ET.parse(chemin or telecharger()).getroot()
    fautes: list[Exemple] = []
    justes: list[Exemple] = []
    for categorie in racine.iter("category"):
        id_categorie = categorie.get("id", "")
        if id_categorie in CATEGORIES_ECARTEES or categorie.get("default") == "off":
            continue
        for regle, parent in _regles(categorie):
            if regle.get("default") == "off":
                continue
            for exemple in regle.iter("example"):
                texte, marque = _texte(exemple)
                if exemple.get("type") == "incorrect" and exemple.get("correction") is None:
                    continue
                correction = exemple.get("correction")
                if correction is None:
                    phrase = _nettoyer(texte.replace("\x00", marque or ""))
                    if phrase:
                        justes.append(Exemple(parent, id_categorie, phrase, phrase))
                    continue
                if marque is None or not correction:
                    continue
                # Plusieurs corrections possibles : la premiere est la
                # preferee, mais toutes sont recevables.
                premiere = correction.split("|")[0]
                fautif = _nettoyer(texte.replace("\x00", marque))
                attendu = _nettoyer(texte.replace("\x00", premiere))
                if fautif and fautif != attendu:
                    fautes.append(Exemple(parent, id_categorie, fautif, attendu))
                    for autre in correction.split("|")[1:]:
                        _ALTERNATIVES[fautif].add(
                            _nettoyer(texte.replace("\x00", autre)))
    return fautes, justes


_ALTERNATIVES: dict[str, set[str]] = defaultdict(set)


def _regles(categorie: ET.Element):
    """Chaque <rule>, avec l'identifiant qui la nomme.

    Dans un <rulegroup>, c'est le groupe qui porte l'identifiant : toutes ses
    variantes tombent ainsi dans la meme moitie du banc.
    """
    for enfant in categorie:
        if enfant.tag == "rule":
            yield enfant, enfant.get("id", "")
        elif enfant.tag == "rulegroup":
            if enfant.get("default") == "off":
                continue
            for regle in enfant.iter("rule"):
                yield regle, enfant.get("id", "")


def moitie(regle: str) -> str:
    """« dev » ou « ecart », stable d'une execution a l'autre."""
    empreinte = hashlib.sha1(regle.encode("utf-8")).digest()[0]
    return "dev" if empreinte % 2 == 0 else "ecart"


def evaluer(correcteur, fautes, justes) -> dict:
    corrigees, ratees, fausses = [], [], []
    for e in fautes:
        obtenu = correcteur.corriger(e.fautif, mise_en_forme=False)[0]
        if obtenu == e.attendu or obtenu in _ALTERNATIVES.get(e.fautif, ()):
            corrigees.append((e, obtenu))
        elif obtenu == e.fautif:
            ratees.append((e, obtenu))
        else:
            # Papote a touche la phrase, mais pas comme il fallait.
            fausses.append((e, obtenu))
    intactes, abimees = [], []
    for e in justes:
        obtenu = correcteur.corriger(e.fautif, mise_en_forme=False)[0]
        (intactes if obtenu == e.fautif else abimees).append((e, obtenu))
    return {"corrigees": corrigees, "ratees": ratees, "fausses": fausses,
            "intactes": intactes, "abimees": abimees}


def _filtrer_registre(exemples):
    return [e for e in exemples if not _REGISTRE_PARLE.search(e.fautif)
            and not _REGISTRE_PARLE.search(e.attendu)]


def charger(moitie_voulue: str | None = None):
    fautes, justes = extraire()
    fautes, justes = _filtrer_registre(fautes), _filtrer_registre(justes)
    if moitie_voulue:
        fautes = [e for e in fautes if moitie(e.regle) == moitie_voulue]
        justes = [e for e in justes if moitie(e.regle) == moitie_voulue]
    return fautes, justes


def _resume(nom: str, r: dict) -> None:
    total_f = len(r["corrigees"]) + len(r["ratees"]) + len(r["fausses"])
    total_j = len(r["intactes"]) + len(r["abimees"])
    print(f"\n  {nom}")
    print(f"    fautes corrigees      {len(r['corrigees']):5d} / {total_f}"
          f"  ({len(r['corrigees']) / max(1, total_f):.0%})")
    print(f"    fautes mal corrigees  {len(r['fausses']):5d}"
          f"  (touchees, mais pas comme il fallait)")
    print(f"    phrases justes abimees {len(r['abimees']):4d} / {total_j}"
          f"  ({len(r['abimees']) / max(1, total_j):.1%})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--categories", action="store_true")
    parser.add_argument("--max", type=int, default=60)
    args = parser.parse_args()

    from papote.moteur import construire
    correcteur = construire()

    for moitie_voulue, nom in (("dev", "DEVELOPPEMENT"), ("ecart", "TENU A L'ECART")):
        fautes, justes = charger(moitie_voulue)
        r = evaluer(correcteur, fautes, justes)
        _resume(f"{nom} — LanguageTool {VERSION}", r)
        if args.categories:
            par = Counter(e.categorie for e in fautes)
            ok = Counter(e.categorie for e, _ in r["corrigees"])
            abime = Counter(e.categorie for e, _ in r["abimees"])
            for cat, n in par.most_common():
                print(f"      {cat:28s} {ok[cat]:4d}/{n:<5d}  abimees {abime[cat]}")
        if args.detail and moitie_voulue == "dev":
            print("\n  -- phrases justes abimees --")
            for e, o in r["abimees"][:args.max]:
                print(f"   [{e.regle}] {e.fautif}\n      -> {o}")
            print("\n  -- fautes mal corrigees --")
            for e, o in r["fausses"][:args.max]:
                print(f"   [{e.regle}] {e.fautif}\n      attendu {e.attendu}\n      obtenu  {o}")


if __name__ == "__main__":
    main()
