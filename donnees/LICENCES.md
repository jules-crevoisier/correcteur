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

## `frequences_fr.txt.gz` — les 48 000 mots les plus employés

Ordre de fréquence extrait de [wordfreq](https://github.com/rspeer/wordfreq)
(Robyn Speer), sous licence **Apache 2.0**, puis filtré par le dictionnaire
ci-dessus. Le fichier ne contient que des mots, dans l'ordre du plus courant au
plus rare : il sert à départager deux corrections également plausibles.

## Le reste du projet

Le code du correcteur ne dépend d'aucune bibliothèque de correction : tout ce
qui lit ces fichiers est écrit dans ce dépôt, en Python, avec la bibliothèque
standard.
