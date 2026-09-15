# Correcteur

Correcteur d'orthographe français pour Windows qui **respecte votre façon
d'écrire**.

Sélectionnez du texte, appuyez sur `Ctrl+Alt+C`, le texte corrigé remplace la
sélection. Aucune fenêtre, aucun clic, aucun copier-coller manuel.

**Un seul fichier**, `Correcteur.exe` : ni Python, ni Java, ni compte, ni clé
d'API. Tout fonctionne hors ligne — aucun texte n'est envoyé sur Internet.

## Pourquoi celui-ci plutôt que Reverso

Les correcteurs classiques appliquent les normes du **français écrit soutenu**.
Sur un message Discord, le résultat sonne faux :

| Vous écrivez | Reverso propose | Correcteur |
|---|---|---|
| `j'ai pas compris` | ~~je n'ai pas compris~~ | `j'ai pas compris` |
| `y a personne` | ~~il n'y a personne~~ | `y a personne` |
| `faut que j'y aille` | ~~il faut que j'y aille~~ | `faut que j'y aille` |
| `c'est pas grave` | ~~ce n'est pas grave~~ | `c'est pas grave` |
| `c'est quoi ce truc` | ~~qu'est-ce que c'est~~ | `c'est quoi ce truc` |
| `dsl`, `tkt`, `wsh` | ~~ADSL~~ | `dsl`, `tkt`, `wsh` |

« J'ai pas » n'est pas une faute, c'est du français parlé. Cet outil corrige
les **fautes** — accents, accords, conjugaison, homonymes — et laisse le
**registre** tranquille.

| Vous écrivez | Correcteur |
|---|---|
| `je sais pas si sa va marcher` | `je sais pas si ça va marcher` |
| `ils on mangé tout les gateaux` | `ils ont mangé tous les gâteaux` |
| `ca ma pris 2 heures` | `ça m'a pris 2 heures` |
| `Est ce que tu peut venir` | `Est-ce que tu peux venir` |
| `cest vraiment tres interressant se truc` | `c'est vraiment très intéressant ce truc` |
| `tas vu ou est passé mon telephone` | `t'as vu où est passé mon téléphone` |
| `jai pas compris se que tu dit` | `j'ai pas compris ce que tu dis` |
| `elles sont venu hier mes elles sont reparties tot` | `elles sont venues hier mais elles sont reparties tôt` |
| `je vais mangé un truc` | `je vais manger un truc` |
| `ils mange trop` | `ils mangent trop` |

## Installation

Téléchargez **`Correcteur.exe`** depuis l'onglet
[Releases](../../releases) — la dernière version est tout en haut — et
double-cliquez dessus.

Windows affichera un avertissement SmartScreen au premier lancement :
l'exécutable n'est pas signé numériquement. *Informations complémentaires* →
*Exécuter quand même*.

Une icône bleue apparaît près de l'horloge : l'outil est actif. C'est tout —
il n'y a rien d'autre à installer.

### Démarrage automatique avec Windows

Clic droit sur l'icône → **Lancer au démarrage de Windows**.

L'entrée est inscrite dans votre propre session (`HKCU\...\Run`), sans droits
administrateur, et se retire par le même menu. Si vous déplacez ensuite
l'exécutable, il corrige le chemin tout seul au lancement suivant.

En ligne de commande : `Correcteur.exe --demarrage on` (ou `off`, ou `etat`).

## Utilisation

**Partout**, c'est le raccourci :

1. Écrivez votre message, dans n'importe quelle application.
2. Sélectionnez-le (`Ctrl+A` suffit dans un champ de saisie).
3. `Ctrl+Alt+C`.

Le texte corrigé remplace la sélection et une notification résume ce qui a
changé.

**Pour relire un texte avant de l'envoyer**, clic droit sur l'icône →
*Ouvrir la fenêtre*. Collez, `Ctrl+Entrée`, le texte corrigé s'affiche avec la
liste des corrections.

Le clic droit permet aussi de mettre l'outil en pause ou d'ouvrir les réglages.

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
  "MAJUSCULE_PHRASE": false,     // majuscule en début de phrase
  "PONCTUATION_POINT": false     // point final manquant
}
```

Passez-les à `true` pour les activer.

### Ajouter vos propres mots

```json
"lexique_perso": ["Valorant", "Kayn", "monpseudo", "gg"]
```

## Ce que l'outil ne touche jamais

- Le registre parlé : négations sans « ne », `y a`, `faut que`, `ça`, `c'est quoi`
- Les liens, adresses e-mail, mentions `@pseudo`, salons `#general`
- Les blocs de code entre backticks et les spoilers `||...||`
- Les emojis `:joy:` et les emojis Discord personnalisés
- L'emphase volontaire : `ouiiii`, `mdrrrr`, `nooon`
- L'argot d'Internet : `dsl`, `tkt`, `jsp`, `wsh`, `askip`… (~150 mots)
- Les mots anglais courants : `the game`, `check this out` (~380 mots)
- Les sigles en capitales, les noms propres et tout mot contenant un chiffre

## Comment ça marche

Aucune bibliothèque de correction, aucun serveur : le moteur tient dans trois
fichiers Python et un dictionnaire.

| Couche | Fichier | Rôle |
|---|---|---|
| Protection | `correcteur/regles.py` | Ce qui sort du circuit avant examen |
| Grammaire | `correcteur/grammaire.py` | 24 règles de contexte : homonymes, accords, conjugaison |
| Orthographe | `correcteur/lexique.py` | 450 000 formes françaises, accents et fautes de frappe |

### L'orthographe

Le dictionnaire est indexé par **squelette** : la graphie du mot privée de ses
accents. `gateaux`, `gâteaux` et `gâteâux` partagent le squelette `gateaux`.
Un mot inconnu se corrige alors en deux temps :

1. **même squelette** — il ne manquait que les accents : `tres` → `très`,
   `deja` → `déjà`, `coeur` → `cœur` ;
2. **squelette à une frappe d'écart** — il y avait aussi une faute de frappe :
   `interressant` → `intéressant`, `anniverssaire` → `anniversaire`.

On ne devine jamais : on fabrique des candidats et on ne garde que ceux qui
existent. Quand deux candidats sont aussi plausibles l'un que l'autre — `prés`
et `près`, `élève` et `élevé` — une liste de fréquences les départage, et si
elle ne tranche pas nettement, **le mot est laissé tel quel**.

### La grammaire

Le dictionnaire ne voit pas les fautes où les deux graphies existent :
`sa va`, `ils on mangé`, `j'ai manger`. Vingt-quatre règles regardent les mots
voisins pour trancher, et chacune ne se déclenche que sur un contexte où
l'autre lecture est impossible :

| On corrige | On ne touche pas |
|---|---|
| `sa va` → `ça va` | `sa mère est venue` |
| `ils on mangé` → `ils ont mangé` | `on mange à midi` |
| `j'ai manger` → `j'ai mangé` | `j'ai été manger dehors` |
| `tout les jours` → `tous les jours` | `tout le monde est là` |
| `des enfant` → `des enfants` | `je les mange` |
| `tas vu` → `t'as vu` | `un tas de trucs` |
| `je vais a la gare` → `à la gare` | `il a la flemme` |

Le principe, partout : **mieux vaut sous-corriger que corrompre**. Un message
qui garde une faute reste lisible ; un message mal corrigé ne l'est plus.

## En ligne de commande

```
Correcteur.exe --texte "je sais pas si sa va marcher"
Correcteur.exe --fenetre        # ouvre la fenêtre de correction
Correcteur.exe --verifier       # contrôle dictionnaire, correction et réglages
Correcteur.exe --demarrage on   # se lance avec Windows (on/off/etat)
Correcteur.exe --console        # sans icône, journal en console
Correcteur.exe --config         # chemin du fichier de réglages
```

`--verifier` est le premier réflexe si quelque chose ne fonctionne pas.

Ces commandes écrivent dans le terminal qui les a lancées. Lancé d'un
double-clic, `Correcteur.exe` n'affiche rien et se contente d'apparaître près
de l'horloge : c'est une application de zone de notification, pas un
programme en ligne de commande.

Depuis les sources, remplacez `Correcteur.exe` par `python -m correcteur`.

## Développement

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q          # ~130 tests, moins d'une seconde
python -m correcteur --texte "sa va ?"
```

Sous Windows, `installer.bat` prépare l'environnement et `Correcteur.vbs`
lance l'outil sans fenêtre noire.

### Fabriquer l'exécutable

```
construire_exe.bat
```

Le résultat est `dist\Correcteur.exe` : un fichier unique d'une vingtaine de
mégaoctets, dictionnaire compris.

C'est aussi ce que fait GitHub à chaque envoi, sur n'importe quelle branche
([`.github/workflows/executable.yml`](.github/workflows/executable.yml)) :
l'exécutable est construit sur une machine Windows, testé, puis déposé dans
l'onglet *Actions*.

Sur `main`, il est en plus publié dans les *Releases*, sous un numéro calculé
tout seul : `majeur.mineur` vient de `__version__` dans
`correcteur/__init__.py`, le dernier nombre est le nombre de commits. Chaque
envoi donne donc une version de plus, sans jamais retomber sur la même, et il
n'y a aucun tag à poser à la main. Pour ouvrir une nouvelle série — `v1.1.x` —
il suffit de changer `__version__`.

### Régénérer le dictionnaire

Les fichiers de `donnees/` sont livrés prêts à l'emploi. Ils ne se
reconstruisent que si le dictionnaire Hunspell change :

```bash
python outils/construire_lexique.py
```

Origine et licences des données : [`donnees/LICENCES.md`](donnees/LICENCES.md).
Le dictionnaire français vient de [Dicollecte](https://grammalecte.net/)
(MPL 2.0), la liste de fréquences de
[wordfreq](https://github.com/rspeer/wordfreq) (Apache 2.0).

## Structure

| Fichier | Rôle |
|---|---|
| `correcteur/lexique.py` | Dictionnaire, candidats, décision |
| `correcteur/grammaire.py` | Règles de contexte |
| `correcteur/regles.py` | Mots et motifs protégés, règles optionnelles |
| `correcteur/moteur.py` | Assemblage des trois couches |
| `correcteur/app.py` | Enchaînement sélection → correction → collage |
| `correcteur/presse_papier.py` | Capture de la sélection via le presse-papiers |
| `correcteur/raccourci.py` | Raccourci clavier global |
| `correcteur/interface.py` | Icône dans la zone de notification |
| `correcteur/fenetre.py` | Fenêtre de correction (tkinter) |
| `correcteur/config.py` | Lecture et écriture des réglages |
| `correcteur/demarrage.py` | Lancement automatique via le registre Windows |
| `correcteur/chemins.py` | Emplacements selon le mode (sources, `.exe`) |
| `outils/construire_lexique.py` | Fabrication des fichiers de `donnees/` |
