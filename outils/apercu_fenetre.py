# -*- coding: utf-8 -*-
"""Photographie la fenetre sans l'ouvrir.

La fenetre de Papote est une page web. Sur Windows c'est le moteur d'Edge
qui la rend ; ici, c'est Chromium — le meme moteur, sans la fenetre. Cela
permet de voir a quoi ressemble une page avant de compiler quoi que ce soit,
et de comparer deux etats d'un coup d'oeil.

Le pont vers Python est remplace par une doublure alimentee par la vraie
`Passerelle` : ce qui s'affiche vient donc des memes donnees que dans
l'application, et non d'un jeu d'exemple qui finirait par mentir.

    pip install playwright
    python outils/apercu_fenetre.py                     toutes les pages
    python outils/apercu_fenetre.py corriger reglages   celles-la seulement
    python outils/apercu_fenetre.py --clair             en theme clair
    python outils/apercu_fenetre.py --large 560         a cette largeur
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

DESTINATION = Path("/tmp/apercu-papote")

# La fenetre s'ouvre a cette taille ; c'est donc la que le dessin doit tomber
# juste. Les autres largeurs se demandent avec « --large ».
LARGEUR, HAUTEUR = 980, 700


def _donnees() -> dict:
    """Les reponses que la doublure sert a la page.

    La page « Dicter » est montree dans son etat le plus interessant : les
    modeles installes, une reunion deja transcrite. C'est celui qu'on veut
    regarder quand on dessine.
    """
    """Ce que la passerelle rendrait, sur une configuration d'exemple.

    L'exemple est garni : une fenetre vide est facile a trouver belle, et ne
    dit rien de ce qu'elle devient une fois remplie.
    """
    from papote import config as config_mod
    from papote.app import Application
    from papote.lexique import Lexique
    from papote.passerelle import Passerelle

    config = dict(config_mod.DEFAUTS)
    config["mots_perso"] = ["Zbeul", "Papote", "gg", "Kylian", "tkt"]
    config["remplacements_perso"] = {"ptetre": "peut-être",
                                     "cdlt": "cordialement",
                                     "jsp": "je sais pas"}
    config["applications_exclues"] = ["code.exe", "windowsterminal.exe",
                                      "jeu.exe"]
    config["registre_par_application"] = {"outlook.exe": "soutenu"}

    lexique = Lexique()
    lexique.charger()
    app = Application(config=config, journal=lambda _m: None)
    app._lexique = lexique
    passerelle = Passerelle(app)

    exemple = "ça va chef ta pasé une bonne ourné ? jesper que oui"
    correction = passerelle.corriger(exemple)

    return {
        "demarrer": passerelle.demarrer(),
        "corriger": correction,
        "exemple": exemple,
        "dictionnaire": passerelle.dictionnaire(),
        "applications": passerelle.applications(),
        "fautes": {
            "total": 1287,
            "actif": True,
            "frequentes": [
                {"mot": "malgres", "compte": 23},
                {"mot": "sa", "compte": 19},
                {"mot": "ca", "compte": 17},
                {"mot": "parmis", "compte": 11},
                {"mot": "jai", "compte": 9},
                {"mot": "quil", "compte": 7},
                {"mot": "tous le monde", "compte": 4},
            ],
        },
        "dictee": {
            "disponible": {"vosk": True, "sounddevice": True},
            "en_cours": False,
            "reunion": True,
            "erreur": "",
            "modeles": [
                {"nom": "vosk-model-small-fr-0.22",
                 "role": "entendre le français",
                 "taille": 41_000_000, "installe": True},
                {"nom": "vosk-model-spk-0.4",
                 "role": "distinguer les voix",
                 "taille": 13_000_000, "installe": True},
            ],
            "poids_installe": 54_000_000,
            "participants": ["Marion", "Personne 2"],
            "tours": [
                {"locuteur": "Marion", "debut": 0.0, "fin": 12.0,
                 "texte": "Bonjour à tous. Moi c'est Marion. On passe au "
                          "budget de janvier. Est-ce qu'on a les chiffres ?"},
                {"locuteur": "Personne 2", "debut": 12.0, "fin": 31.0,
                 "texte": "Pas encore. Je m'occupe de relancer la compta "
                          "d'ici vendredi."},
                {"locuteur": "Marion", "debut": 31.0, "fin": 48.0,
                 "texte": "Très bien. Donc on part sur la deuxième option."},
            ],
        },
        "journal": {
            "chemin": r"C:\Users\vous\AppData\Roaming\Papote\journal.log",
            "contenu": "2026-09-16 14:02:11  [info]  Papote démarre (v1.0.30)\n"
                       "2026-09-16 14:02:12  [info]  Lexique chargé : "
                       "434 738 formes\n"
                       "2026-09-16 14:09:40  [info]  Correction appliquée : "
                       "« sa » → « ça »\n",
        },
    }


DOUBLURE = """
(() => {
  const donnees = __DONNEES__;
  const rien = { message: "" };
  const api = {
    demarrer: async () => donnees.demarrer,
    corriger: async () => donnees.corriger,
    remplacer: async (texte) => ({ texte, remplaces: 0, inconnus: [] }),
    dictionnaire: async () => donnees.dictionnaire,
    applications: async () => donnees.applications,
    fautes: async () => donnees.fautes,
    journal: async () => donnees.journal,
    ajouter_mot: async () => rien,
    retirer_mot: async () => rien,
    ajouter_remplacement: async () => rien,
    retirer_remplacement: async () => rien,
    exclure: async () => rien,
    reintegrer: async () => rien,
    registre_application: async () => rien,
    retirer_registre_application: async () => rien,
    regler: async () => rien,
    regler_regle: async () => rien,
    basculer_demarrage: async () => rien,
    verifier_maj: async () => rien,
    redemarrer: async () => rien,
    effacer_historique: async () => rien,
    vider_journal: async () => rien,
    etat_dictee: async () => donnees.dictee,
    installer_modeles: async () => rien,
    commencer_dictee: async () => rien,
    arreter_dictee: async () => rien,
    renommer_locuteur: async () => rien,
    compte_rendu: async () => ({ ok: true, texte: "# Compte rendu" }),
    oublier_dictee: async () => rien,
  };
  window.pywebview = { api };
})();
"""


def _chromium() -> str | None:
    """Le Chromium deja present, s'il y en a un.

    Les versions de Playwright et de son navigateur vont par paire ; quand
    la machine en heberge un d'une autre paire, mieux vaut le designer que
    d'en telecharger cent cinquante megaoctets de plus.
    """
    for candidat in sorted(Path("/opt/pw-browsers").glob("chromium-*"),
                           reverse=True):
        binaire = candidat / "chrome-linux" / "chrome"
        if binaire.is_file():
            return str(binaire)
    return None


def photographier(pages: list[str], clair: bool, largeur: int,
                  hauteur: int) -> list[Path]:
    from playwright.sync_api import sync_playwright

    from papote.chemins import dossier_web

    donnees = _donnees()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    adresse = (dossier_web() / "index.html").as_uri()
    ecrits = []

    with sync_playwright() as pilote:
        navigateur = pilote.chromium.launch(executable_path=_chromium())
        contexte = navigateur.new_context(
            viewport={"width": largeur, "height": hauteur},
            device_scale_factor=2,        # comme un ecran moderne
            color_scheme="light" if clair else "dark",
            locale="fr-FR",
        )
        contexte.add_init_script(
            DOUBLURE.replace("__DONNEES__",
                             json.dumps(donnees, ensure_ascii=False)))
        page = contexte.new_page()
        page.goto(adresse)
        page.wait_for_selector(".entree")

        for cle in pages:
            page.evaluate("(cle) => afficher(cle)", cle)
            if cle == "corriger":
                # Montrer la page au travail plutot qu'a vide.
                page.evaluate(
                    "(d) => { document.querySelector('#champ').value = d.corriger.texte;"
                    "         compter();"
                    "         montrerCorrections(d.corriger.corrections);"
                    "         montrerInconnus(d.corriger.inconnus); }",
                    donnees)
            page.wait_for_timeout(420)      # laisser les animations finir
            nom = f"{cle}{'-clair' if clair else ''}-{largeur}.png"
            chemin = DESTINATION / nom
            page.screenshot(path=str(chemin))
            ecrits.append(chemin)

        navigateur.close()
    return ecrits


def main() -> int:
    from papote.passerelle import PAGES

    arguments = sys.argv[1:]
    clair = "--clair" in arguments
    largeur = LARGEUR
    if "--large" in arguments:
        largeur = int(arguments[arguments.index("--large") + 1])
    demandees = [a for a in arguments
                 if not a.startswith("--") and not a.isdigit()]
    pages = demandees or [p["cle"] for p in PAGES]

    for chemin in photographier(pages, clair, largeur, HAUTEUR):
        print(f"  {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
