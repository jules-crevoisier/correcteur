# Origine et licences des données

Ces fichiers sont les seules données du correcteur. Ils sont produits par
`outils/construire_lexique.py`, qui ne sert qu'à les régénérer : l'application,
elle, se contente de les lire.

## `fr.dic`, `fr.aff` — dictionnaire Hunspell français

*Dictionnaires orthographiques français*, version 7.5, par Olivier R. et les
contributeurs de Dicollecte — <https://grammalecte.net/>.

Licence **MPL 2.0** (Mozilla Public License) : <https://www.mozilla.org/MPL/2.0/>.

C'est le dictionnaire employé par LibreOffice, Firefox et Thunderbird. Il est
livré tel quel, sans modification.

## `lexique_fr.txt.gz` — 450 000 formes fléchies

Développement des radicaux et des affixes de `fr.dic` / `fr.aff`, groupé par
graphie sans accents. Œuvre dérivée du dictionnaire ci-dessus, donc **MPL 2.0**
elle aussi.

## `analyses_fr.txt.gz`, `flexions_fr.txt.gz` — la morphologie

Ce qu'est chaque forme — personne, nombre, genre — et le paradigme dont elle
vient. Lu dans les drapeaux de `fr.dic` / `fr.aff` par
`outils/morphologie_hunspell.py`, qui explique comment. Œuvre dérivée du
dictionnaire ci-dessus, donc **MPL 2.0** elle aussi.

## `frequences_fr.txt.gz` — les 48 000 mots les plus employés

Ordre de fréquence extrait de [wordfreq](https://github.com/rspeer/wordfreq)
(Robyn Speer), sous licence **Apache 2.0**, puis filtré par le dictionnaire
ci-dessus. Le fichier ne contient que des mots, dans l'ordre du plus courant au
plus rare : il sert à départager deux corrections également plausibles.

## `modele_fr.bin.gz` — le modèle statistique des homophones

Des empreintes de contextes (deux mots de chaque côté de « a/à », « ou/où »,
« son/sont »… et des formes en [e] des verbes du premier groupe) et le nombre
de fois où chacun a été vu. Aucune phrase n'y figure : seulement des comptes,
sous forme d'empreintes CRC32 non réversibles. Fabriqué par
`outils/entrainer_modele.py` à partir de :

| Corpus | Licence | Mots |
|---|---|---|
| [Mozilla Common Voice](https://github.com/common-voice/common-voice), phrases françaises | CC0 | 15 M |
| [Tatoeba](https://tatoeba.org), phrases françaises | CC-BY 2.0 France — © les contributeurs de tatoeba.org | 1,4 M |
| [ELTeC-fra](https://github.com/COST-ELTeC/ELTeC-fra), 100 romans 1840–1920 | textes du domaine public, encodage CC-BY 4.0 (COST Action CA16204) | 8 M |
| [Europarl v7](https://www.statmt.org/europarl/), débats du Parlement européen | réutilisation libre avec mention de la source (Koehn, 2005) | 51 M |

Les comptes sont une œuvre dérivée de ces corpus ; leurs licences autorisent
cette réutilisation avec attribution, faite ici.

## Le reste du projet

Le code du correcteur ne dépend d'aucune bibliothèque de correction : tout ce
qui lit ces fichiers est écrit dans ce dépôt, en Python, avec la bibliothèque
standard.
