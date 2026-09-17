# -*- coding: utf-8 -*-
"""Moteur de correction : orthographe, grammaire et garde-fous.

Le texte traverse trois couches, dans cet ordre :

0. **Vos remplacements.** Ce que vous avez appris au correcteur passe avant
   tout le reste : « ptetre » -> « peut-être », « cdlt » -> « cordialement ».
1. **Les zones intouchables.** Liens, blocs de code, mentions, emojis, argot,
   emphase volontaire : tout cela sort du circuit avant meme d'etre examine.
2. **La grammaire** (`grammaire.py`), qui regarde les mots voisins et tranche
   les homonymes : « sa va » -> « ça va », « ils on » -> « ils ont ».
3. **L'orthographe** (`lexique.py`), qui ne s'occupe que des mots absents du
   dictionnaire : « gateaux » -> « gâteaux ».

Deux principes gouvernent l'ensemble :

- On corrige les fautes, jamais le registre. « j'ai pas » est du francais
  parle correct, et aucune regle d'ici n'y touche.
- Mieux vaut sous-corriger que degrader. Une correction douteuse est ecartee :
  un message un peu fautif reste lisible, un message corrompu ne l'est plus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import grammaire, regles
from .lexique import (
    CLASSE_ACCENT, CLASSE_EDITION, CLASSE_EDITION_DOUBLE, RANG_COURANT,
    RANG_INCONNU, Lexique, sans_accents,
)
from .morphologie import Morphologie
from .politique import PARLE, SOUTENU

# Ce qui ne suit jamais une apostrophe : les formes qui la precedent
# (« se », « de », « le »...) et les abreviations que le dictionnaire connait
# pour de mauvaises raisons — « st » y figure a cause de « St. ».
RESTES_IMPOSSIBLES = {
    "st", "se", "ce", "de", "le", "la", "les", "me", "te", "ne", "je",
    "que", "des", "du", "au", "aux", "ma", "ta", "sa", "mes", "tes", "ses",
}

# Un mot colle plus court que cela ne vaut pas la peine d'etre coupe : la
# coupure y serait plus souvent une coincidence qu'une intention.
LONGUEUR_MINIMALE_COUPURE = 6

# Chaque morceau doit faire au moins deux lettres. « lavion » n'est pas
# « l avion » : c'est l'apostrophe qui manque, pas l'espace.
LONGUEUR_MINIMALE_MORCEAU = 2

# Rang au-dela duquel un morceau n'est plus assez courant pour qu'on coupe.
# Plus large que « franchement courant » : « testé » est le 5 662e mot du
# francais, et « commenttesté » doit bien se couper. Assez etroit pour que
# « github » reste entier — « hub » est le 18 097e.
RANG_MAXIMAL_MORCEAU = 9_000

# Trois lettres identiques d'affilee : « ouiiii », « mdrrrr », « nooon ».
# C'est de l'emphase volontaire, jamais une faute de frappe.
_EMPHASE = re.compile(r"(.)\1{2,}", re.IGNORECASE)

_MOTIFS_PROTEGES = re.compile(
    "|".join(regles.MOTIFS_PROTEGES), re.IGNORECASE | re.DOTALL
)

_DEBUT_DE_PHRASE = re.compile(r"(?:^|[.!?…]\s+|\n\s*)$")

_PONCTUATION_FINALE = ".!?…:;,"

# Typographie francaise, en option.
_ESPACE_INSECABLE = "\u00a0"
_SUSPENSION = re.compile(r"\.{3,}")
_GUILLEMETS = re.compile(r'"([^"\n]{1,200})"')
_AVANT_PONCTUATION = re.compile(r"[ \u00a0]*([?!;:])")


@dataclass(frozen=True)
class Correction:
    """Une modification appliquee au texte."""

    debut: int
    fin: int
    avant: str
    apres: str
    regle: str
    message: str

    def __str__(self) -> str:
        return f"{self.avant} → {self.apres}"


def _normaliser_mot(mot: str) -> str:
    """Pour comparer un mot au lexique protege."""
    return sans_accents(mot.strip(".,;:!?…\"'«»()[]{}-–—*_~")).lower()


def _zones_protegees(texte: str) -> list[tuple[int, int]]:
    """Intervalles du texte auxquels aucune correction ne doit toucher."""
    return [(m.start(), m.end()) for m in _MOTIFS_PROTEGES.finditer(texte)]


def _chevauche(debut: int, fin: int, zones: list[tuple[int, int]]) -> bool:
    return any(debut < z_fin and fin > z_debut for z_debut, z_fin in zones)


class Correcteur:
    """Corrige du francais en respectant le registre de l'auteur."""

    def __init__(self, lexique: Lexique | None = None,
                 regles_optionnelles: dict[str, bool] | None = None,
                 mots_perso: list[str] | None = None,
                 remplacements_perso: dict[str, str] | None = None,
                 registre: str = PARLE,
                 morphologie: Morphologie | None = None):
        self.lexique = lexique if lexique is not None else Lexique()
        self.morphologie = (morphologie if morphologie is not None
                            else Morphologie())
        self.registre = registre if registre in (PARLE, SOUTENU) else PARLE

        actives = dict(regles.REGLES_OPTIONNELLES)
        actives.update(regles_optionnelles or {})
        if self.registre == SOUTENU:
            # Un texte soutenu commence par une majuscule et finit par un
            # point : ce n'est plus une question de gout.
            actives["MAJUSCULE_PHRASE"] = True
            actives["PONCTUATION_POINT"] = True
        self.regles_ignorees = {nom for nom, active in actives.items() if not active}

        self.mots_proteges = set(regles.LEXIQUE_PROTEGE) | set(regles.LEXIQUE_ANGLAIS)
        for mot in mots_perso or []:
            self.mots_proteges.add(_normaliser_mot(mot))

        # Les cles sont comparees en minuscules et sans apostrophe typographique,
        # pour que « Ptetre » et « ptetre » trouvent la meme entree.
        remplacements = dict(regles.ABREVIATIONS_SOUTENUES) \
            if self.registre == SOUTENU else {}
        # Les remplacements de l'utilisateur passent avant les notres.
        remplacements.update({
            cle: valeur for cle, valeur in (remplacements_perso or {}).items()
            if cle.strip() and valeur.strip()
        })
        self.remplacements = {
            cle.lower().replace("\u2019", "'"): valeur
            for cle, valeur in remplacements.items()
        }

    def prechauffer(self) -> None:
        """Lit les fichiers de donnees maintenant plutot qu'a la 1re correction."""
        self.lexique.charger()
        self.morphologie.charger()

    # -- protection ---------------------------------------------------------

    def _protege(self, mot: str) -> bool:
        """Ce mot doit-il rester tel quel, quoi qu'il arrive ?"""
        if _EMPHASE.search(mot):
            return True
        if _normaliser_mot(mot) in self.mots_proteges:
            return True
        # Sigles et emphase en capitales : « SNCF », « NON ».
        return len(mot) > 1 and mot.isupper()

    # -- orthographe --------------------------------------------------------

    def _connu(self, mot: str) -> bool:
        if self.lexique.connait(mot):
            return True
        # « j'ai », « qu'il » : l'elision se verifie a part.
        elision, noyau = grammaire.separer_clitique(mot)
        if elision:
            return not noyau or self.lexique.connait(noyau)
        return False

    def _apostrophe_manquante(self, mot: str) -> str | None:
        """« jai » -> « j'ai », « cest » -> « c'est », « daccord » -> « d'accord ».

        L'apostrophe est la touche la plus souvent sautee en tapant vite. Le
        mot colle n'existe jamais dans le dictionnaire, ce qui rend la
        correction sure : il suffit que la coupure donne deux morceaux
        connus.
        """
        for elision in grammaire.CLITIQUES:
            tete = elision.rstrip("'")
            if not mot.lower().startswith(tete) or len(mot) <= len(tete):
                continue
            reste = mot[len(tete):]
            # « ca » ne doit pas devenir « c'a » : il faut un vrai mot derriere.
            # « ny » fait exception — « n'y » est trop courant pour le manquer.
            if len(reste) < 2 and reste != "y":
                continue
            # Ces mots-la ne suivent jamais une apostrophe : ce sont
            # eux-memes des elisions, ou des abreviations. Sans cette liste,
            # « dse » devenait « d'se » et « cst » devenait « c'st ».
            if reste in RESTES_IMPOSSIBLES:
                continue
            # Le morceau de droite doit etre un mot **courant**, pas
            # seulement un mot du dictionnaire : « ab » y figure (9 539e), et
            # « tab » devenait « t'ab ». « ny » -> « n'y » fait exception,
            # « y » n'etant pas dans la liste de frequences.
            if self.lexique.connait(reste) and (
                    reste == "y" or self.lexique.rang(reste) <= RANG_COURANT):
                return mot[: len(tete)] + "'" + reste
            # « cetait » -> « c'était » : le morceau de droite a le droit
            # d'avoir perdu ses accents.
            accentue = self.lexique.suggestion(reste, classe_max=CLASSE_ACCENT)
            if accentue is not None:
                return mot[: len(tete)] + "'" + accentue

            # « jesper » -> « j'espère » : il a aussi le droit d'avoir une
            # faute de frappe, mais alors le mot obtenu doit etre franchement
            # courant — sans quoi « subject » deviendrait « s'abject ».
            #
            # Et seulement si le mot entier n'a aucune graphie accentuee.
            # « decolle » en a deux, « décolle » et « décollé » : le
            # correcteur hesite et se tait, ce qui est juste. Laisser
            # l'apostrophe passer derriere en faisait « d'école ».
            if self.lexique.formes(mot.lower()):
                continue
            # Ni si une simple lettre suffit a reparer le mot. « menbre »
            # est « membre » — une lettre — et devenait « m'entre », une
            # apostrophe *et* une lettre. Le moins d'inventions possible.
            if self.lexique.suggestion(mot.lower(),
                                       classe_max=CLASSE_EDITION) is not None:
                return None
            frappe = self.lexique.suggestion(reste, classe_max=CLASSE_EDITION)
            if frappe is not None and self.lexique.rang(frappe) <= RANG_COURANT:
                return mot[: len(tete)] + "'" + frappe
        return None

    def _orthographe(self, mot: str, profond: bool = True,
                     precedent: str = "") -> str | None:
        """Le mot correctement orthographie, s'il ne fait aucun doute.

        `profond` autorise la recherche a deux frappes d'ecart, qui rattrape
        « jorunée » ou « bonjoru » mais coute jusqu'a deux dixiemes de seconde
        sur un mot inconnu. On la reserve aux corrections demandees : sous les
        doigts, une pause pareille se sentirait.
        """
        if len(mot) < 2:
            # Une lettre isolee est une abreviation (« c pas grave »), pas un
            # mot a corriger.
            return None

        elision, noyau = grammaire.separer_clitique(mot)

        # Un mot capitalise au milieu d'une phrase est un nom propre : on veut
        # bien lui rendre ses accents, pas le remplacer par un autre mot.
        prudent = mot[:1].isupper()

        # Ordre de confiance : les accents oublies d'abord, l'apostrophe
        # oubliee ensuite, la faute de frappe en dernier. « cest » deviendrait
        # « est » si on laissait la distance d'edition passer la premiere.
        accents = self.lexique.suggestion(noyau, classe_max=CLASSE_ACCENT)
        if accents is not None:
            return elision + accents

        if not elision:
            apostrophe = self._apostrophe_manquante(mot)
            if apostrophe is not None:
                return apostrophe

        if prudent:
            return None

        # L'espace sautee vient avant la faute de frappe. « ilfaut » doit
        # devenir « il faut », et non « faut » — ce que la distance d'edition
        # proposait, en escamotant un mot au passage.
        if not elision:
            coupure = self._espace_manquante(mot)
            if coupure is not None:
                return coupure

        # Le determinant qui precede reduit le champ des possibles. Apres
        # « les », un adverbe n'a rien a faire : « les délay » ne peut pas
        # etre « les delà », et « délai » — qu'aucune marge de frequence ne
        # departageait — devient le seul candidat.
        if precedent in grammaire.DETERMINANTS_PLURIELS or precedent == "les":
            pluriel = self._accorder_au_pluriel(noyau)
            if pluriel is not None:
                return elision + pluriel

        # La majuscule d'un nom propre passe avant le garde-fou des
        # frequences : « france » y figure — la liste est en minuscules —
        # alors que le nom commun, lui, n'existe pas.
        majuscule = self.lexique.majuscule_obligatoire(noyau)
        if majuscule is not None:
            return elision + majuscule

        # Un mot que le dictionnaire ignore mais que la liste de frequences
        # connait est un mot que des gens ecrivent : une abreviation
        # (« perm »), une marque (« chanel »), un mot anglais passe dans
        # l'usage (« cool », « mail »). Ce n'est pas une faute de frappe, et
        # « perm » ne doit pas devenir « père ».
        #
        # La separation est nette : aucune des fautes de frappe du corpus n'y
        # figure, et tous ces mots-la y sont. La fenetre continue de les
        # proposer ; c'est la correction automatique qui s'abstient.
        if self.lexique.rang(noyau) != RANG_INCONNU:
            return None

        frappe = self.lexique.suggestion(
            noyau,
            classe_max=CLASSE_EDITION_DOUBLE if profond else CLASSE_EDITION,
        )
        return elision + frappe if frappe is not None else None

    def _accorder_au_pluriel(self, mot: str) -> str | None:
        """La correction de `mot`, mise au pluriel, quand un déterminant
        pluriel la precede.

        Deux choses a la fois, et c'est ce qui la rend sure. D'abord le
        contexte **ecarte** des candidats : apres « les », seul un mot qui a
        un pluriel est recevable. « délay » hesitait entre « delà » (1 183e)
        et « délai » (2 638e) — trop proches pour trancher, donc le
        correcteur se taisait. Mais « delà » n'a pas de pluriel : il ne reste
        qu'un candidat, et le doute disparait.

        Ensuite le contexte **accorde** : ce n'est pas « délai » qu'il faut
        ecrire apres « les », c'est « délais ».
        """
        recevables = []
        for candidat in self.lexique.candidats(mot):
            if candidat.rang == RANG_INCONNU or candidat.classe > CLASSE_EDITION:
                continue
            # Le pluriel se lit dans le dictionnaire : « bijou » fait
            # « bijoux », « pneu » fait « pneus », et aucune terminaison ne
            # distingue les deux.
            pluriel = self.morphologie.au_pluriel(candidat.mot)
            if pluriel is not None:
                recevables.append((candidat.rang, pluriel))
                continue
            for pluriel in (candidat.mot + "s", candidat.mot + "x",
                            candidat.mot):
                if self.lexique.connait(pluriel) and pluriel != candidat.mot:
                    recevables.append((candidat.rang, pluriel))
                    break

        if len(recevables) != 1:
            # Zero : le contexte n'a rien sauve. Plusieurs : il n'a pas
            # tranche, et ce n'est pas a lui de le faire au hasard.
            return None
        rang, pluriel = recevables[0]
        return pluriel if rang <= RANG_COURANT * 2 else None

    def _espace_manquante(self, mot: str) -> str | None:
        """« ilfaut » -> « il faut », « commenttesté » -> « comment testé ».

        L'espace est la touche la plus large du clavier, et la plus souvent
        manquee quand on tape vite. Le mot colle n'existe jamais au
        dictionnaire, ce qui rend la coupure sure — a trois conditions, sans
        lesquelles « github » deviendrait « git hub » et « facebook »
        « face book » :

        1. les deux morceaux doivent etre **courants**, pas seulement connus.
           « hub » est au dictionnaire, 18 000e ; cela ne suffit pas ;
        2. aucun des deux ne doit etre une lettre isolee. « lavion » ne
           devient pas « l avion » — c'est le travail de l'apostrophe ;
        3. le mot colle doit etre assez long pour que la coupure veuille dire
           quelque chose.

        Entre plusieurs coupures possibles, on garde celle dont le morceau le
        moins courant l'est encore le plus : c'est la plus probable.
        """
        if len(mot) < LONGUEUR_MINIMALE_COUPURE:
            return None

        minuscule = mot.lower()
        if self._un_seul_mot_plus_probable(minuscule):
            return None
        # Le mot existe, a ses accents pres : « decolle » est « décolle » ou
        # « décollé », et le correcteur se tait faute de savoir lequel. Cette
        # hesitation dit que le mot en est un — pas qu'il en cache deux.
        # Sans cela, « l'avion decolle » devenait « l'avion de colle ».
        if self.lexique.formes(minuscule):
            return None

        meilleures = []
        for i in range(LONGUEUR_MINIMALE_MORCEAU,
                       len(mot) - LONGUEUR_MINIMALE_MORCEAU + 1):
            gauche, droite = minuscule[:i], minuscule[i:]
            if not (self.lexique.connait(gauche)
                    and self.lexique.connait(droite)):
                continue
            rangs = (self.lexique.rang(gauche), self.lexique.rang(droite))
            if max(rangs) > RANG_MAXIMAL_MORCEAU:
                continue
            if self.lexique.connait(f"{gauche}-{droite}"):
                # « microonde » n'est pas « micro onde » : c'est
                # « micro-onde », a qui il manque un trait d'union. Ce que le
                # dictionnaire connait sous cette forme-la n'est pas deux
                # mots, et une espace n'y ferait pas l'affaire.
                continue
            meilleures.append((max(rangs), i))

        if not meilleures:
            return None
        _rang, coupure = min(meilleures)
        return mot[:coupure] + " " + mot[coupure:]

    def _un_seul_mot_plus_probable(self, minuscule: str) -> bool:
        """Le mot cache-t-il une lettre manquante plutot qu'une espace ?

        « platforme » se coupe en « plat » et « forme », deux mots courants —
        et c'est « plateforme » a qui il manque un « e ». Pareil pour
        « gestionaire », qui donnait « gestion aire ». Couper la, c'est
        inventer une phrase a la place de celle qu'on ecrivait.

        Ce qui tranche, c'est le **sens** de l'edition. Une espace sautee est
        une omission : si le mot n'en est vraiment qu'un, la reparation
        **ajoute** une lettre — la consonne doublee de « gestionnaire », le
        « e » de « plateforme ». Elle n'en retire pas, et elle n'en echange
        pas : le candidat doit donc etre strictement plus long que ce qui a
        ete tape.

        Les deux autres cas montrent pourquoi la condition est si etroite.
        Une lettre retiree : « apriori » donnerait « priori » au lieu de
        « a priori ». Une lettre echangee : « jevais » donnerait « devais »
        au lieu de « je vais ». Dans les deux cas, la coupure a raison.
        """
        candidat = self.lexique.suggestion(minuscule,
                                           classe_max=CLASSE_EDITION)
        return candidat is not None and len(candidat) > len(minuscule)

    def propositions(self, mot: str, maximum: int = 4) -> list[str]:
        """Les remplacements plausibles d'un mot inconnu, faute de certitude.

        Le correcteur ne remplace que ce dont il est sur. Quand il hesite —
        « ourné » vaut « journée » autant que « durée » — il vaut mieux
        montrer la courte liste que laisser la faute en place.
        """
        elision, noyau = grammaire.separer_clitique(mot)
        return [elision + p for p in self.lexique.propositions(noyau, maximum)]

    # -- une passe ----------------------------------------------------------

    def _passe(self, texte: str, profond: bool = True) -> tuple[str, list[Correction]]:
        jetons = grammaire.decouper(texte)
        zones = _zones_protegees(texte)
        propositions: list[Correction] = []
        traites: set[int] = set()

        def utilisable(indices: range, debut: int, fin: int,
                       regle: str = "") -> bool:
            if _chevauche(debut, fin, zones):
                return False
            if regle in regles.REGLES_SUR_MOTS_PROTEGES:
                # La protection empeche le correcteur de **deviner** sur un
                # mot qu'il ne connait pas. Une regle qui nomme le mot
                # compose en entier ne devine rien : sans cette exception,
                # « week end » restait tel quel parce que « end » est un mot
                # anglais protege.
                return True
            return not any(self._protege(jetons[i].texte) for i in indices)

        # -- vos remplacements : ils passent avant tout, y compris avant les
        #    protections, puisque c'est vous qui les avez demandes.
        if self.remplacements:
            for i, jeton in enumerate(jetons):
                if _chevauche(jeton.debut, jeton.fin, zones):
                    continue
                remplacement = self.remplacements.get(
                    jeton.texte.lower().replace("\u2019", "'")
                )
                if remplacement is None or remplacement == jeton.texte:
                    continue
                propositions.append(
                    Correction(jeton.debut, jeton.fin, jeton.texte,
                               grammaire.appliquer_casse(jeton.texte, remplacement),
                               "REMPLACEMENT_PERSO",
                               "remplacement enregistre dans votre dictionnaire")
                )
                traites.add(i)

        # -- grammaire : elle voit le contexte, elle passe en premier.
        for suggestion in grammaire.analyser(
            texte, jetons, self.lexique, self.regles_ignorees, self.registre,
            self.morphologie,
        ):
            indices = range(suggestion.index, suggestion.index + suggestion.portee)
            if traites.intersection(indices):
                continue
            debut = jetons[suggestion.index].debut
            fin = jetons[indices[-1]].fin
            if not utilisable(indices, debut, fin, suggestion.regle):
                continue
            propositions.append(
                Correction(debut, fin, texte[debut:fin], suggestion.texte,
                           suggestion.regle, suggestion.message)
            )
            traites.update(indices)

        # -- orthographe : uniquement les mots qu'aucun dictionnaire ne connait.
        for i, jeton in enumerate(jetons):
            if i in traites or not utilisable(range(i, i + 1), jeton.debut, jeton.fin):
                continue
            if self._connu(jeton.texte):
                continue
            remplacement = self._orthographe(
                jeton.texte, profond, precedent=jetons[i - 1].texte.lower()
                if i else "")
            if remplacement is None or remplacement == jeton.texte:
                continue
            propositions.append(
                Correction(jeton.debut, jeton.fin, jeton.texte, remplacement,
                           "ORTHOGRAPHE", "mot absent du dictionnaire")
            )

        return self._appliquer(texte, propositions)

    @staticmethod
    def _appliquer(texte: str, propositions: list[Correction]):
        """Reecrit le texte de la fin vers le debut, pour ne pas decaler les offsets."""
        propositions.sort(key=lambda c: c.debut, reverse=True)
        appliquees: list[Correction] = []
        derniere_position = len(texte) + 1

        for proposition in propositions:
            if proposition.fin > derniere_position:
                continue
            texte = texte[:proposition.debut] + proposition.apres + texte[proposition.fin:]
            appliquees.append(proposition)
            derniere_position = proposition.debut

        appliquees.reverse()
        return texte, appliquees

    # -- regles optionnelles de mise en forme --------------------------------

    def _mise_en_forme(self, texte: str) -> tuple[str, list[Correction]]:
        corrections: list[Correction] = []

        if "MAJUSCULE_PHRASE" not in self.regles_ignorees:
            for jeton in reversed(grammaire.decouper(texte)):
                premiere = jeton.texte[:1]
                if not premiere.islower():
                    continue
                if not _DEBUT_DE_PHRASE.search(texte[:jeton.debut]):
                    continue
                corrections.append(
                    Correction(jeton.debut, jeton.debut + 1, premiere,
                               premiere.upper(), "MAJUSCULE_PHRASE",
                               "majuscule en debut de phrase")
                )
                texte = texte[:jeton.debut] + premiere.upper() + texte[jeton.debut + 1:]

        if "TYPOGRAPHIE" not in self.regles_ignorees:
            texte, typographiques = self._typographie(texte)
            corrections.extend(typographiques)

        if "PONCTUATION_POINT" not in self.regles_ignorees:
            corps = texte.rstrip()
            if corps and corps[-1] not in _PONCTUATION_FINALE:
                position = len(corps)
                corrections.append(
                    Correction(position, position, "", ".", "PONCTUATION_POINT",
                               "point final manquant")
                )
                texte = corps + "." + texte[position:]

        corrections.reverse()
        return texte, corrections

    def _typographie(self, texte: str) -> tuple[str, list[Correction]]:
        """Points de suspension, guillemets francais, espaces insecables.

        Les liens et les blocs de code sont laisses de cote : une espace
        insecable glissee dans une URL la casse.
        """
        corrections: list[Correction] = []
        zones = _zones_protegees(texte)

        def transformer(morceau: str) -> str:
            nouveau = _SUSPENSION.sub("…", morceau)
            if nouveau != morceau:
                corrections.append(Correction(0, 0, "...", "…", "TYPOGRAPHIE",
                                              "points de suspension"))
            morceau, nouveau = nouveau, _GUILLEMETS.sub(
                lambda m: f"«{_ESPACE_INSECABLE}{m.group(1).strip()}"
                          f"{_ESPACE_INSECABLE}»", nouveau)
            if nouveau != morceau:
                corrections.append(Correction(0, 0, '"', "« »", "TYPOGRAPHIE",
                                              "guillemets français"))
            morceau, nouveau = nouveau, _AVANT_PONCTUATION.sub(
                lambda m: _ESPACE_INSECABLE + m.group(1), nouveau)
            if nouveau != morceau:
                corrections.append(Correction(0, 0, "?", f"{_ESPACE_INSECABLE}?",
                                              "TYPOGRAPHIE", "espace insécable"))
            return nouveau

        morceaux, position = [], 0
        for debut, fin in sorted(zones):
            if debut < position:
                continue
            morceaux.append(transformer(texte[position:debut]))
            morceaux.append(texte[debut:fin])
            position = fin
        morceaux.append(transformer(texte[position:]))

        return "".join(morceaux), corrections

    # -- entree publique ----------------------------------------------------

    def corriger(self, texte: str, passes: int = 2,
                 mise_en_forme: bool = True,
                 profond: bool = True) -> tuple[str, list[Correction]]:
        """Corrige `texte` et renvoie (texte_corrige, corrections_appliquees).

        Deux passes par defaut : corriger « ils on manger » en « ils ont
        manger » debloque la regle du participe, que la premiere passe ne
        pouvait pas voir.

        `mise_en_forme` couvre la majuscule de debut de phrase et le point
        final. La correction au fil de la frappe la desactive : une phrase en
        cours d'ecriture n'est pas encore finie, et lui coller un point a
        chaque espace serait insupportable.

        `profond` autorise la recherche a deux frappes d'ecart. La frappe la
        desactive egalement : elle coute trop cher pour une touche.
        """
        if not texte or not texte.strip():
            return texte, []

        # Les espaces de bord comptent au collage : on les met de cote et on
        # les restitue tels quels.
        marge_gauche = texte[: len(texte) - len(texte.lstrip())]
        marge_droite = texte[len(texte.rstrip()):]
        corps = texte.strip()

        toutes: list[Correction] = []
        for _ in range(max(1, passes)):
            corps, corrections = self._passe(corps, profond)
            if not corrections:
                break
            toutes.extend(corrections)

        if mise_en_forme:
            corps, corrections = self._mise_en_forme(corps)
            toutes.extend(corrections)

        return marge_gauche + corps + marge_droite, toutes


def construire(regles_optionnelles: dict[str, bool] | None = None,
               mots_perso: list[str] | None = None,
               remplacements_perso: dict[str, str] | None = None,
               registre: str = PARLE) -> Correcteur:
    """Le correcteur pret a l'emploi, dictionnaire compris."""
    return Correcteur(Lexique(), regles_optionnelles, mots_perso,
                      remplacements_perso, registre)


def depuis_config(config: dict, lexique: Lexique | None = None,
                  registre: str | None = None,
                  morphologie: Morphologie | None = None) -> Correcteur:
    """Le correcteur decrit par un fichier de reglages.

    `lexique` et `morphologie` se passent de l'exterieur pour que les deux
    registres partagent les memes tables : elles pesent quelques dizaines de
    megaoctets, et les charger deux fois n'apporterait rien.
    """
    return Correcteur(
        lexique if lexique is not None else Lexique(),
        regles_optionnelles=config.get("regles_optionnelles"),
        mots_perso=config.get("mots_perso"),
        remplacements_perso=config.get("remplacements_perso"),
        registre=registre if registre is not None
        else config.get("registre", PARLE),
        morphologie=morphologie,
    )
