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
2. Installez **Java** depuis [adoptium.net](https://adoptium.net/) (bouton
   *Latest LTS*). C'est le moteur linguistique qui en a besoin.
3. Double-cliquez sur **`installer.bat`** et patientez (~250 Mo de
   dictionnaire français, une seule fois).
4. Double-cliquez sur **`Correcteur.vbs`**.

Une icône bleue apparaît près de l'horloge : l'outil est actif.

### Démarrer automatiquement avec Windows

Appuyez sur `Win+R`, tapez `shell:startup`, validez, puis glissez un raccourci
vers `Correcteur.vbs` dans le dossier qui s'ouvre.

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
python -m correcteur --console      # sans icône, journal en console
python -m correcteur --config       # chemin du fichier de réglages
```

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

Pour construire un exécutable autonome : `construire_exe.bat` → `dist\Correcteur.exe`
(Java reste nécessaire sur la machine cible).

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
