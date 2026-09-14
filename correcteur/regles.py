# -*- coding: utf-8 -*-
"""Politique de correction : ce qu'on corrige, ce qu'on laisse tranquille.

Le principe directeur : on corrige les *fautes*, jamais le *registre*.
« j'ai pas » est du français parlé correct, pas une erreur. LanguageTool,
comme Reverso, applique par défaut les normes du francais ecrit soutenu ;
tout ce module sert a desactiver cette couche-la.
"""

# ---------------------------------------------------------------------------
# Categories entierement ecartees.
#
# Ces categories de LanguageTool ne signalent pas des fautes mais des ecarts
# par rapport au francais formel : familiarites, anglicismes, regionalismes,
# repetitions stylistiques. Sur un message Discord, elles n'ont aucun sens.
# ---------------------------------------------------------------------------
CATEGORIES_IGNOREES = {
    # « y a », « c'est eux qu'ont fait », « parle-moi pas »... 
    # Cette categorie est presque integralement du maintien de registre.
    "CAT_TOURS_CRITIQUES",
    # « totalement » -> « completement », « ca sera » -> « cela sera »...
    "STYLE",
    # « tres tres » signale comme familier.
    "REPETITIONS_STYLE",
    # « dispo » -> « disponible », « c'est quoi » -> « qu'est-ce que »...
    "CAT_REGLES_DE_BASE",
    # Pleonasmes : question de style, pas d'orthographe.
    "CAT_PLEONASMES",
    # « smooth », « momentum »... on ne fait pas la police de l'anglicisme.
    "CAT_ANGLICISMES_FOREIGN_TERMS",
    "CAT_CALQUES",
    # Regionalismes et archaismes : ce n'est pas une faute d'ecrire « cenne ».
    "CAT_REGIONALISMES",
    "CAT_ARCHAISMES",
    # Marques de commerce : « frigo » -> « refrigerateur ». Non.
    "CAT_MARQUES_DE_COMMERCE",
    # Coherence semantique : trop de faux positifs sur du texte court.
    "SEMANTICS",
    # Ponctuation stylistique (virgules « manquantes », etc.).
    "PONCTUATION_VIRGULE",
    "PONCTUATION_STYLE_OS",
}

# ---------------------------------------------------------------------------
# Regles ecartees une par une.
#
# Celles-ci vivent dans des categories qu'on veut garder (la grammaire, la
# typographie) mais qui imposent malgre tout le registre soutenu.
# ---------------------------------------------------------------------------
REGLES_IGNOREES = {
    # LE coupable principal : « j'ai pas » -> « je n'ai pas ».
    # C'est exactement le comportement que Reverso impose.
    "P_V_PAS",
    # « faut que j'y aille » -> « il faut que j'y aille ».
    "IL_FAUT",
    # « c'est pas grave » -> « ce n'est pas grave ».
    "NE_IMP_PAS",
    # « y a » -> « il y a » (doublon de CAT_TOURS_CRITIQUES, par securite).
    "IL_Y_A",
    "Y_APOSTROPHE",
    "Y_EN_A",
    "Y_DOIVENT",
    "Y_A",
    "Y_AVAIT",
    # Negations partielles : meme logique que P_V_PAS.
    "NEGATION_PLUS",
    "NEGATION_QUE",
    "NEGATION_PERSONNE",
    "NEGATION_NULLE_PART",
    "ON_N_A",
    # « je m'excuse » -> « excusez-moi » : lecon de politesse, pas une faute.
    "JE_M_EXCUSE",
    # Abreviations jugees familieres.
    "DET_ABREGE",
    "QQ",
    "WE",
    "DISPO",
    # Structures interrogatives orales : « tu viens ? », « c'est quoi ? ».
    "QUESTION_REGISTRE_SOUTENU",
    "QU_EST_CE_QUE",
    "QUOI_VERBE_INTERROGATION",
    "QUOI_FAIRE",
    "POSER_UNE_QUESTION",
    "C_EST_QUOI",
    # « ca » juge familier face a « cela ».
    "CA_CE",
    # Mots repetes pour l'emphase : « non non non », « tres tres bien ».
    "FRENCH_WORD_REPEAT_RULE",
    "REP_TRES",
    "REP_OUI",
    "REP_NON",
    "REP_JUSTE",
    # « tas » pour « t'as ».
    "CONFUSION_TU_AS",
    "BARBARISME_TU",
    # Espaces insecables avant ? ! : ; — corrects en typographie francaise
    # mais ils s'affichent mal sur Discord et cassent parfois le collage.
    "UNPAIRED_BRACKETS",
    "FRENCH_WHITESPACE",
    "FRENCH_WHITESPACE_STRICT",
}

# Regles desactivees par defaut mais que l'utilisateur peut reactiver
# depuis la configuration (cle « regles_optionnelles »).
REGLES_OPTIONNELLES = {
    # Met une majuscule en debut de phrase. Propre, mais certains preferent
    # garder leur style tout-minuscules sur Discord.
    "UPPERCASE_SENTENCE_START": False,
    # Ajoute le point final manquant.
    "PONCTUATION_POINT": False,
}

# ---------------------------------------------------------------------------
# Lexique a proteger.
#
# LanguageTool ne connait pas l'argot d'Internet et propose des remplacements
# absurdes : « dsl » -> « ADSL », « mdr » -> « mdr » introuvable, etc.
# Tout mot de cette liste est immunise contre les regles d'orthographe.
# ---------------------------------------------------------------------------
LEXIQUE_PROTEGE = {
    # Abreviations courantes
    "dsl", "mdr", "ptdr", "lol", "tkt", "tqt", "jsp", "jpp", "slt", "bjr",
    "bsr", "stp", "svp", "pk", "pq", "pcq", "prsq", "cad", "bcp", "tjr",
    "tjrs", "qqn", "qqch", "rdv", "nrv", "dcd", "dac", "oki", "jvb", "vrmt",
    "jms", "srx", "tfq", "ct", "cv", "mrc", "bnj", "tt", "ms", "ds", "pr",
    "auj", "ajd", "bref", "askip", "apparement",
    # Interjections et argot
    "wsh", "wesh", "frr", "frero", "frere", "gros", "zbeul", "ouf", "relou",
    "chelou", "meuf", "keuf", "reuf", "teuf", "bail", "bails", "sah",
    "wallah", "khey", "chanmé", "chanme", "vener", "nickel", "grave",
    "carrement", "franchement", "genre", "trop", "chaud", "zarb",
    # Vocabulaire en ligne / gaming
    "screen", "screenshot", "stream", "streamer", "chill", "spoil", "spoiler",
    "ping", "afk", "brb", "gg", "wp", "ez", "irl", "rip", "noob", "smurf",
    "tryhard", "clutch", "nerf", "buff", "lag", "ragequit", "gameplay",
    "cringe", "based", "ratio", "hype", "troll", "spam", "dm", "mp", "vocal",
    "serv", "serveur", "bot", "pseudo", "pfp", "banni", "kick", "mute",
    # Plateformes et marques
    "discord", "twitch", "youtube", "tiktok", "insta", "snap", "whatsapp",
    "telegram", "steam", "spotify", "netflix", "reddit", "twitter",
    # Formes contractees frequentes
    "chuis", "chais", "ouais", "ouaip", "nan", "bah", "ben", "hein", "euh",
    "hmm", "pff", "yes", "yep", "nope", "ok", "okay",
}

# Prefixes/motifs qu'on ne touche jamais, ou qu'on protege integralement.
MOTIFS_PROTEGES = [
    r"https?://\S+",            # liens
    r"www\.\S+",                # liens sans schema
    r"\b\S+@\S+\.\S+\b",        # adresses e-mail
    r"<@!?\d+>",                # mentions Discord
    r"<#\d+>",                  # salons Discord
    r"<a?:\w+:\d+>",            # emojis personnalises Discord
    r":[a-z0-9_+-]+:",          # emojis textuels :joy:
    r"```.*?```",               # blocs de code
    r"`[^`]+`",                 # code inline
    r"\|\|.*?\|\|",             # spoilers Discord
    r"(?<!\w)[@#/]\w+",         # @pseudo, #salon, /commande
    r"\b\w*\d\w*\b",            # tout mot contenant un chiffre
]
