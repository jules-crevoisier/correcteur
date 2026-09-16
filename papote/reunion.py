# -*- coding: utf-8 -*-
"""Tirer un compte rendu d'une reunion transcrite.

Une heure de reunion, c'est huit mille mots. Personne ne les relit. Ce qu'on
cherche apres coup tient en trois listes : **ce qui a ete decide**, **ce que
chacun doit faire**, et **ce qui reste en suspens**.

Ces trois choses ne se devinent pas — elles s'annoncent. Le francais parle a
des tournures pour cela, et elles sont peu nombreuses :

    on part sur la deuxieme option      une decision
    je m'occupe de relancer le client   une action, et qui la prend
    d'ici vendredi                      une echeance
    est-ce qu'on a le budget ?          une question, restee sans reponse

Ce module les reconnait, et **rien de plus**. Il ne comprend pas la reunion :
il repere des formules et rend ce qu'il a trouve, en citant la phrase entiere
pour qu'on puisse verifier d'un coup d'oeil. Un compte rendu qui se trompe et
qu'on peut corriger vaut mieux qu'un resume qui invente et qu'on croit.

C'est aussi pourquoi tout est rendu **en plus** de la transcription complete,
jamais a la place : ce qui n'a pas ete repere n'est pas perdu.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _nu(texte: str) -> str:
    """Le texte sans accents ni majuscules, pour comparer des formules."""
    decompose = unicodedata.normalize("NFD", texte.lower())
    sans = "".join(c for c in decompose if unicodedata.category(c) != "Mn")
    return sans.replace("’", "'")


# ---------------------------------------------------------------------------
# Ce qui s'annonce
# ---------------------------------------------------------------------------

# Une decision. Ces formules referment un debat ; elles ne s'emploient pas
# autrement.
DECISIONS = (
    "on part sur", "on part la-dessus", "on valide", "c'est valide",
    "on decide", "on a decide", "c'est decide", "on retient", "on garde",
    "on choisit", "c'est acte", "on acte", "c'est adopte", "on adopte",
    "on fait comme ca", "on reste sur", "on opte pour", "va pour",
    "c'est ok pour", "on se met d'accord sur", "on est d'accord pour",
    "on abandonne", "on laisse tomber", "on annule", "on reporte",
)

# Une action, quand celui qui parle la prend lui-meme.
ENGAGEMENTS = (
    # Les elisions comptent : « je m'occupe du dossier » est un engagement
    # autant que « je m'occupe de relancer ».
    "je m'occupe de", "je m'occupe du", "je m'occupe d'", "je m'en occupe",
    "je prends", "je me charge de", "je me charge du", "je me charge d'",
    "je vais faire", "je vais m'occuper", "je fais", "je m'y mets",
    "je te l'envoie", "je vous l'envoie", "je l'envoie", "je relance",
    "je prepare", "je redige", "je regarde", "je verifie", "je contacte",
    "je reviens vers", "c'est moi qui",
)

# Une action confiee a quelqu'un d'autre. On ne devine pas a qui : la
# personne se nomme dans la phrase, ou l'action reste a attribuer.
DEMANDES = (
    "il faut que", "il faut qu'", "faut que", "faut qu'",
    "il faudrait que", "il faudrait qu'", "faudrait que", "faudrait qu'",
    "tu peux", "vous pouvez", "tu pourrais", "vous pourriez",
    "tu t'occupes", "vous vous occupez", "il faudra", "on doit",
    "n'oublie pas de", "n'oubliez pas de", "pense a", "pensez a",
    "merci de", "peux-tu", "pouvez-vous",
)

# Ce qui ouvre un nouveau sujet. Sans ces reperes, un compte rendu d'une
# heure est un seul bloc.
TRANSITIONS = (
    "on passe a", "point suivant", "sujet suivant", "deuxieme point",
    "troisieme point", "dernier point", "premier point", "ensuite",
    "concernant", "au sujet de", "pour ce qui est de", "sur le sujet de",
    "autre chose", "autre sujet", "prochain point", "on enchaine sur",
    "parlons de", "venons-en a",
)

# Les echeances. Le jour de la semaine seul suffit : dans une reunion, « on
# se voit jeudi » ne parle pas d'un jeudi quelconque.
_JOURS = "lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche"
_MOIS = ("janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre"
         "|octobre|novembre|decembre")
ECHEANCES = re.compile(
    r"\b(?:"
    rf"(?:avant|apres|d'ici|pour|des|le|jusqu'a)\s+(?:{_JOURS})"
    rf"|(?:{_JOURS})(?:\s+(?:prochain|matin|apres-midi|soir))?"
    rf"|\d{{1,2}}\s+(?:{_MOIS})"
    r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
    r"|aujourd'hui|demain|apres-demain|ce soir|ce matin"
    r"|(?:la\s+)?semaine prochaine|(?:le\s+)?mois prochain"
    r"|fin de semaine|fin du mois|en fin de journee"
    r"|d'ici (?:la fin|une semaine|deux semaines|un mois)"
    r")\b"
)


@dataclass(frozen=True)
class Releve:
    """Une chose reperee, et la phrase entiere d'ou elle sort.

    La phrase est la pour qu'on puisse verifier : c'est ce qui distingue un
    compte rendu d'un resume qu'il faut croire sur parole.
    """

    espece: str          # « décision », « action », « question »
    qui: str
    quoi: str
    quand: str = ""
    instant: float = 0.0


def _phrases(texte: str) -> list[str]:
    """Decoupe un tour de parole en phrases, ponctuation comprise."""
    morceaux = re.split(r"(?<=[.!?…])\s+", texte)
    return [m.strip() for m in morceaux if m.strip()]


def _echeance(phrase: str) -> str:
    trouve = ECHEANCES.search(_nu(phrase))
    return trouve.group(0) if trouve else ""


def _contient(phrase_nue: str, formules) -> str:
    """La premiere formule presente, ou une chaine vide."""
    for formule in formules:
        if formule in phrase_nue:
            return formule
    return ""


def relever(tours) -> list[Releve]:
    """Tout ce que les tours de parole annoncent d'eux-memes."""
    releves: list[Releve] = []
    for tour in tours:
        for phrase in _phrases(tour.texte):
            nue = _nu(phrase)
            quand = _echeance(phrase)

            if _contient(nue, DECISIONS):
                releves.append(Releve("décision", tour.locuteur, phrase,
                                      quand, tour.debut))
                continue
            if _contient(nue, ENGAGEMENTS):
                releves.append(Releve("action", tour.locuteur, phrase,
                                      quand, tour.debut))
                continue
            if _contient(nue, DEMANDES):
                releves.append(Releve("action", _destinataire(phrase, tour),
                                      phrase, quand, tour.debut))
                continue
            if phrase.rstrip().endswith("?"):
                releves.append(Releve("question", tour.locuteur, phrase,
                                      quand, tour.debut))
    return releves


def _destinataire(phrase: str, tour) -> str:
    """A qui l'action est confiee, quand la phrase le dit.

    « il faut que Marion relance » nomme sa personne ; « il faut qu'on
    relance » n'en nomme aucune, et l'action reste a attribuer. On ne
    devine pas : une action attribuee au hasard est pire qu'une action sans
    responsable, parce que personne ne la reprend.
    """
    apres = re.search(r"\b(?:que|qu')\s+([A-ZÉÈÀÎÔÛ]\w+)", phrase)
    if apres:
        return apres.group(1)
    return "à attribuer"


# ---------------------------------------------------------------------------
# Les sujets
# ---------------------------------------------------------------------------

@dataclass
class Sujet:
    """Un morceau de reunion, entre deux transitions."""

    titre: str
    debut: float
    tours: list


def decouper_en_sujets(tours) -> list[Sujet]:
    """Suit les annonces de changement de sujet.

    Quand la reunion n'en fait aucune — et beaucoup n'en font pas — tout
    tient dans un seul bloc, et c'est la reponse honnete.
    """
    sujets: list[Sujet] = []
    for tour in tours:
        titre = _titre_de_transition(tour.texte)
        if titre or not sujets:
            sujets.append(Sujet(titre or "", tour.debut, []))
        sujets[-1].tours.append(tour)
    return sujets


def _titre_de_transition(texte: str) -> str:
    """Ce qui suit « on passe a », en quelques mots."""
    nue = _nu(texte)
    for formule in TRANSITIONS:
        place = nue.find(formule)
        if place == -1:
            continue
        suite = texte[place + len(formule):].strip(" ,:'")
        suite = re.split(r"[.!?…]", suite)[0].strip()
        mots = suite.split()
        if not mots:
            continue
        titre = " ".join(mots[:7])
        return titre[:1].upper() + titre[1:]
    return ""


# ---------------------------------------------------------------------------
# Le rendu
# ---------------------------------------------------------------------------

def _duree_lisible(secondes: float) -> str:
    minutes = int(secondes // 60)
    if not minutes:
        return f"{int(secondes)} s"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d}"


def compte_rendu(transcription, titre: str = "Compte rendu",
                 date: str = "") -> str:
    """Le compte rendu, en Markdown.

    L'ordre suit ce qu'on cherche en le rouvrant : d'abord ce qui engage
    (decisions, actions), ensuite ce qui reste ouvert, et la transcription
    entiere en dernier — elle sert a verifier, pas a lire.
    """
    tours = transcription.tours
    releves = relever(tours)
    lignes = [f"# {titre}", ""]

    entete = []
    if date:
        entete.append(f"**Date** : {date}")
    if transcription.duree:
        entete.append(f"**Durée** : {_duree_lisible(transcription.duree)}")
    participants = transcription.participants
    if participants:
        entete.append(f"**Participants** : {', '.join(participants)}")
    if entete:
        lignes += entete + [""]

    if not tours:
        lignes.append("_Rien n'a été enregistré._")
        return "\n".join(lignes)

    decisions = [r for r in releves if r.espece == "décision"]
    actions = [r for r in releves if r.espece == "action"]
    questions = [r for r in releves if r.espece == "question"]

    if decisions:
        lignes += ["## Décisions", ""]
        for releve in decisions:
            lignes.append(f"- {releve.quoi}  \n  _{releve.qui}_")
        lignes.append("")

    if actions:
        lignes += ["## Actions", ""]
        lignes.append("| Qui | Quoi | Quand |")
        lignes.append("|---|---|---|")
        for releve in actions:
            quoi = releve.quoi.replace("|", "\\|")
            lignes.append(f"| {releve.qui} | {quoi} | {releve.quand or '—'} |")
        lignes.append("")

    if questions:
        lignes += ["## Questions restées ouvertes", ""]
        for releve in questions:
            lignes.append(f"- {releve.quoi} _({releve.qui})_")
        lignes.append("")

    sujets = decouper_en_sujets(tours)
    if len(sujets) > 1:
        lignes += ["## Sujets abordés", ""]
        for rang, sujet in enumerate(sujets, 1):
            titre_sujet = sujet.titre or "Ouverture"
            lignes.append(f"{rang}. **{titre_sujet}** "
                          f"— {_horodatage(sujet.debut)}")
        lignes.append("")

    lignes += ["## Transcription", ""]
    for tour in tours:
        lignes.append(f"**{tour.locuteur}** _({_horodatage(tour.debut)})_  ")
        lignes.append(tour.texte)
        lignes.append("")

    if not (decisions or actions or questions):
        lignes.insert(len(entete) + 3,
                      "_Aucune décision ni action n'a été repérée : la "
                      "transcription complète est ci-dessous._\n")

    return "\n".join(lignes).rstrip() + "\n"


def _horodatage(secondes: float) -> str:
    return f"{int(secondes // 60):02d}:{int(secondes % 60):02d}"
