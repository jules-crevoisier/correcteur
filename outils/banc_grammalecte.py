# -*- coding: utf-8 -*-
"""Un second banc d'essai que nous n'avons pas ecrit : les tests de Grammalecte.

Grammalecte (Olivier R., GPL 3), le correcteur grammatical libre de
LibreOffice, de Firefox et de Thunderbird, ecrit ses regles dans un seul
fichier, « gc_lang/fr/rules.grx », et chaque regle y porte ses tests :

    TEST: au {{moi}} d’avril                          ->> mois        une faute
    TEST: Ce qui fait en tout deux personnes.                         une phrase juste

Grammalecte les rejoue tous a chaque version (« make.py fr -t ») : aucune de
ses regles ne passe sans eux. Il y en a quatorze mille, dont pres de six
mille fautes, ecrits sur quinze ans par d'autres que nous et d'autres que
LanguageTool. Les deux bancs se completent : leurs auteurs n'ont pas les
memes angles morts.

Le format, tel que le lit « gc_core/py/lang_core/tests_core.py » :

- chaque faute est entre {{ }} ; apres « ->> », les suggestions, une liste
  par faute, separees par « ||| », les variantes recevables par « | » ;
- une ligne qui commence par « __ocr__ », « __neg__ »... ne vaut que si
  cette option, coupee par defaut, est allumee : elle est ecartee ;
- une faute signalee sans suggestion ne dit pas ce qu'il faut ecrire : un
  correcteur qui reecrit la phrase, comme Papote, ne peut pas s'y mesurer.
  Elle est comptee a part, et laissee.

Les suggestions sont celles que Grammalecte fait lui-meme, faute par faute :
mises bout a bout, elles ne font pas toujours une phrase juste (« en
{{pleine}} {{foret}} ->> plein|||forêt »). Chaque faute est donc jugee a sa
place, comme le fait Grammalecte : corrigee si Papote y met l'une des
suggestions et ne touche a rien d'autre dans la phrase ; laissee s'il n'y
touche pas ; mal corrigee sinon. L'apostrophe droite et la courbe valent la
meme lettre.

Ce qui est ecarte, comme pour le banc LanguageTool :

- les options de pure norme : typographie (espaces, guillemets, apostrophe
  typographique, ecriture epicene, nombres, unites), majuscules, virgules,
  OCR, chimie, balisage ; le style (« populaire », pleonasmes, repetitions) ;
  la validite des dates ; et toute faute dont la correction ne change que
  des espaces, des points ou des majuscules (« O.R. » / « OR ») ;
- l'option « neg » (« ne » oublie) et, plus largement, toute correction
  attendue qui *ajoute* un « ne », ou le « il » de « il y a », « il faut » :
  c'est du francais parle, que Papote laisse volontairement ;
- la section « Tests repris de LanguageTool » : ces phrases sont deja dans
  l'autre banc, elles ne compteraient pas deux fois.

Les phrases justes viennent des tests sans {{ }} : ce sont souvent des pieges
poses expres (« Quelle mouche vous a piqués ? »), et, en fin de fichier, des
textes entiers (Maupassant, Poe, Moliere) qui ne doivent rien declencher.

Un second jeu de phrases justes, plus proche de la vraie vie, est le fichier
de citations du Wiktionnaire que Grammalecte garde pour traquer ses fausses
alertes (« gc_lang/fr/tests/test_wiktionary_citations.txt », 350 000
citations relues et corrigees par son auteur ; textes CC BY-SA). Ce sont des
phrases d'auteurs, de journaux, de lois : une phrase abimee y est presque
toujours une fausse alerte. Leur francais est parfois ancien (« poëte »,
« j'avois ») : le detail le montre ; les citations imprimees avec le s long
(« eſt »), d'avant 1800, sont laissees. Un echantillon fixe d'une phrase sur
cent suffit (3 400 phrases, quelques minutes).

Les fichiers ne sont pas copies dans le depot : ils sont telecharges a la
premiere utilisation, depuis le miroir GitHub du depot officiel (qui garde
les commits de l'auteur), a un commit fige pour que les chiffres restent
comparables d'un jour a l'autre.

Comme pour le banc LanguageTool, il est coupe en deux moities, regle par
regle (et, pour les citations, phrase par phrase) :

    developpement   on peut en lire le detail et s'en servir pour corriger ;
    tenu a l'ecart  on n'en lit que le score.

    python outils/banc_grammalecte.py                les deux scores
    python outils/banc_grammalecte.py --detail       le detail du developpement
    python outils/banc_grammalecte.py --categories   le score par option
    python outils/banc_grammalecte.py --citations    et les citations du Wiktionnaire
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "outils"))

from banc_languagetool import _resume, moitie  # noqa: E402

# Grammalecte 2.3.0, miroir quotidien du depot officiel.
VERSION = "2.3.0"
COMMIT = "08511c222029b3be20bf547563315d10fb48d44b"
_BASE = f"https://raw.githubusercontent.com/Pofilo/grammalecte/{COMMIT}/gc_lang/fr/"
URL_REGLES = _BASE + "rules.grx"
URL_CITATIONS = _BASE + "tests/test_wiktionary_citations.txt"
CACHE = RACINE / "outils" / "cache"
CACHE_REGLES = CACHE / f"grammalecte-{VERSION}-rules.grx"
CACHE_CITATIONS = CACHE / f"grammalecte-{VERSION}-citations-wiktionnaire.txt"

# Les options de Grammalecte (« OPT/... » en tete de rules.grx) que Papote ne
# cherche pas a corriger, par choix.
OPTIONS_ECARTEES = {
    # typographie
    "typo", "apos", "eepi", "esp", "tab", "nbsp", "unit", "num", "nf",
    "liga", "mapos", "chim", "virg", "poncfin", "ocr",
    # majuscules
    "maj", "minis",
    # style : « malgre que », pleonasmes, repetitions
    "bs", "pleo", "redon1", "redon2",
    # registre parle : la negation sans « ne »
    "neg",
    # dates incoherentes, mots composes inconnus, balisage
    "date", "mc", "html", "latex", "md", "idrule",
}
OPTIONS_GARDEES = {
    "conf", "loc", "gn", "infi", "conj", "ppas", "imp", "inte", "vmode",
    "tu", "eleu",
}
_OPTIONS = OPTIONS_ECARTEES | OPTIONS_GARDEES

# Sections de tests sans regle qu'il faut laisser : deja dans l'autre banc.
SECTIONS_ECARTEES = {"Tests repris de LanguageTool"}

# Une correction attendue qui ajoute l'un de ces tours est du registre soutenu
# impose au parle : « j'ai pas » -> « je n'ai pas », « faut » -> « il faut ».
_AJOUTS_PARLES = [re.compile(m, re.IGNORECASE) for m in (
    r"\bne\b", r"\bn['’]", r"\bil y a\b", r"\bil y avait\b",
    r"\bil faut\b", r"\bil fallait\b", r"\bil faudra\b", r"\bil faudrait\b",
)]

_ENTETE = re.compile(r"^__(\S+?)__(?=\s|$)")
_OPTION_ENTETE = re.compile(r"^[\[<][^\]>]*[\]>]/(\w+)\(")
_OPTION_ACTION = re.compile(r"<<-.*?/(\w+)/")
_OPTION_CONDITION = re.compile(r"option\(\"(\w+)\"\)")
_SECTION = re.compile(r"^!!!(?!!)\s*(.*?)\s*!*\s*$")
_OPTION_TEST = re.compile(r"^__(\w+)__ ")
_FAUTE = re.compile(r"\{\{(.*?)\}\}")


@dataclass(frozen=True)
class Faute:
    """Une faute soulignee : `fautif[debut:fin]`, et ce qui peut la remplacer."""
    regle: str
    categorie: str
    fautif: str
    debut: int
    fin: int
    suggestions: tuple[str, ...]
    places: tuple[tuple[int, int], ...] = ()   # toutes les fautes de la phrase

    @property
    def attendu(self) -> str:
        return self.fautif[:self.debut] + self.suggestions[0] + self.fautif[self.fin:]

    def marquee(self) -> str:
        return (self.fautif[:self.debut] + "[" + self.fautif[self.debut:self.fin]
                + "]" + self.fautif[self.fin:])


@dataclass(frozen=True)
class Juste:
    regle: str
    categorie: str
    fautif: str          # le nom est celui du banc LanguageTool : la phrase lue


def _telecharger(url: str, chemin: Path) -> Path:
    if not chemin.is_file():
        chemin.parent.mkdir(parents=True, exist_ok=True)
        print(f"telechargement de {chemin.name}...", file=sys.stderr)
        with urllib.request.urlopen(url, timeout=300) as reponse:
            donnees = reponse.read()
        chemin.write_bytes(donnees)
    return chemin


def telecharger() -> Path:
    return _telecharger(URL_REGLES, CACHE_REGLES)


def telecharger_citations() -> Path:
    return _telecharger(URL_CITATIONS, CACHE_CITATIONS)


def _nettoyer(texte: str) -> str:
    return re.sub(r"\s+", " ", texte).strip()


def _lire_tests(chemin: Path):
    """(regle, options de la regle, ligne de test), dans l'ordre du fichier.

    Une regle commence par « __nom__ » (graphe) ou « __[i]/conf(nom)__ »
    (expression rationnelle). Son option est dans l'en-tete ou dans ses
    actions (« <<- /gn/ ... », « <<- option("eepi") and ... »). Les tests qui suivent un titre « !!! » sans
    regle (« Tests historiques », « Le Horla »...) portent le nom du titre.
    """
    options: dict[str, set[str]] = {}
    regle = ""
    tests = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        m = _ENTETE.match(ligne)
        if m:
            entete = m.group(1)
            nom = re.search(r"\((\w+)\)", entete)
            # « !7 » : la priorite de la regle, pas son nom.
            regle = re.sub(r"!\d+$", "", nom.group(1) if nom else entete)
            options.setdefault(regle, set())
            opt = _OPTION_ENTETE.match(entete)
            if opt and opt.group(1) in _OPTIONS:
                options[regle].add(opt.group(1))
            # Une regle courte tient sur une ligne : motif et action compris.
            ligne = ligne[m.end():]
        else:
            m = _SECTION.match(ligne)
            if m and m.group(1):
                regle = "§" + m.group(1)
                options.setdefault(regle, set())
                continue
        if "<<-" in ligne and regle:
            for opt in _OPTION_ACTION.findall(ligne) + _OPTION_CONDITION.findall(ligne):
                if opt in _OPTIONS:
                    options[regle].add(opt)
            continue
        if ligne.startswith("TEST:"):
            tests.append((regle, ligne[5:].strip()))
    return [(r, frozenset(options.get(r, ())), t) for r, t in tests]


def _decouper(test: str):
    """(texte annote, [suggestions de chaque faute] ou None).

    « ->> » suivi de rien : les fautes sont signalees sans suggestion.
    « ->> "" » : la suggestion est d'effacer.
    """
    if "->>" not in test:
        return test.strip(), None
    texte, suggestions = test.split("->>", 1)
    suggestions = suggestions.strip()
    if not suggestions:
        return texte.strip(), None
    if len(suggestions) >= 2 and suggestions[0] == suggestions[-1] == '"':
        suggestions = suggestions[1:-1]
    return texte.strip(), [tuple(s.split("|")) for s in suggestions.split("|||")]


def _typographie_seule(fautif: str, suggestion: str) -> bool:
    """« Mr Paul » / « Mr Paul » (insecable), « O.R. » / « OR » : rien que la
    norme typographique, que Papote n'impose pas. Le trait d'union, lui, est
    de l'orthographe (« sous culture » / « sous-culture ») : il compte."""
    def squelette(texte: str) -> str:
        texte = re.sub(r"[\s\u00a0\u202f]+", " ", texte.replace("’", "'"))
        return texte.replace(".", "").strip().lower()
    return squelette(fautif) == squelette(suggestion)


def _ajoute_du_parle(fautif: str, attendu: str) -> bool:
    return any(len(m.findall(attendu)) > len(m.findall(fautif))
               for m in _AJOUTS_PARLES)


def categorie(options: frozenset) -> str:
    return "+".join(sorted(options)) or "sans option"


def _ecartee(regle: str, options: frozenset) -> bool:
    return bool(options & OPTIONS_ECARTEES) or regle[1:] in SECTIONS_ECARTEES


def extraire(chemin: Path | None = None):
    """(fautes, phrases justes, decompte de ce qui a ete laisse).

    Une phrase a plusieurs {{ }} donne plusieurs fautes : chacune est jugee
    a sa place (voir `juger`).
    """
    fautes: list[Faute] = []
    justes: list[Juste] = []
    laisses = Counter()
    for regle, options, test in _lire_tests(chemin or telecharger()):
        if _OPTION_TEST.match(test):
            laisses["option coupee par defaut"] += 1
            continue
        if _ecartee(regle, options):
            laisses["option ou section ecartee"] += 1
            continue
        annote, suggestions = _decouper(test)
        annote = _nettoyer(annote)
        places = []
        morceaux = []
        position = 0
        for m in _FAUTE.finditer(annote):
            morceaux.append(annote[position:m.start()])
            debut = sum(map(len, morceaux))
            morceaux.append(m.group(1))
            places.append((debut, debut + len(m.group(1))))
            position = m.end()
        morceaux.append(annote[position:])
        phrase = "".join(morceaux)
        if not places:
            if phrase:
                justes.append(Juste(regle, categorie(options), phrase))
            continue
        if suggestions is None:
            laisses["faute signalee sans suggestion"] += len(places)
            continue
        if len(suggestions) != len(places):
            laisses["suggestions mal appariees"] += len(places)
            continue
        for (debut, fin), propositions in zip(places, suggestions):
            faute = Faute(regle, categorie(options), phrase, debut, fin,
                          propositions, tuple(places))
            if _typographie_seule(phrase[debut:fin], propositions[0]):
                laisses["typographie seule"] += 1
                continue
            if _ajoute_du_parle(phrase, faute.attendu):
                laisses["registre parle"] += 1
                continue
            fautes.append(faute)
    return fautes, justes, laisses


def charger(moitie_voulue: str | None = None):
    fautes, justes, _ = extraire()
    if moitie_voulue:
        fautes = [e for e in fautes if moitie(e.regle) == moitie_voulue]
        justes = [e for e in justes if moitie(e.regle) == moitie_voulue]
    return fautes, justes


def charger_citations(moitie_voulue: str | None = None, pas: int = 100):
    """Une citation sur `pas`, choisie par son empreinte : toujours les memes."""
    citations = []
    texte = telecharger_citations().read_text(encoding="utf-8")
    for ligne in texte.splitlines():
        ligne = _nettoyer(ligne)
        if not ligne or ligne.startswith("#") or "ſ" in ligne:
            continue
        empreinte = hashlib.sha1(ligne.encode("utf-8")).digest()
        if pas > 1 and int.from_bytes(empreinte[1:4], "big") % pas:
            continue
        if moitie_voulue and moitie(ligne) != moitie_voulue:
            continue
        citations.append(Juste("wiktionnaire", "citation", ligne))
    return citations


def _zone(fautif: str, obtenu: str, debut: int, fin: int):
    """La zone de `fautif` autour de [debut, fin), et ce qu'elle est devenue.

    La zone s'etend a toute retouche de Papote qui la chevauche : s'il a
    reecrit « on tant » d'un bloc, c'est le bloc qu'on compare.
    """
    blocs = difflib.SequenceMatcher(None, fautif, obtenu, autojunk=False).get_opcodes()
    change = True
    while change:
        change = False
        for etiquette, i1, i2, _, _ in blocs:
            if etiquette == "equal":
                continue
            touche = (i1 < fin and i2 > debut) or (i1 == i2 and debut <= i1 <= fin)
            if touche and (i1 < debut or i2 > fin):
                debut, fin = min(debut, i1), max(fin, i2)
                change = True

    # Ce qui est insere juste au bord de la zone en fait partie : « on » qui
    # devient « ont » est une insertion d'un « t » a sa fin.
    gauche = min([j1 + (debut - i1) for e, i1, i2, j1, _ in blocs
                  if e == "equal" and i1 <= debut <= i2]
                 + [j1 for e, i1, _, j1, _ in blocs if e != "equal" and i1 == debut]
                 + [len(obtenu)])
    droite = max([j1 + (fin - i1) for e, i1, i2, j1, _ in blocs
                  if e == "equal" and i1 <= fin <= i2]
                 + [j2 for e, _, i2, _, j2 in blocs if e != "equal" and i2 == fin]
                 + [0])
    return debut, fin, obtenu[gauche:max(gauche, droite)]


def retouche_ailleurs(faute: Faute, obtenu: str) -> bool:
    """Papote a-t-il change la phrase loin de toutes ses fautes soulignees ?"""
    places = faute.places or ((faute.debut, faute.fin),)
    blocs = difflib.SequenceMatcher(None, _apostrophes(faute.fautif),
                                    _apostrophes(obtenu), autojunk=False).get_opcodes()
    for etiquette, i1, i2, _, _ in blocs:
        if etiquette == "equal":
            continue
        if not any((i1 < f and i2 > d) or (i1 == i2 and d <= i1 <= f)
                   for d, f in places):
            return True
    return False


def juger(faute: Faute, obtenu: str) -> str:
    """« corrigee », « laissee », « ailleurs » ou « fausse », pour une faute.

    C'est ainsi que Grammalecte lit ses propres tests : a la place soulignee,
    l'une des suggestions, et rien d'autre dans la phrase (il compte comme un
    echec toute erreur qu'il trouve en plus). « ailleurs » : la faute est bien
    corrigee, mais Papote a aussi touche le reste de la phrase ; elle compte
    parmi les fautes mal corrigees, comme dans le banc LanguageTool ou la
    phrase entiere doit etre juste.
    """
    fautif, obtenu = _apostrophes(faute.fautif), _apostrophes(obtenu)
    if obtenu == fautif:
        return "laissee"
    debut, fin, devenu = _zone(fautif, obtenu, faute.debut, faute.fin)
    avant = fautif[debut:faute.debut]
    apres = fautif[faute.fin:fin]
    if devenu == fautif[debut:fin]:
        return "laissee"
    if any(devenu == avant + _apostrophes(s) + apres for s in faute.suggestions):
        return "ailleurs" if retouche_ailleurs(faute, obtenu) else "corrigee"
    return "fausse"


def _apostrophes(texte: str) -> str:
    """Grammalecte ecrit « c’est », Papote insere « c'est » : c'est la meme
    lettre, seule la typographie change (l'option « apos », ecartee)."""
    return texte.replace("’", "'")


def evaluer(correcteur, fautes, justes) -> dict:
    memoire: dict[str, str] = {}

    def corriger(phrase: str) -> str:
        if phrase not in memoire:
            memoire[phrase] = correcteur.corriger(phrase, mise_en_forme=False)[0]
        return memoire[phrase]

    corrigees, ratees, fausses, ailleurs = [], [], [], []
    for e in fautes:
        obtenu = corriger(e.fautif)
        verdict = juger(e, obtenu)
        if verdict == "ailleurs":
            ailleurs.append((e, obtenu))
            verdict = "fausse"
        {"corrigee": corrigees, "laissee": ratees, "fausse": fausses}[verdict].append((e, obtenu))
    intactes, abimees = [], []
    for e in justes:
        obtenu = corriger(e.fautif)
        intacte = _apostrophes(obtenu) == _apostrophes(e.fautif)
        (intactes if intacte else abimees).append((e, obtenu))
    return {"corrigees": corrigees, "ratees": ratees, "fausses": fausses,
            "ailleurs": ailleurs, "intactes": intactes, "abimees": abimees}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--categories", action="store_true")
    parser.add_argument("--citations", action="store_true",
                        help="mesurer aussi les citations du Wiktionnaire")
    parser.add_argument("--pas", type=int, default=100,
                        help="une citation sur PAS (1 : toutes, plusieurs heures)")
    parser.add_argument("--max", type=int, default=60)
    args = parser.parse_args()

    from papote.moteur import construire
    correcteur = construire()

    _, _, laisses = extraire()
    print(f"\n  Grammalecte {VERSION} ({COMMIT[:10]}) — tests laisses de cote :")
    for raison, n in laisses.most_common():
        print(f"    {raison:32s} {n:5d}")

    for moitie_voulue, nom in (("dev", "DEVELOPPEMENT"), ("ecart", "TENU A L'ECART")):
        fautes, justes = charger(moitie_voulue)
        r = evaluer(correcteur, fautes, justes)
        _resume(f"{nom} — tests de Grammalecte {VERSION}", r)
        print(f"      dont justes a leur place  {len(r['ailleurs']):5d}"
              f"  (mais la phrase retouchee ailleurs)")
        if args.categories:
            par = Counter(e.categorie for e in fautes)
            ok = Counter(e.categorie for e, _ in r["corrigees"])
            faux = Counter(e.categorie for e, _ in r["fausses"])
            for cat, n in par.most_common():
                print(f"      {cat:28s} {ok[cat]:4d}/{n:<5d}  mal corrigees {faux[cat]}")
        if args.detail and moitie_voulue == "dev":
            print("\n  -- phrases justes abimees --")
            for e, o in r["abimees"][:args.max]:
                print(f"   [{e.regle}] {e.fautif}\n      -> {o}")
            print("\n  -- fautes mal corrigees --")
            for e, o in r["fausses"][:args.max]:
                print(f"   [{e.regle}] {e.marquee()}\n      attendu {' | '.join(e.suggestions)}"
                      f"\n      obtenu  {o}")
            print("\n  -- fautes laissees --")
            for e, o in r["ratees"][:args.max]:
                print(f"   [{e.regle}] {e.marquee()}\n      attendu {' | '.join(e.suggestions)}")

        if args.citations:
            citations = charger_citations(moitie_voulue, args.pas)
            rc = evaluer(correcteur, [], citations)
            total, n = len(citations), len(rc["abimees"])
            print(f"\n  {nom} — citations du Wiktionnaire (une sur {args.pas})")
            print(f"    phrases justes abimees {n:4d} / {total}  ({n / max(1, total):.1%})")
            if args.detail and moitie_voulue == "dev":
                print("\n  -- citations abimees --")
                for e, o in rc["abimees"][:args.max]:
                    print(f"   {e.fautif}\n      -> {o}")


if __name__ == "__main__":
    main()
