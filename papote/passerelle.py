# -*- coding: utf-8 -*-
"""Ce que la fenetre sait faire, sans rien savoir de son apparence.

La fenetre de Papote est une page web rendue par le moteur d'Edge. Le
JavaScript ne connait de Python que cet objet : il appelle des methodes, il
recoit des dictionnaires, et c'est tout. Aucune methode d'ici ne sait ce
qu'est un bouton.

Cette separation n'est pas une elegance : c'est ce qui rend la fenetre
testable. Un test ouvre une `Passerelle` sur une configuration jetable et
verifie qu'ajouter un mot l'enregistre bien — sans ecran, sans navigateur,
et sans les trois cents lignes de doublure qu'exigeait tkinter.

Trois regles tenues partout ici :

1. toute methode rend un dictionnaire serialisable en JSON. Jamais un objet
   du moteur, qui ne traverserait pas le pont ;
2. aucune ne leve. Une erreur revient dans la reponse, sous « erreur », et
   la page l'affiche. Une exception qui traverse le pont laisse la fenetre
   muette, sans rien dire a personne ;
3. les methodes lentes — corriger un long texte, interroger GitHub — sont
   appelees depuis un fil cote JavaScript. Ici, on ne s'en occupe pas.
"""

from __future__ import annotations

import re

from . import __version__, config as config_mod
from . import demarrage, grammaire, journal as journal_mod, logo, maj, regles
from .lexique import LexiqueIntrouvable
from .politique import PARLE, REGISTRES, SOUTENU

# Les pages, dans l'ordre de la colonne. Le JavaScript se contente de les
# afficher : ajouter une page ici la fait apparaitre, sans toucher au HTML.
PAGES = (
    {"cle": "corriger", "nom": "Corriger", "icone": "crayon",
     "soustitre": "Collez un texte, relisez-le avant de l'envoyer."},
    {"cle": "dictionnaire", "nom": "Mon dictionnaire", "icone": "livre",
     "soustitre": "Les mots et les tournures qui vous appartiennent."},
    {"cle": "fautes", "nom": "Vos fautes", "icone": "barres",
     "soustitre": "Ce que vous corrigez le plus, compté chez vous."},
    {"cle": "applications", "nom": "Applications", "icone": "fenetre",
     "soustitre": "Où se taire, et où hausser le ton."},
    {"cle": "reglages", "nom": "Réglages", "icone": "reglages",
     "soustitre": "Tout ce qui se réglait dans un fichier."},
)

# Les interrupteurs de la page « Reglages », dans l'ordre d'affichage. Les
# tenir ici plutot que dans le HTML evite qu'un libelle et son reglage se
# separent le jour ou l'un des deux bouge.
INTERRUPTEURS = (
    {"cle": "correction_auto", "libelle": "Corriger pendant que j'écris",
     "explication": "Le texte se corrige tout seul, sans rien demander."},
    {"cle": "collage_auto", "libelle": "Recoller le texte corrigé",
     "explication": "Après le raccourci, remet le texte à la place de la "
                    "sélection."},
    {"cle": "apprentissage", "libelle": "Retenir mes habitudes",
     "explication": "Trois annulations sur le même mot, et Papote n'y "
                    "touche plus."},
    {"cle": "notifications", "libelle": "Afficher les notifications",
     "explication": "Un résumé des corrections appliquées, près de "
                    "l'horloge."},
    {"cle": "verifier_maj", "libelle": "Chercher les nouvelles versions",
     "explication": "Téléchargées en arrière-plan, installées au "
                    "redémarrage."},
)

RACCOURCIS = (
    {"cle": "raccourci", "libelle": "Corriger la sélection"},
    {"cle": "raccourci_relecture", "libelle": "Relire la sélection"},
    {"cle": "raccourci_annuler", "libelle": "Annuler la dernière correction"},
    {"cle": "raccourci_fenetre", "libelle": "Ouvrir cette fenêtre"},
)

# Nombre de mots inconnus pour lesquels on cherche des remplacements. Au-dela,
# la page devient un mur et la recherche se fait sentir.
INCONNUS_MONTRES = 12


def _normaliser_mot(mot: str) -> str:
    return mot.lower().replace("’", "'")


class Passerelle:
    """L'unique porte entre la page et le reste de Papote."""

    def __init__(self, app):
        self.app = app
        self.config = dict(app.config)
        # Le dernier texte corrige, pour que « remplacer un mot » sache sur
        # quoi travailler sans que la page ait a le renvoyer en entier.
        self._dernier_texte = ""

    # -- au chargement de la page -------------------------------------------

    def demarrer(self) -> dict:
        """Tout ce que la page doit savoir pour se dessiner la premiere fois."""
        return {
            "version": __version__,
            "pages": list(PAGES),
            "interrupteurs": list(INTERRUPTEURS),
            "raccourcis": list(RACCOURCIS),
            "registres": [
                {"cle": PARLE, "nom": "Parlé",
                 "explication": "« j'ai pas » reste « j'ai pas »."},
                {"cle": SOUTENU, "nom": "Soutenu",
                 "explication": "Remet les « ne », déplie les abréviations."},
            ],
            "regles_optionnelles": [
                {"cle": cle, "libelle": _libelle_regle(cle),
                 "actif": bool(self.config.get("regles_optionnelles", {})
                               .get(cle, defaut))}
                for cle, defaut in regles.REGLES_OPTIONNELLES.items()
            ],
            "reglages": self._reglages_exposes(),
            "logo": logo.svg(28, identifiant="marque"),
            "demarrage_disponible": demarrage.disponible(),
            "demarrage_actif": _sans_bruit(demarrage.actif, False),
            "compilee": maj.compilee(),
            "maj": self.etat_maj(),
        }

    def _reglages_exposes(self) -> dict:
        """Les reglages que la page manipule, et rien d'autre.

        Les delais de copie et de collage n'y sont pas : personne ne les
        regle depuis la fenetre, et les exposer serait promettre un ecran
        qui n'existe pas.
        """
        return {
            cle: self.config.get(cle, config_mod.DEFAUTS.get(cle))
            for cle in [i["cle"] for i in INTERRUPTEURS]
            + [r["cle"] for r in RACCOURCIS] + ["registre", "delai_oubli"]
        }

    # -- page « Corriger » --------------------------------------------------

    def corriger(self, texte: str) -> dict:
        """Corrige un texte et rend de quoi montrer ce qui a change."""
        if not (texte or "").strip():
            return {"texte": texte, "corrections": [], "inconnus": []}
        try:
            corrige, corrections = self.app.corriger_texte(texte)
        except LexiqueIntrouvable as e:
            return {"erreur": str(e).split("\n")[0]}
        except Exception as e:                       # noqa: BLE001
            journal_mod.erreur("Correction impossible", e)
            return {"erreur": f"La correction a échoué : {e}"}

        self._dernier_texte = corrige
        return {
            "texte": corrige,
            "corrections": [
                {"avant": c.avant, "apres": c.apres, "regle": c.regle,
                 "message": c.message}
                for c in corrections
            ],
            "inconnus": self._inconnus(corrige),
        }

    def _inconnus(self, texte: str) -> list[dict]:
        """Les mots qu'aucun dictionnaire ne connait, et quoi mettre a la place.

        Le correcteur ne remplace que ce dont il est sur. Quand il hesite —
        « ourné » vaut « journée » autant que « durée » — il se tait, et
        c'est ici que le mot refait surface avec ses candidats.
        """
        try:
            correcteur = self.app.correcteur
        except Exception:                            # noqa: BLE001
            return []

        connus = {_normaliser_mot(m) for m in self.config.get("mots_perso", [])}
        vus: set[str] = set()
        inconnus: list[dict] = []
        for jeton in grammaire.decouper(texte):
            mot = jeton.texte
            cle = mot.lower()
            if cle in vus or len(mot) < 2 or any(c.isdigit() for c in mot):
                continue
            vus.add(cle)
            if correcteur._connu(mot) or correcteur._protege(mot):
                continue
            if _normaliser_mot(mot) in connus:
                continue
            inconnus.append({
                "mot": mot,
                "propositions": _sans_bruit(
                    lambda m=mot: correcteur.propositions(m, maximum=3), []),
            })
            if len(inconnus) >= INCONNUS_MONTRES:
                break
        return inconnus

    def remplacer(self, texte: str, mot: str, remplacement: str) -> dict:
        """Remplace un mot entier partout dans le texte."""
        motif = re.compile(rf"(?<!\w){re.escape(mot)}(?!\w)")
        nouveau, nombre = motif.subn(remplacement.replace("\\", "\\\\"), texte)
        if not nombre:
            return {"texte": texte, "remplaces": 0, "inconnus": []}
        return {"texte": nouveau, "remplaces": nombre,
                "inconnus": self._inconnus(nouveau)}

    # -- page « Mon dictionnaire » ------------------------------------------

    def dictionnaire(self) -> dict:
        return {
            "mots": sorted(self.config.get("mots_perso", []), key=str.lower),
            "remplacements": [
                {"de": de, "vers": vers}
                for de, vers in sorted(
                    self.config.get("remplacements_perso", {}).items())
            ],
        }

    def ajouter_mot(self, mot: str) -> dict:
        mot = (mot or "").strip()
        if not mot:
            return {"erreur": "Écrivez d'abord un mot."}
        if " " in mot:
            return {"erreur": "Un mot, pas une expression : "
                              "les remplacements sont juste en dessous."}
        mots = list(self.config.get("mots_perso", []))
        if any(_normaliser_mot(m) == _normaliser_mot(mot) for m in mots):
            return {"erreur": f"« {mot} » y est déjà."}
        mots.append(mot)
        self.config["mots_perso"] = mots
        return self._enregistrer(f"« {mot} » ne sera plus corrigé.")

    def retirer_mot(self, mot: str) -> dict:
        mots = [m for m in self.config.get("mots_perso", []) if m != mot]
        self.config["mots_perso"] = mots
        return self._enregistrer(f"« {mot} » redevient corrigeable.")

    def ajouter_remplacement(self, de: str, vers: str) -> dict:
        de, vers = (de or "").strip(), (vers or "").strip()
        if not de or not vers:
            return {"erreur": "Il faut les deux : ce qu'on écrit, "
                              "et ce que ça doit devenir."}
        if _normaliser_mot(de) == _normaliser_mot(vers):
            return {"erreur": "Les deux sont identiques."}
        remplacements = dict(self.config.get("remplacements_perso", {}))
        remplacements[_normaliser_mot(de)] = vers
        self.config["remplacements_perso"] = remplacements
        return self._enregistrer(f"« {de} » deviendra « {vers} ».")

    def retirer_remplacement(self, de: str) -> dict:
        remplacements = dict(self.config.get("remplacements_perso", {}))
        remplacements.pop(de, None)
        self.config["remplacements_perso"] = remplacements
        return self._enregistrer(f"« {de} » ne sera plus remplacé.")

    # -- page « Vos fautes » ------------------------------------------------

    def fautes(self) -> dict:
        habitudes = getattr(self.app, "apprentissage", None)
        if habitudes is None:
            return {"total": 0, "frequentes": [], "lecons": []}
        return {
            "total": habitudes.total_corrections(),
            "frequentes": [
                {"mot": mot, "compte": compte}
                for mot, compte in habitudes.fautes_frequentes(15)
            ],
            "actif": bool(self.config.get("apprentissage", True)),
        }

    def oublier_faute(self, mot: str) -> dict:
        habitudes = getattr(self.app, "apprentissage", None)
        if habitudes is not None:
            habitudes.oublier_mot(mot)
            _sans_bruit(self.app.enregistrer_habitudes, None)
        return {"message": f"« {mot} » ne compte plus.", "fautes": self.fautes()}

    def effacer_historique(self) -> dict:
        habitudes = getattr(self.app, "apprentissage", None)
        if habitudes is not None:
            habitudes.vider()
            _sans_bruit(self.app.enregistrer_habitudes, None)
        return {"message": "Historique effacé.", "fautes": self.fautes()}

    # -- page « Applications » ----------------------------------------------

    def applications(self) -> dict:
        return {
            "courante": _sans_bruit(self.app.application_courante, None),
            "exclues": sorted(self.config.get("applications_exclues", [])),
            "registres": [
                {"application": app, "registre": registre}
                for app, registre in sorted(
                    self.config.get("registre_par_application", {}).items())
            ],
        }

    def exclure(self, application: str) -> dict:
        application = (application or "").strip().lower()
        if not application:
            return {"erreur": "Nommez une application."}
        exclues = list(self.config.get("applications_exclues", []))
        if application in exclues:
            return {"erreur": f"« {application} » y est déjà."}
        exclues.append(application)
        self.config["applications_exclues"] = exclues
        return self._enregistrer(f"Papote se taira dans « {application} ».")

    def reintegrer(self, application: str) -> dict:
        exclues = [a for a in self.config.get("applications_exclues", [])
                   if a != application]
        self.config["applications_exclues"] = exclues
        return self._enregistrer(f"Papote corrigera de nouveau dans "
                                 f"« {application} ».")

    def registre_application(self, application: str, registre: str) -> dict:
        application = (application or "").strip().lower()
        if not application:
            return {"erreur": "Nommez une application."}
        if registre not in REGISTRES:
            return {"erreur": f"Registre inconnu : {registre}."}
        par_application = dict(self.config.get("registre_par_application", {}))
        par_application[application] = registre
        self.config["registre_par_application"] = par_application
        return self._enregistrer(f"« {application} » passe en registre "
                                 f"{registre}.")

    def retirer_registre_application(self, application: str) -> dict:
        par_application = dict(self.config.get("registre_par_application", {}))
        par_application.pop(application, None)
        self.config["registre_par_application"] = par_application
        return self._enregistrer(f"« {application} » reprend le registre "
                                 f"par défaut.")

    # -- page « Reglages » --------------------------------------------------

    def regler(self, cle: str, valeur) -> dict:
        """Change un reglage et l'enregistre aussitot.

        Il n'y a pas de bouton « Enregistrer » : un reglage qu'on bascule est
        un reglage qu'on veut. Le bouton ne servait qu'a le perdre en fermant
        la fenetre.
        """
        if cle not in config_mod.DEFAUTS:
            return {"erreur": f"Réglage inconnu : {cle}."}
        self.config[cle] = valeur
        return self._enregistrer(None)

    def regler_regle(self, nom: str, actif: bool) -> dict:
        optionnelles = dict(self.config.get("regles_optionnelles", {}))
        optionnelles[nom] = bool(actif)
        self.config["regles_optionnelles"] = optionnelles
        return self._enregistrer(None)

    def basculer_demarrage(self, actif: bool) -> dict:
        try:
            demarrage.installer() if actif else demarrage.retirer()
        except Exception as e:                       # noqa: BLE001
            return {"erreur": f"Impossible : {e}"}
        return {"message": "Papote se lancera avec Windows." if actif
                else "Papote ne se lancera plus avec Windows.",
                "demarrage_actif": _sans_bruit(demarrage.actif, False)}

    # -- mises a jour -------------------------------------------------------

    def etat_maj(self) -> dict:
        en_attente = _sans_bruit(maj.en_attente, None) is not None
        return {
            "compilee": maj.compilee(),
            "prete": en_attente,
            "numero": _sans_bruit(maj.numero_en_attente, None) if en_attente
            else None,
        }

    def verifier_maj(self) -> dict:
        """Cherche, telecharge, et dit quoi proposer. A appeler dans un fil."""
        if not maj.compilee():
            return {"message": "Lancé depuis les sources : "
                               "« git pull » fait le travail."}
        try:
            version = maj.disponible()
        except maj.MiseAJourImpossible as e:
            return {"erreur": f"Vérification impossible : {e}"}
        if version is None:
            return {"message": "Vous êtes déjà à jour.", "maj": self.etat_maj()}
        try:
            maj.installer_maintenant(version)
        except maj.MiseAJourImpossible as e:
            return {"erreur": f"Téléchargement impossible : {e}"}
        return {"message": f"Version {version} téléchargée.",
                "maj": self.etat_maj()}

    def redemarrer(self) -> dict:
        try:
            maj.demander_redemarrage()
        except OSError as e:
            return {"erreur": f"Impossible : {e}"}
        return {"message": "Papote redémarre… "
                           "Cette fenêtre peut être fermée."}

    # -- journal ------------------------------------------------------------

    def journal(self) -> dict:
        return {
            "chemin": str(_sans_bruit(journal_mod.chemin, "")),
            "contenu": _sans_bruit(lambda: journal_mod.lire(200), ""),
        }

    def vider_journal(self) -> dict:
        _sans_bruit(journal_mod.vider, None)
        return {"message": "Journal vidé.", "journal": self.journal()}

    # -- enregistrement -----------------------------------------------------

    def _enregistrer(self, message: str | None) -> dict:
        """Ecrit la configuration et la fait relire a l'application.

        L'icone tourne dans un autre processus et relit le fichier toute
        seule ; celle-ci, c'est nous qui la prevenons.
        """
        try:
            config_mod.sauvegarder(self.config)
        except OSError as e:
            return {"erreur": f"Enregistrement impossible : {e}"}
        _sans_bruit(lambda: self.app.recharger(dict(self.config)), None)
        reponse = {"reglages": self._reglages_exposes()}
        if message:
            reponse["message"] = message
        return reponse


def _libelle_regle(cle: str) -> str:
    libelles = {
        "MAJUSCULE_PHRASE": "Majuscule en début de phrase",
        "PONCTUATION_POINT": "Point final manquant",
        "TYPOGRAPHIE": "Typographie française (« », …, espaces fines)",
    }
    return libelles.get(cle, cle.replace("_", " ").capitalize())


def _sans_bruit(action, defaut):
    """Appelle `action`, et rend `defaut` si elle echoue.

    Beaucoup de ce que la page affiche est accessoire : le nom de
    l'application au premier plan, l'etat du demarrage automatique. Qu'un de
    ces renseignements manque ne doit pas empecher la fenetre de s'ouvrir.
    """
    try:
        return action()
    except Exception:                                # noqa: BLE001
        return defaut
