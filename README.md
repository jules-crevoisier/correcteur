# Correcteur

Correcteur d'orthographe français pour Windows qui **respecte votre façon d'écrire**.

Sélectionnez du texte, appuyez sur `Ctrl+Alt+C`, le texte corrigé remplace la
sélection. Aucune fenêtre, aucun clic, aucun copier-coller manuel.

## Pourquoi celui-ci plutôt que Reverso

Les correcteurs classiques appliquent les normes du **français écrit soutenu**.
Sur un message Discord, le résultat est artificiel :

| Vous écrivez | Reverso propose | Correcteur |
|---|---|---|
| `j'ai pas compris` | ~~je n'ai pas compris~~ | `j'ai pas compris` |
| `y a personne` | ~~il n'y a personne~~ | `y a personne` |
| `faut que j'y aille` | ~~il faut que j'y aille~~ | `faut que j'y aille` |
| `c'est pas grave` | ~~ce n'est pas grave~~ | `c'est pas grave` |
| `dsl` | ~~ADSL~~ | `dsl` |

« J'ai pas » n'est pas une faute, c'est du français parlé. Cet outil corrige
les **fautes** — accords, conjugaisons, accents, homonymes — et laisse le
**registre** tranquille.

| Vous écrivez | Correcteur |
|---|---|
| `je sais pas si sa va marcher` | `je sais pas si ça va marcher` |
| `ils on mangé tout les gateaux` | `ils ont mangé tous les gâteaux` |
| `Les filles sont venu hier` | `Les filles sont venues hier` |
| `ca ma pris 2 heures` | `ça m'a pris 2 heures` |
| `Est ce que tu peut venir` | `Est-ce que tu peux venir` |

Tout fonctionne **hors ligne et gratuitement**. Aucun texte n'est envoyé sur
Internet, aucun compte, aucune clé d'API.

## Installation

1. Installez **Python** depuis [python.org](https://www.python.org/downloads/)
   en cochant *Add Python to PATH*.
2. Double-cliquez sur **`installer.bat`** et patientez.
3. Double-cliquez sur **`Correcteur.vbs`**.

Une icône bleue apparaît près de l'horloge : l'outil est actif.

L'installateur télécharge Java automatiquement s'il est absent — vous n'avez
rien à installer vous-même. Comptez ~300 Mo au total (Java + dictionnaire
français), une seule fois.

### Démarrage automatique avec Windows

Clic droit sur l'icône → **Lancer au démarrage de Windows**. C'est tout.

L'entrée est inscrite dans votre propre session (`HKCU\...\Run`), sans droits
administrateur, et se retire par le même menu. Si vous déplacez ensuite le
dossier de l'application, elle corrige le chemin toute seule au lancement
suivant.

En ligne de commande : `python -m correcteur --demarrage on` (ou `off`, ou
`etat`).

## Exécutable autonome

Pour obtenir une version qui ne demande **ni Python ni Java** sur la machine
de destination :

```
installer.bat          (une fois, pour préparer l'environnement)
construire_exe.bat
```

Le résultat est dans `dist\Correcteur\` : un dossier déplaçable contenant
`Correcteur.exe`, le moteur Java et le dictionnaire français. Copiez-le où
vous voulez — y compris sur une clé USB — lancez `Correcteur.exe`, puis
activez le démarrage automatique depuis l'icône.

Le format est un dossier plutôt qu'un fichier unique parce que l'ensemble
pèse ~300 Mo : un exécutable unique devrait tout ré-extraire à chaque
démarrage. Le dossier ne contient qu'un seul fichier cliquable et démarre
instantanément.

## Utilisation

1. Écrivez votre message, dans n'importe quelle application.
2. Sélectionnez-le (`Ctrl+A` suffit dans un champ de saisie).
3. `Ctrl+Alt+C`.

Le texte corrigé remplace la sélection et une notification résume ce qui a
changé. Un clic droit sur l'icône permet de mettre l'outil en pause ou
d'ouvrir les réglages.

## Réglages

Clic droit sur l'icône → *Ouvrir les réglages*. Le fichier se trouve dans
`%APPDATA%\Correcteur\config.json`. Redémarrez l'application après modification.

| Réglage | Par défaut | Rôle |
|---|---|---|
| `raccourci` | `ctrl+alt+c` | Combinaison de touches. Ex. : `ctrl+shift+f`, `f9` |
| `collage_auto` | `true` | `false` : le texte corrigé est mis dans le presse-papiers sans être collé |
| `notifications` | `true` | Affiche le résumé des corrections |
| `lexique_perso` | `[]` | Mots à ne jamais corriger : pseudos, jargon, noms de jeux |
| `delai_copie` | `0.35` | À augmenter si une application lente rate la capture |
| `regles_optionnelles` | voir ci-dessous | Corrections désactivées par défaut |

Deux règles sont désactivées d'origine car elles relèvent du goût :

```json
"regles_optionnelles": {
  "UPPERCASE_SENTENCE_START": false,   // majuscule en début de phrase
  "PONCTUATION_POINT": false           // point final manquant
}
```

Passez-les à `true` pour les activer.

### Ajouter vos propres mots

```json
"lexique_perso": ["Valorant", "Kayn", "monpseudo", "gg"]
```

## Ce que l'outil ne touche jamais

- Les liens, adresses e-mail, mentions `@pseudo`, salons `#general`
- Les blocs de code entre backticks et les spoilers `||...||`
- Les emojis `:joy:` et les emojis Discord personnalisés
- L'emphase volontaire : `ouiiii`, `mdrrrr`, `nooon`
- L'argot d'Internet : `dsl`, `tkt`, `jsp`, `wsh`, `askip`… (~150 mots)
- Tout mot contenant un chiffre

## En ligne de commande

```
python -m correcteur --texte "je sais pas si sa va marcher"
python -m correcteur --verifier      # contrôle Java, moteur et réglages
python -m correcteur --demarrage on  # se lance avec Windows (on/off/etat)
python -m correcteur --console       # sans icône, journal en console
python -m correcteur --config        # chemin du fichier de réglages
```

`--verifier` est le premier réflexe si quelque chose ne fonctionne pas : il
affiche la version de Java détectée, teste une correction réelle et indique
l'état du démarrage automatique.

## Comment il évite de dégrader vos messages

LanguageTool, le moteur linguistique, propose parfois des corrections pires
que la faute d'origine : `mangé` → `mangait` (qui n'existe pas), `ta fini` →
`te finir`, `ceter` → `ce ter`. Trois garde-fous filtrent ces propositions :

1. **Validation lexicale** — un mot proposé qui n'est pas au dictionnaire est
   rejeté.
2. **Interdiction de re-découpage** — une suggestion qui change le nombre de
   mots est rejetée, sauf si elle ne fait qu'ajouter une apostrophe ou un
   trait d'union.
3. **Changements cosmétiques uniquement** sur les groupes de plusieurs mots —
   accents, apostrophes, terminaisons d'accord. Les réécritures sont écartées.

Le principe : **mieux vaut sous-corriger que corrompre**. Un message qui
garde une faute reste lisible ; un message mal corrigé ne l'est plus.

## Développement

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

`tests/test_moteur.py` simule LanguageTool et teste la logique de filtrage
(instantané). `tests/test_integration.py` valide le comportement réel contre
le vrai moteur (~50 s).

`tests/test_demarrage.py` et `tests/test_java.py` simulent respectivement le
registre Windows et l'environnement Java : toute la suite tourne sur
n'importe quel système.

## Structure

| Fichier | Rôle |
|---|---|
| `correcteur/regles.py` | Quelles règles ignorer, quels mots protéger |
| `correcteur/moteur.py` | Filtrage des suggestions et garde-fous |
| `correcteur/app.py` | Enchaînement sélection → correction → collage |
| `correcteur/presse_papier.py` | Capture de la sélection via le presse-papiers |
| `correcteur/raccourci.py` | Raccourci clavier global |
| `correcteur/interface.py` | Icône dans la zone de notification |
| `correcteur/config.py` | Lecture et écriture des réglages |
| `correcteur/java.py` | Localisation de Java (portable, `JAVA_HOME`, `PATH`) |
| `correcteur/demarrage.py` | Lancement automatique via le registre Windows |
| `correcteur/chemins.py` | Emplacements selon le mode (sources, `.exe`, portable) |
| `outils/installer_java.ps1` | Téléchargement d'un Java portable |
| `outils/assembler.py` | Assemblage de la distribution autonome |
