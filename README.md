# Papote

Correcteur d'orthographe français pour Windows qui **respecte votre façon
d'écrire**. Il s'appelle Papote parce qu'il est fait pour la conversation,
pas pour la dissertation.

Il corrige **pendant que vous tapez**, dans n'importe quelle application. Rien
à sélectionner, aucun raccourci à retenir : vous écrivez `sa va`, il écrit
`ça va`. Une correction vous déplaît ? **Retour arrière** la défait, comme sur
un téléphone.

Il se tait là où il gênerait — terminal, éditeur de code — et il apprend de ce
que vous refusez.

**Un seul fichier**, `Papote.exe` : ni Python, ni Java, ni compte, ni clé
d'API. Tout fonctionne hors ligne — aucun texte n'est envoyé sur Internet.

## Pourquoi celui-ci plutôt que Reverso

Les correcteurs classiques appliquent les normes du **français écrit soutenu**.
Sur un message Discord, le résultat sonne faux :

| Vous écrivez | Reverso propose | Papote |
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

| Vous écrivez | Papote |
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

Téléchargez **`Papote.msi`** depuis l'onglet
[Releases](../../releases) — la dernière version est tout en haut — et
double-cliquez dessus.

L'installateur ne demande **aucun droit administrateur** : Papote se range
dans votre profil. Il propose trois choses au passage, à cocher ou non :

| Étape | Par défaut |
|---|---|
| Papote et son dictionnaire | Obligatoire, 20 Mo |
| Lancer au démarrage de Windows | Coché |
| Raccourci sur le bureau | Décoché |

Les deux dernières se retrouvent ensuite dans les réglages de l'application :
la case de l'installateur et celle des réglages écrivent au même endroit.

Vous préférez ne rien installer ? **`Papote.exe`** est le programme seul, à
poser où vous voulez — une clé USB, par exemple — et à lancer tel quel.

Windows affichera un avertissement SmartScreen au premier lancement :
l'exécutable n'est pas signé numériquement. *Informations complémentaires* →
*Exécuter quand même*.

> L'outil s'est appelé **Correcteur** jusqu'à la version 1.0. Si vous l'aviez
> déjà installé, vos réglages et votre dictionnaire sont repris tels quels au
> premier lancement de Papote, et l'ancienne entrée de démarrage automatique
> est remplacée par la nouvelle. L'ancien `Correcteur.exe` peut être supprimé.

Une icône bleue apparaît près de l'horloge : l'outil est actif. C'est tout —
il n'y a rien d'autre à installer.

### Démarrage automatique avec Windows

Clic droit sur l'icône → **Lancer au démarrage de Windows**, ou la case du
même nom dans les réglages.

L'entrée est inscrite dans votre propre session (`HKCU\...\Run`), sans droits
administrateur, et se retire par le même menu. Si vous déplacez ensuite
l'exécutable, il corrige le chemin tout seul au lancement suivant.

En ligne de commande : `Papote.exe --demarrage on` (ou `off`, ou `etat`).

## Utilisation

### Il corrige tout seul

Écrivez, n'importe où. Le mot se corrige dès que vous tapez l'espace ou la
ponctuation qui le termine :

```
vous tapez      je sais pas si sa va marcher
vous obtenez    je sais pas si ça va marcher
```

La correction attend le mot suivant quand elle en a besoin : `sa` reste `sa`
tant que rien ne prouve que c'est un `ça`. C'est la phrase qui tranche, pas le
mot isolé.

**Retour arrière annule la dernière correction.** Appuyez dessus juste après
qu'elle soit arrivée, et le mot d'origine revient — exactement comme sur un
clavier de téléphone. Rien à apprendre. `Ctrl+Alt+Z` fait la même chose plus
tard, quand vous avez continué à écrire.

Le mot rétabli vous est ensuite proposé dans *Mon dictionnaire*. Et si vous
refusez trois fois la même correction sur le même mot, **il l'apprend tout
seul** : il n'y touchera plus jamais.

### Il ne corrige pas partout

Une correction automatique dans un terminal ou un éditeur de code ne rend
service à personne. Papote connaît une vingtaine de programmes où il se tait
d'office — `cmd.exe`, `powershell.exe`, `code.exe`, les IDE JetBrains — et
l'onglet *Applications* laisse compléter la liste.

Le plus rapide : clic droit sur l'icône → **Ne plus corriger dans…**, qui
propose le programme où vous veniez d'écrire.

### Il corrige aussi à la demande

Pour un texte déjà écrit — un message collé, un vieux brouillon :
sélectionnez-le et appuyez sur **`Ctrl+Alt+C`**. Le texte corrigé remplace la
sélection.

### Il relit avant d'appliquer, si vous le demandez

Pour un message qui compte, `Ctrl+Alt+R` sur la sélection ouvre la relecture :
chaque correction proposée s'affiche avec sa case, l'aperçu suit vos choix, et
le résultat part dans le presse-papiers — à vous de le coller.

### Il a une fenêtre

Clic droit sur l'icône → *Ouvrir la fenêtre*, `Ctrl+Alt+F`, ou double-clic sur
l'icône. Cinq onglets :

| Onglet | À quoi il sert |
|---|---|
| **Corriger** | Coller un texte, `Ctrl+Entrée`, relire avant d'envoyer. Les mots inconnus s'affichent en dessous : un clic les ajoute à votre dictionnaire. |
| **Mon dictionnaire** | Les mots à ne jamais corriger, et vos remplacements. |
| **Vos fautes** | Ce que vous corrigez le plus, compté sur votre machine. |
| **Applications** | Où se taire, et où hausser le ton. |
| **Réglages** | Tout ce qui se réglait dans un fichier JSON, plus le journal des erreurs. |

## Lui apprendre vos mots

Deux listes, dans l'onglet *Mon dictionnaire* :

**Les mots à ne pas corriger** — pseudos, jargon, noms de jeux. `Kayn`,
`Valorant`, votre pseudo. Trois façons de les ajouter : le bouton sous le texte
corrigé, la proposition qui suit un `Ctrl+Alt+Z`, ou le champ de saisie.

**Vos remplacements** — ce que vous écrivez, et ce qu'il faut écrire à la
place :

| Vous tapez | Il écrit |
|---|---|
| `ptetre` | `peut-être` |
| `jsui` | `je suis` |
| `cdlt` | `cordialement` |
| `adr` | `12 rue des Lilas, 75011 Paris` |

Ils passent avant tout le reste — avant le dictionnaire, avant les protections.
C'est donc aussi un outil d'abréviations : rien n'oblige le remplacement à
corriger une faute.

## Deux registres

Par défaut Papote écrit comme vous parlez. Mais une lettre de motivation n'est
pas un message Discord, alors il sait aussi hausser le ton :

| Vous écrivez | Parlé *(défaut)* | Soutenu |
|---|---|---|
| `j'ai pas compris` | `j'ai pas compris` | `Je n'ai pas compris.` |
| `y a personne` | `y a personne` | `Il n'y a personne.` |
| `faut pas exagérer` | `faut pas exagérer` | `Il ne faut pas exagérer.` |
| `on a pas le temps` | `on a pas le temps` | `On n'a pas le temps.` |
| `dsl bcp de travail` | `dsl bcp de travail` | `Désolé beaucoup de travail.` |
| `ça marche` | `ça marche` | `Cela marche.` |

Le registre soutenu remet les `ne` de négation, rétablit les sujets
impersonnels, déplie les abréviations, et impose la majuscule et le point
final.

Il se règle globalement, ou **application par application** : soutenu dans
Outlook, parlé sur Discord. Onglet *Applications*.

## Vos fautes

L'onglet *Vos fautes* montre ce que vous corrigez le plus :

```
  47 fois   sa → ça
  23 fois   malgres → malgré
  12 fois   jai → j'ai
```

Tout est compté **sur votre machine et nulle part ailleurs**, dans
`%APPDATA%\Papote\apprentissage.json`. Un bouton efface l'historique. Ce
fichier contient des mots que vous avez écrits : c'est le prix de
l'apprentissage, et c'est pourquoi il s'efface aussi facilement.

C'est aussi ce qui permet à Papote d'apprendre : trois annulations sur le même
mot et il ne le corrige plus, trois annulations sur la même règle et il propose
de l'éteindre.

## Réglages

Onglet *Réglages* de la fenêtre. Tout y est, plus besoin d'éditer quoi que ce
soit à la main.

| Réglage | Par défaut | Rôle |
|---|---|---|
| Corriger pendant que j'écris | activé | La correction au fil de la frappe |
| Recoller le texte corrigé | activé | Sinon `Ctrl+Alt+C` se contente du presse-papiers |
| Notifications | activé | Le résumé des corrections près de l'horloge |
| Apprendre de mes annulations | activé | Trois refus et il cède |
| Typographie française | désactivé | `…`, guillemets `« »`, espaces insécables |
| Majuscule en début de phrase | désactivé | Beaucoup tiennent au tout-minuscules |
| Point final manquant | désactivé | Même raison |
| Registre par défaut | parlé | Voir plus haut |
| Lancer au démarrage de Windows | — | Sans droits administrateur |
| Mises à jour automatiques | activé | Voir plus bas |

### Les raccourcis

Trois raccourcis, tous personnalisables. Cliquez sur le bouton, **appuyez sur
la combinaison voulue** : pas besoin de deviner comment elle s'écrit. Échap
annule la saisie, Retour arrière supprime le raccourci.

| Raccourci | Par défaut | Rôle |
|---|---|---|
| Corriger la sélection | `Ctrl+Alt+C` | Corrige le texte sélectionné |
| Annuler la dernière correction | `Ctrl+Alt+Z` | Remet ce que vous aviez écrit |
| Relire avant de corriger | `Ctrl+Alt+R` | Montre les corrections, une par une |
| Ouvrir la fenêtre | `Ctrl+Alt+F` | — |

Une touche seule est refusée : elle partirait chaque fois que vous l'écrivez.
Les touches de fonction (`F1` à `F12`) font exception, elles ne servent à rien
d'autre.

Le fichier reste lisible dans `%APPDATA%\Papote\config.json` si vous y
tenez ; l'application le relit toute seule dans les deux secondes.

## Mises à jour

L'outil va chercher tout seul les nouvelles versions : au lancement, puis une
fois par jour. Quand il en trouve une, il la télécharge en arrière-plan et
**elle prend la place de l'ancienne au démarrage suivant** — jamais pendant
que vous écrivez. Remplacer un exécutable sous les doigts de quelqu'un est le
plus sûr moyen de lui faire perdre sa phrase.

Dès qu'une version est prête, **un bouton « Redémarrer » apparaît** — dans les
réglages, et en bas de la colonne de gauche quelle que soit la page où vous
êtes. Un clic, Papote se relance, la nouvelle version prend la place. Le clic
droit sur l'icône propose la même chose.

Le téléchargement ne vient que des [Releases de ce
dépôt](../../releases), en HTTPS, et l'empreinte SHA-256 publiée par GitHub
est vérifiée quand elle est présente. Rien d'autre n'est envoyé ni reçu : la
requête ne contient que le numéro de version installée.

Pour tout couper : décochez *Chercher les nouvelles versions automatiquement*.

## Quand quelque chose ne va pas

`Papote.exe` n'a pas de console : sans journal, un message d'erreur disparaît
avec lui. Tout ce qui se passe mal est donc noté dans
`%APPDATA%\Papote\journal.log`, avec la pile d'appels quand il y en a une.

*Réglages → Quand quelque chose ne va pas* permet de l'ouvrir, de le copier
d'un clic — pour le coller dans un rapport de bug — ou de l'effacer. Rien n'en
sort tout seul : le fichier reste sur votre machine.

En ligne de commande : `Papote.exe --journal`.

## Ce que l'outil ne touche jamais

- Le registre parlé : négations sans « ne », `y a`, `faut que`, `ça`, `c'est quoi`
- Ce que vous tapez dans un raccourci clavier : dès qu'une touche de commande
  est enfoncée, la phrase en cours est oubliée
- Les liens, adresses e-mail, mentions `@pseudo`, salons `#general`
- Les blocs de code entre backticks et les spoilers `||...||`
- Les emojis `:joy:` et les emojis Discord personnalisés
- L'emphase volontaire : `ouiiii`, `mdrrrr`, `nooon`
- L'argot d'Internet : `dsl`, `tkt`, `jsp`, `wsh`, `askip`… (~150 mots)
- Les mots anglais courants : `the game`, `check this out` (~380 mots)
- Les sigles en capitales, les noms propres et tout mot contenant un chiffre

## Comment ça marche

Aucune bibliothèque de correction, aucun serveur : le moteur tient dans
quelques fichiers Python et un dictionnaire.

| Couche | Fichier | Rôle |
|---|---|---|
| Où et comment | `papote/politique.py` | Se taire ici, hausser le ton là |
| Vos remplacements | `papote/config.py` | Ce que vous lui avez appris passe avant tout |
| Protection | `papote/regles.py` | Ce qui sort du circuit avant examen |
| Grammaire | `papote/grammaire.py` | 51 règles de contexte : homonymes, accords, conjugaison |
| Morphologie | `papote/morphologie.py` | Ce qu'est chaque mot : personne, nombre, genre |
| Genre des noms | `papote/genres.py` | Ce que le dictionnaire ne dit pas |
| Orthographe | `papote/lexique.py` | 450 000 formes françaises, accents et fautes de frappe |
| Frappe | `papote/frappe.py` | Suit ce que vous tapez et décide quand intervenir |

### La correction au fil de la frappe

Tout repose sur une chose : savoir exactement ce qui est à l'écran. L'outil
retient la phrase en cours, et chaque fois qu'un mot se termine, il soumet la
phrase entière au correcteur. S'il faut changer quelque chose, il efface
exactement ce qu'il a écrit et le retape.

La règle qui gouverne le reste : **au moindre doute, il oublie la phrase**. Une
touche qu'il ne sait pas interpréter, un accent circonflexe composé en deux
touches, une flèche, un clic ailleurs, cinq secondes de silence — et le tampon
repart de zéro. Une correction manquée ne se voit pas ; une correction
appliquée au mauvais endroit détruit le texte.

Rien de ce qui est tapé n'est conservé : le tampon vit en mémoire, quelques
centaines de caractères, et rien n'en sort — ni fichier, ni réseau. Dès qu'une
touche de commande est enfoncée, il s'efface.


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
`sa va`, `ils on mangé`, `j'ai manger`. Cinquante et une règles regardent les mots
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
| `les gens pense` → `les gens pensent` | `ces quelques minutes ont suffi` |
| `tu vas ou` → `tu vas où` | `café ou thé` |
| `il a du partir` → `il a dû partir` | `il a du pain` |
| `je suis sur de moi` → `sûr` | `je suis sur la route` |
| `ces pas grave` → `c'est pas grave` | `ses pas résonnaient` |
| `les gens finit` → `les gens finissent` | `les chiens court vite` |
| `ils vient demain` → `ils viennent` | `ce sont des choses qui arrivent` |
| `les bijou` → `les bijoux` | `la souris est cassée` |
| `ils ont prit` → `ils ont pris` | `le prix est correct` |
| `nous somme en retard` → `nous sommes` | `nous sommes allés à la plage` |
| `des voitures rouge` → `rouges` | `il se lave les mains avant de manger` |
| `si j'aurais su` → `si j'avais su` | `je serais ravi de t'aider` |
| `ils se sont trompé` → `trompés` | `elles se sont écrit` |

### La morphologie

Longtemps, les accords se sont faits en devinant. Le pluriel d'un nom, c'était
« ajoute un *s*, sauf en *-al* et en *-eau* » — ce qui rate `bijoux`. Le pluriel
d'un verbe, c'était « retire le *-er* et mets *-ent* » — ce qui ne voyait qu'un
verbe sur six. Et « ce mot finit par un *s*, donc c'est un pluriel » prenait
`le temps`, `la souris` et `le prix` pour des pluriels.

Tout cela est pourtant écrit dans le dictionnaire Hunspell, sous les drapeaux
qui décrivent les paradigmes. `outils/morphologie_hunspell.py` l'en extrait par
deux signes que Dicollecte y a laissés :

- **les élisions.** Chaque règle indique ce qui peut la précéder, et cette liste
  est une empreinte de la personne. `j'` ne précède qu'une première personne,
  `s'` qu'une troisième ; `m'` manque devant un `nous`, `t'` devant un `vous`,
  `q'` devant un impératif ;
- **le `L'`.** Du côté des noms, il marque les formes qui acceptent l'article
  élidé. Or `l'` ne précède qu'un singulier : `l'affiche` se dit, `l'affiches`
  non. Le drapeau donne donc le nombre, sans exception.

Reste l'ordre des règles, qui se lit tout seul : le français se conjugue
toujours dans le même sens — je, tu, il, nous, vous, ils — et un créneau placé
juste après un `vous` est forcément un pluriel. C'est ce qui distingue
`il vient` de `ils viennent`, que la terminaison ne distingue pas.

Il en sort deux tables, 186 000 formes et 26 000 paradigmes, que Papote consulte
par dichotomie sans rien construire au démarrage :

```
pensent   3p             penser
affiche   1s,3s,i2s,xs   affiche afficher
```

Le paradigme d'un verbe arrive **découpé par temps**, et c'est ce qui permet
d'accorder sans déplacer : dans `les gens finit`, on cherche la troisième
personne du pluriel *dans le temps de `finit`*, ce qui donne `finissent` et non
`finirent` — un passé simple parfaitement correct, mais hors sujet.

### Le genre des noms

Le dictionnaire ne le dit pas. Il connaît celui des paradigmes à deux genres
— `chat` / `chatte` —, pas celui de `voiture` ni de `cheval`. Tant que
l'accord se faisait au masculin par défaut, `des voitures blanc` devenait
`des voitures blancs` : pas une faute laissée, une faute **écrite**.

`papote/genres.py` le reconstitue par trois voies, et assume la quatrième :

| | |
|---|---|
| **la phrase** | `la porte est ouvert` → le déterminant porte déjà le genre |
| **la terminaison** | `-tion`, `-ité`, `-esse` sont féminins sans exception ; `-ment`, `-isme`, `-oir` masculins. Chacune vient avec ses exceptions nommées : `jument`, `silence`, `eau`, `peau` |
| **une liste** | les noms courts et courants qu'aucune règle ne couvre : `eau`, `nuit`, `main`, `jour` |
| **rien** | et alors on se tait |

Se taire est la partie qui compte. Un nom dont le genre reste inconnu ne fait
pas accorder un adjectif dont le masculin et le féminin diffèrent :

```
des voitures blanc   ->  des voitures blanches   (« voiture » est dans la liste)
des trucs blanc      ->  des trucs blanc         (« truc », on ne sait pas)
des trucs rouge      ->  des trucs rouges        (« rouge » ne change pas)
```

Les mots qui changent de sens avec leur genre — `le livre` et `la livre`,
`le poste` et `la poste` — ne figurent nulle part : une table à une colonne
se tromperait une fois sur deux.


Le principe, partout : **mieux vaut sous-corriger que corrompre**. Un message
qui garde une faute reste lisible ; un message mal corrigé ne l'est plus.

### Mesurer plutôt que croire

Un correcteur ne se juge pas sur ses règles mais sur ses résultats. Le corpus
d'évaluation tient dans `outils/evaluer.py` : des phrases fautives avec leur
correction attendue, et des phrases correctes qui doivent ressortir intactes.

```
python outils/evaluer.py --detail

  categorie        corrigees
  accent           10/10  ██████████
  accord           22/22  ██████████████████████
  apostrophe        7/7   ███████
  conjugaison      32/32  ████████████████████████████████
  frappe            2/2   ██
  homophone        24/24  ████████████████████████

  RAPPEL      97/97  (100 %)   fautes attrapees
  PRECISION  130/130  (100 %)   phrases correctes laissees tranquilles
```

La précision est le seuil dur, et la suite de tests le défend :
`tests/test_qualite.py` échoue dès qu'**une seule** phrase correcte est abîmée.
Une faute laissée passer se remarque à peine ; une phrase juste corrompue se
voit tout de suite.

Les phrases du corpus n'ont pas été choisies pour flatter l'outil : elles ont
été écrites en trois vagues, chacune à l'aveugle, et chaque vague a trouvé des
dégradations que la précédente ne voyait pas — `il n'y à plus rien`,
`nous sommons allés`, `ces quelques minutent`. Ce sont elles qui ont dicté les
garde-fous.

## En ligne de commande

```
Papote.exe --texte "je sais pas si sa va marcher"
Papote.exe --fenetre        # ouvre la fenêtre de correction
Papote.exe --verifier       # contrôle dictionnaire, correction et réglages
Papote.exe --maj            # cherche une nouvelle version et la télécharge
Papote.exe --demarrage on   # se lance avec Windows (on/off/etat)
Papote.exe --console        # sans icône, journal en console
Papote.exe --config         # chemin du fichier de réglages
```

`--verifier` est le premier réflexe si quelque chose ne fonctionne pas.

Ces commandes écrivent dans le terminal qui les a lancées. Lancé d'un
double-clic, `Papote.exe` n'affiche rien et se contente d'apparaître près
de l'horloge : c'est une application de zone de notification, pas un
programme en ligne de commande.

Depuis les sources, remplacez `Papote.exe` par `python -m papote`.

## Développement

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q          # ~360 tests, moins d'une seconde
python outils/evaluer.py           # la qualité du correcteur, en chiffres
python -m papote --texte "sa va ?"
```

Sous Windows, `installer.bat` prépare l'environnement et `Papote.vbs`
lance l'outil sans fenêtre noire.

### Fabriquer l'exécutable

```
construire_exe.bat
```

Le résultat est `dist\Papote.exe` : un fichier unique d'une vingtaine de
mégaoctets, dictionnaire compris.

L'installateur, lui, se construit avec [WiX](https://wixtoolset.org/) à partir
de `installateur/papote.wxs` — c'est ce que fait GitHub à chaque envoi. Ses
images ne sont pas versionnées : elles se redessinent à partir des icônes du
programme.

```
python outils/images_installateur.py
wix build installateur/papote.wxs -d Version=1.0.0 -bindpath dist -bindpath installateur -ext WixToolset.UI.wixext -culture fr-FR -out dist/Papote.msi
```

C'est aussi ce que fait GitHub à chaque envoi, sur n'importe quelle branche
([`.github/workflows/executable.yml`](.github/workflows/executable.yml)) :
l'exécutable est construit sur une machine Windows, testé, puis déposé dans
l'onglet *Actions*.

Sur `main`, il est en plus publié dans les *Releases*, sous un numéro calculé
tout seul : `majeur.mineur` vient de `SERIE` dans `papote/__init__.py`, le
dernier nombre est le nombre de commits. Chaque envoi donne donc une version
de plus, sans jamais retomber sur la même, et il n'y a aucun tag à poser à la
main. Pour ouvrir une nouvelle série — `v1.1.x` — il suffit de changer `SERIE`.

Le numéro est inscrit dans le code avant la compilation
(`papote/version_compilee.py`, ignoré par git) : c'est ainsi que
l'exécutable sait, plus tard, qu'une version plus récente est parue.

### Les icônes

Elles sont en pixel art, et se lisent dans le code : chaque icône est une
grille de caractères, chaque caractère un pixel.

```python
"papote": _grille("""
....########....
..############..
.####++++++####.
.##############.
.#.oo..oo..oo.#.
...
""")
```

Le rendu se fait à l'agrandissement entier, sans lissage, pour que le trait
reste net à toutes les tailles. Rien ne dépend de Pillow côté fenêtre :
`tkinter.PhotoImage` sait poser des pixels un par un.

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
| `papote/lexique.py` | Dictionnaire, candidats, décision |
| `papote/grammaire.py` | Règles de contexte |
| `papote/regles.py` | Mots et motifs protégés, règles optionnelles |
| `papote/moteur.py` | Assemblage des trois couches |
| `papote/app.py` | Enchaînement sélection → correction → collage |
| `papote/presse_papier.py` | Capture de la sélection via le presse-papiers |
| `papote/interface.py` | Icône dans la zone de notification |
| `papote/fenetre.py` | Fenêtre : corriger, dictionnaire, réglages (tkinter) |
| `papote/theme.py` | Couleurs, espacements, widgets dessinés |
| `papote/icones.py` | Les icônes, en pixel art |
| `papote/journal.py` | Le journal des erreurs |
| `papote/couleurs.py` | La palette, sans dépendance |
| `papote/frappe.py` | Correction au fil de la frappe et annulation |
| `papote/politique.py` | Où corriger, et sur quel ton |
| `papote/apprentissage.py` | Ce qu'il retient de vos habitudes |
| `papote/relecture.py` | Comparaison des deux textes, correction par correction |
| `papote/maj.py` | Recherche, téléchargement et mise en place des versions |
| `papote/raccourci.py` | Raccourcis globaux et lecture des combinaisons |
| `papote/config.py` | Lecture, migration et écriture des réglages |
| `papote/demarrage.py` | Lancement automatique via le registre Windows |
| `papote/chemins.py` | Emplacements selon le mode (sources, `.exe`) |
| `outils/construire_lexique.py` | Fabrication des fichiers de `donnees/` |
| `outils/evaluer.py` | Le corpus d'évaluation et son tableau de bord |
| `outils/images_installateur.py` | L'icône et les images de l'installateur |
| `installateur/papote.wxs` | La recette de l'installateur MSI |
