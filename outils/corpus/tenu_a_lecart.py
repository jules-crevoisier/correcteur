# -*- coding: utf-8 -*-
"""Le corpus tenu a l'ecart : celui qu'on ne regarde pas.

Un correcteur mis au point sur les phrases qui le notent finit par les
apprendre par coeur. Le corpus de developpement affichait 100 % dans les
deux sens, et quarante phrases ordinaires prises au hasard en cassaient
trente-deux : le chiffre ne mesurait rien.

Ces phrases-ci ont ete ecrites d'un trait, sans les faire passer par le
correcteur, et elles ne servent qu'a le noter. La regle qui va avec :

    on ne corrige jamais une regle « parce qu'elle rate telle phrase d'ici ».

Ce qu'on a le droit de lire, c'est le score par categorie. Le detail des
echecs reste sous enveloppe : `--ouvrir-l-enveloppe` l'affiche, et ce jour-la
le corpus est brule — il faut en ecrire un autre.

Quand une categorie stagne, la marche a suivre est d'ecrire *de nouvelles*
phrases de cette categorie dans le corpus de developpement, et de travailler
dessus. Le tenu a l'ecart ne bouge pas.
"""

# (texte fautif, texte attendu, categorie)
FAUTES = [
    # -- accents oublies -----------------------------------------------------
    ("on se voit a quelle heure", "on se voit à quelle heure", "accent"),
    ("j'ai recu ton colis ce matin", "j'ai reçu ton colis ce matin", "accent"),
    ("c'est la meme chose", "c'est la même chose", "accent"),
    ("il est rentre tard hier soir", "il est rentré tard hier soir", "accent"),
    ("une soiree tranquille", "une soirée tranquille", "accent"),
    ("le diner est pret", "le dîner est prêt", "accent"),
    ("elle a prefere rester", "elle a préféré rester", "accent"),
    ("un evenement important", "un événement important", "accent"),
    ("la verite c'est que j'ai oublie", "la vérité c'est que j'ai oublié", "accent"),
    ("tu m'as manque", "tu m'as manqué", "accent"),
    ("j'ai telephone deux fois", "j'ai téléphoné deux fois", "accent"),
    ("des que possible", "dès que possible", "accent"),
    ("ou est passe mon telephone", "où est passé mon téléphone", "accent"),
    ("c'est deja fini", "c'est déjà fini", "accent"),
    ("il fait tres froid dehors", "il fait très froid dehors", "accent"),

    # -- apostrophes sautees -------------------------------------------------
    ("jarrive dans cinq minutes", "j'arrive dans cinq minutes", "apostrophe"),
    ("jespere que ca ira", "j'espère que ça ira", "apostrophe"),
    ("lhopital est loin", "l'hôpital est loin", "apostrophe"),
    ("sil te plait repond moi", "s'il te plaît répond moi", "apostrophe"),
    ("je pense quon devrait partir", "je pense qu'on devrait partir", "apostrophe"),
    ("cetait une bonne idee", "c'était une bonne idée", "apostrophe"),
    ("dabord on mange", "d'abord on mange", "apostrophe"),
    ("il ma rappele hier", "il m'a rappelé hier", "apostrophe"),
    ("lannee prochaine je demenage", "l'année prochaine je déménage", "apostrophe"),

    # -- fautes de frappe ----------------------------------------------------
    ("je suis en retrad", "je suis en retard", "frappe"),
    ("c'est increyable", "c'est incroyable", "frappe"),
    ("une petite quesiton", "une petite question", "frappe"),
    ("le rendz-vous est annule", "le rendez-vous est annulé", "frappe"),
    ("tu as raisno", "tu as raison", "frappe"),
    ("bonojur tout le monde", "bonjour tout le monde", "frappe"),
    ("merci beacoup", "merci beaucoup", "frappe"),
    ("un probelme technique", "un problème technique", "frappe"),

    # -- homophones grammaticaux ---------------------------------------------
    ("sa m'enerve un peu", "ça m'énerve un peu", "homophone"),
    ("il a dit quil viendra", "il a dit qu'il viendra", "homophone"),
    ("elle ce demande pourquoi", "elle se demande pourquoi", "homophone"),
    ("je c'est pas quoi dire", "je sais pas quoi dire", "homophone"),
    ("tout les matins c'est pareil", "tous les matins c'est pareil", "homophone"),
    ("il et vraiment sympa", "il est vraiment sympa", "homophone"),
    ("ils on tout mange", "ils ont tout mangé", "homophone"),
    ("elles son deja la", "elles sont déjà là", "homophone"),
    ("ou est ce que tu vas", "où est-ce que tu vas", "homophone"),
    ("un peut de patience", "un peu de patience", "homophone"),
    ("mes bon, tant pis", "mais bon, tant pis", "homophone"),
    ("je vais a la piscine", "je vais à la piscine", "homophone"),
    ("il à oublie ses cles", "il a oublié ses clés", "homophone"),
    ("ce livre et super", "ce livre est super", "homophone"),
    ("tous le monde attend", "tout le monde attend", "homophone"),
    ("quelque soit ton choix", "quel que soit ton choix", "homophone"),
    ("il s'est ce qu'il veut", "il sait ce qu'il veut", "homophone"),
    ("on c'est vu hier", "on s'est vu hier", "homophone"),
    ("il y'a un souci", "il y a un souci", "homophone"),
    ("j'aurai du partir plus tot", "j'aurais dû partir plus tôt", "homophone"),
    ("ces pas grave", "c'est pas grave", "homophone"),
    ("sur ce point la je suis d'accord", "sur ce point-là je suis d'accord", "homophone"),

    # -- conjugaison ---------------------------------------------------------
    ("je doit y aller", "je dois y aller", "conjugaison"),
    ("tu peut me rappeler", "tu peux me rappeler", "conjugaison"),
    ("il prends son temps", "il prend son temps", "conjugaison"),
    ("nous somme d'accord", "nous sommes d'accord", "conjugaison"),
    ("vous ete sur de vous", "vous êtes sûr de vous", "conjugaison"),
    ("ils viens demain", "ils viennent demain", "conjugaison"),
    ("j'ai oublier mes cles", "j'ai oublié mes clés", "conjugaison"),
    ("il a repondu tout de suite", "il a répondu tout de suite", "conjugaison"),
    ("elle va partir bientot", "elle va partir bientôt", "conjugaison"),
    ("il faut que je fais attention", "il faut que je fasse attention", "conjugaison"),
    ("si j'aurais le temps je viendrais", "si j'avais le temps je viendrais",
     "conjugaison"),
    ("demain je serais chez moi", "demain je serai chez moi", "conjugaison"),
    ("on a bien manger", "on a bien mangé", "conjugaison"),
    ("je vais t'appeler pour t'expliquer", "je vais t'appeler pour t'expliquer",
     "conjugaison"),
    ("tu as bien travailler", "tu as bien travaillé", "conjugaison"),
    ("nous avons fini de manger", "nous avons fini de manger", "conjugaison"),
    ("ils ont pris le train", "ils ont pris le train", "conjugaison"),
    ("je finirai ca demain", "je finirai ça demain", "conjugaison"),

    # -- accord en genre et en nombre ----------------------------------------
    ("j'ai trois chat a la maison", "j'ai trois chats à la maison", "accord"),
    ("les enfant sont rentres", "les enfants sont rentrés", "accord"),
    ("mes ami arrivent ce soir", "mes amis arrivent ce soir", "accord"),
    ("deux heure plus tard", "deux heures plus tard", "accord"),
    ("ma soeur est venu me voir", "ma sœur est venue me voir", "accord"),
    ("elle est parti sans rien dire", "elle est partie sans rien dire", "accord"),
    ("une journee charge", "une journée chargée", "accord"),
    ("elles sont content", "elles sont contentes", "accord"),
    ("les gens son fou", "les gens sont fous", "accord"),
    ("des idee interessantes", "des idées intéressantes", "accord"),
    ("plusieurs personne attendent", "plusieurs personnes attendent", "accord"),
    ("ces dernier jours", "ces derniers jours", "accord"),
    ("nous sommes arrive en retard", "nous sommes arrivés en retard", "accord"),
    ("vous etes venu a deux", "vous êtes venus à deux", "accord"),
    ("leur enfants dorment", "leurs enfants dorment", "accord"),
    ("toute les semaines", "toutes les semaines", "accord"),

    # -- traits d'union ------------------------------------------------------
    ("on prend rendez vous quand", "on prend rendez-vous quand", "trait-union"),
    ("peut etre que je viendrai", "peut-être que je viendrai", "trait-union"),
    ("c'est a dire quoi exactement", "c'est-à-dire quoi exactement", "trait-union"),
    ("qu'est ce que tu fais", "qu'est-ce que tu fais", "trait-union"),
    ("dis moi tout", "dis-moi tout", "trait-union"),
    ("envoie moi le lien", "envoie-moi le lien", "trait-union"),
    ("donne lui son cadeau", "donne-lui son cadeau", "trait-union"),
    ("au dessus de la porte", "au-dessus de la porte", "trait-union"),
    ("vas y doucement", "vas-y doucement", "trait-union"),
    ("il est la bas", "il est là-bas", "trait-union"),

    # -- mots rares qui masquent une faute -----------------------------------
    ("je sui en route", "je suis en route", "mot-rare"),
    ("il fau qu'on parle", "il faut qu'on parle", "mot-rare"),
    ("tou va bien", "tout va bien", "mot-rare"),
    ("j'ai pri le bus", "j'ai pris le bus", "mot-rare"),
    ("on ce voit demain", "on se voit demain", "mot-rare"),

    # -- doublons ------------------------------------------------------------
    ("je vais vais partir", "je vais partir", "doublon"),
    ("c'est le le meilleur", "c'est le meilleur", "doublon"),
    ("on a a fini", "on a fini", "doublon"),
    ("il faut que que tu viennes", "il faut que tu viennes", "doublon"),

    # -- majuscules des noms propres -----------------------------------------
    ("je vais a paris ce week-end", "je vais à Paris ce week-end", "majuscule"),
    ("elle habite en france", "elle habite en France", "majuscule"),
    ("on part pour marseille lundi", "on part pour Marseille lundi", "majuscule"),
]


# Phrases correctes : le correcteur ne doit pas y toucher une lettre. Le
# registre parle en fait partie — « j'ai pas » n'est pas une faute a reparer,
# c'est une facon de parler qu'on a choisi de respecter.
INTOUCHABLES = [
    # -- registre parle, a preserver tel quel --------------------------------
    "j'ai pas le temps ce soir",
    "y'a rien a faire",
    "faut qu'on se voie",
    "je sais pas trop",
    "t'as vu l'heure ?",
    "on se capte demain",
    "c'est chaud ce truc",
    "ça marche, à demain",
    "bon bah tant pis",
    "j'te jure c'est vrai",
    "chui mort de rire",
    "nickel merci beaucoup",
    "ouais carrément",
    "mdr t'es sérieux ?",
    "ok pas de souci",

    # -- phrases ordinaires bien ecrites -------------------------------------
    "Je t'envoie le document dès que je rentre.",
    "On se retrouve devant la gare à midi.",
    "Elle m'a demandé si tu venais aussi.",
    "Il y avait beaucoup de monde au marché.",
    "Les résultats arrivent la semaine prochaine.",
    "Je n'ai pas encore eu le temps de lire ton message.",
    "Tu me diras ce que tu en penses.",
    "Nous avons décidé de reporter la réunion.",
    "Ce restaurant est vraiment très bon.",
    "Mon frère travaille dans une banque.",
    "Il pleut depuis ce matin sans s'arrêter.",
    "Est-ce que quelqu'un a vu mes lunettes ?",
    "Je préfère y aller à pied.",
    "Elles se sont croisées par hasard.",
    "Les enfants ont fini leurs devoirs.",
    "On a passé une excellente soirée.",
    "Il faudrait qu'on en reparle calmement.",
    "Je vous remercie pour votre réponse rapide.",
    "Ça fait plaisir de te revoir.",
    "Le train a eu du retard à cause de la neige.",

    # -- accords deja corrects, souvent abimes par un correcteur -------------
    "Les photos que j'ai prises sont réussies.",
    "La lettre qu'elle a écrite est longue.",
    "Ces quelques jours ont suffi.",
    "Les trois quarts du travail sont faits.",
    "Beaucoup de gens pensent la même chose.",
    "Une partie des invités est déjà partie.",
    "Plus d'un a essayé sans y arriver.",
    "Ni l'un ni l'autre ne viendra.",
    "Tout le monde est content du résultat.",
    "La plupart des gens s'en moquent.",
    "Chacun fait ce qu'il peut.",
    "Aucune de ces solutions ne marche.",
    "Leurs affaires traînent partout.",
    "Leur voiture est en panne.",
    "Quelques minutes suffiront.",
    "Certaines choses ne changent jamais.",

    # -- verbes dont la forme ressemble a une faute --------------------------
    "Nous sommes tous d'accord là-dessus.",
    "Vous êtes arrivés les premiers.",
    "Ils ont eu de la chance ce jour-là.",
    "Elle a fait de son mieux.",
    "Je suis sûr de ce que j'avance.",
    "Il vaut mieux ne rien dire.",
    "Ça ne sert à rien d'insister.",
    "Il s'en veut encore aujourd'hui.",
    "On y va quand tu veux.",
    "Je m'en souviens très bien.",
    "Tu t'en sors comment ?",
    "Elle s'y attendait un peu.",

    # -- noms qui ressemblent a des participes passes ------------------------
    "J'ai une idée derrière la tête.",
    "Il a peur de se tromper.",
    "On a eu chaud sur ce coup-là.",
    "Elle a envie de changer d'air.",
    "Nous avons besoin de ton avis.",
    "Ils ont raison sur toute la ligne.",
    "Tu as tort de t'inquiéter.",
    "J'ai faim, on mange bientôt ?",
    "Il a soif après tout ce sport.",
    "Elle a mal au dos depuis hier.",

    # -- pieges d'homophones deja bien ecrits --------------------------------
    "Je sais ce que tu veux dire.",
    "C'est se demander à quoi ça sert.",
    "Où est-ce que tu as trouvé ça ?",
    "Ou alors on annule tout.",
    "Il est là depuis une heure.",
    "La porte est restée ouverte.",
    "Ses parents sont adorables.",
    "Ces gens-là ne m'inspirent pas.",
    "Tout va bien de ton côté ?",
    "Tous les jours c'est la même chose.",
    "Il peut venir s'il veut.",
    "Un peu de silence ferait du bien.",
    "Mais enfin, qu'est-ce qui t'arrive ?",
    "Mes clés ont encore disparu.",
    "On s'est bien amusés hier soir.",
    "C'est arrivé sans prévenir.",
    "Il a pris son temps pour répondre.",
    "Elle a mis une heure à venir.",

    # -- chiffres, sigles, adresses, code : rien a corriger ------------------
    "Le RDV est à 14h30 au 12 rue des Lilas.",
    "Il travaille à la SNCF depuis 2015.",
    "Envoie ça sur contact@exemple.fr stp.",
    "regarde https://exemple.fr/page?x=1&y=2",
    "lance `npm run build` avant de pousser",
    "le fichier s'appelle rapport_final_v2.pdf",
    "Appelle-moi au 06 12 34 56 78.",
    "C'est écrit noir sur blanc dans le PDF.",

    # -- anglais insere dans du francais -------------------------------------
    "j'ai un call dans dix minutes",
    "on fait un brainstorming demain",
    "c'est vraiment nice comme endroit",
    "je te forward le mail",
    "check tes notifications",
]
