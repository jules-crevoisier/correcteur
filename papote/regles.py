# -*- coding: utf-8 -*-
"""Politique de correction : ce qu'on corrige, ce qu'on laisse tranquille.

Le principe directeur : on corrige les *fautes*, jamais le *registre*.
« j'ai pas » est du français parlé correct, pas une erreur. Reverso et les
correcteurs classiques appliquent les normes du français écrit soutenu ; ce
module et `grammaire.py` s'entendent pour ne jamais le faire.

Concrètement, aucune règle du correcteur ne touche à :

    j'ai pas compris          (la négation parlée, sans « ne »)
    y a personne              (« il y a » réduit à « y a »)
    faut que j'y aille        (le sujet impersonnel omis)
    c'est quoi ce truc        (l'interrogation orale)
    ça marche                 (« ça » n'est pas remplacé par « cela »)
    dispo, frigo, bcp         (les abréviations)
    ouiiii, mdrrrr            (l'emphase)

Ce fichier liste en plus les mots et les motifs auxquels le correcteur ne
doit toucher sous aucun prétexte, et les deux règles de mise en forme qu'il
laisse désactivées par défaut.
"""

# ---------------------------------------------------------------------------
# Regles desactivees par defaut, que l'utilisateur peut activer depuis la
# configuration (cle « regles_optionnelles »).
# ---------------------------------------------------------------------------
REGLES_OPTIONNELLES = {
    # Met une majuscule en debut de phrase. Propre, mais beaucoup de gens
    # tiennent a leur style tout-minuscules sur Discord.
    "MAJUSCULE_PHRASE": False,
    # Ajoute le point final manquant.
    "PONCTUATION_POINT": False,
    # Typographie francaise : « ... » -> « … », guillemets « », espaces
    # insecables. Correct, mais mal rendu par certaines applications.
    "TYPOGRAPHIE": False,
}

# ---------------------------------------------------------------------------
# Abreviations depliees dans le registre soutenu.
#
# Elles ne sont pas des fautes : « bcp » est parfaitement clair entre amis.
# Mais dans une lettre de motivation, elles n'ont rien a y faire. Cette table
# ne sert donc que lorsque le registre soutenu est demande.
# ---------------------------------------------------------------------------
ABREVIATIONS_SOUTENUES = {
    "bcp": "beaucoup", "dsl": "désolé", "slt": "salut", "bjr": "bonjour",
    "bsr": "bonsoir", "stp": "s'il te plaît", "svp": "s'il vous plaît",
    "pk": "pourquoi", "pq": "pourquoi", "pcq": "parce que", "pck": "parce que",
    "prsq": "parce que", "cad": "c'est-à-dire", "qqn": "quelqu'un",
    "qqch": "quelque chose", "rdv": "rendez-vous", "tjr": "toujours",
    "tjrs": "toujours", "auj": "aujourd'hui", "ajd": "aujourd'hui",
    "vrmt": "vraiment", "jms": "jamais", "ms": "mais", "ds": "dans",
    "pr": "pour", "tt": "tout", "nrv": "énervé", "dispo": "disponible",
    "jsp": "je ne sais pas", "askip": "à ce qu'il paraît",
    "mrc": "merci", "bnj": "bonjour", "dac": "d'accord", "oki": "d'accord",
    "nan": "non", "ouaip": "oui", "chuis": "je suis",
    }

# ---------------------------------------------------------------------------
# Lexique a proteger.
#
# Aucun dictionnaire ne connait l'argot d'Internet, et les suggestions qu'il
# inspire sont absurdes : « dsl » -> « dol », « tkt » -> « tket ». Tout mot de
# cette liste sort du circuit avant meme d'etre examine.
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

# ---------------------------------------------------------------------------
# Mots anglais.
#
# Un message ecrit en francais en contient toujours quelques-uns, et le
# dictionnaire francais les prend pour des fautes : « the » deviendrait
# « thé », « can » deviendrait « c'an ». Seuls figurent ici les mots anglais
# qui ne sont pas aussi des mots francais — « site », « table » ou « long »
# n'ont pas besoin d'etre proteges, et « son » doit rester corrigible.
# ---------------------------------------------------------------------------
LEXIQUE_ANGLAIS = {
    "above", "account", "across", "activity", "add", "all", "also",
    "although", "always", "amazing", "and", "any", "anyone", "anything",
    "anywhere", "app", "appear", "area", "arm", "around", "ask", "at",
    "awesome", "back", "because", "become", "been", "before", "begin",
    "behind", "being", "believe", "below", "beside", "best", "between",
    "book", "branch", "bring", "bro", "browser", "buy", "by", "can",
    "card", "care", "check", "child", "city", "class", "click", "college",
    "come", "community", "company", "consider", "control", "could",
    "cover", "crazy", "create", "cut", "day", "death", "decision",
    "delete", "deploy", "development", "did", "difference", "director",
    "disk", "does", "doing", "door", "download", "drug", "dude", "during",
    "early", "easy", "edit", "education", "effect", "empty", "end",
    "even", "evening", "event", "everyone", "everything", "everywhere",
    "experience", "eye", "fact", "fake", "fall", "false", "family",
    "fast", "father", "feature", "feel", "field", "first", "fix",
    "folder", "follow", "form", "free", "friend", "from", "funny", "game",
    "get", "give", "going", "got", "government", "great", "ground",
    "group", "grow", "guy", "guys", "had", "hand", "happen", "has",
    "hate", "he", "head", "health", "hear", "heart", "help", "her",
    "here", "him", "his", "history", "hope", "host", "hour", "how",
    "however", "idea", "include", "install", "interest", "into", "is",
    "it", "its", "just", "keep", "kid", "kill", "kind", "know", "last",
    "late", "law", "lead", "learn", "leave", "level", "life", "line",
    "link", "list", "little", "load", "logout", "lose", "make", "many",
    "market", "matter", "maybe", "mean", "meet", "member", "memory",
    "merge", "might", "mind", "model", "money", "month", "morning",
    "most", "mother", "move", "much", "music", "my", "name", "near",
    "need", "network", "never", "next", "nice", "night", "nobody", "not",
    "nothing", "now", "number", "of", "offer", "old", "one", "only",
    "other", "others", "our", "over", "own", "paper", "party", "password",
    "pay", "payment", "perfect", "person", "play", "player", "please",
    "policy", "power", "president", "price", "problem", "program",
    "project", "provide", "push", "reach", "read", "real", "really",
    "reason", "receive", "relationship", "remain", "remember", "remove",
    "research", "result", "right", "road", "role", "room", "run", "said",
    "save", "say", "says", "school", "season", "see", "seem", "send",
    "sense", "server", "setup", "share", "she", "ship", "side", "since",
    "sit", "so", "society", "some", "someone", "something", "somewhere",
    "sorry", "space", "speak", "spend", "start", "stay", "story",
    "student", "study", "stuff", "system", "take", "talk", "tax", "teach",
    "teacher", "team", "than", "thank", "thanks", "that", "the", "their",
    "them", "then", "there", "therefore", "these", "they", "things",
    "think", "this", "though", "through", "time", "to", "today",
    "tomorrow", "tonight", "tool", "town", "true", "turn", "two", "under",
    "understand", "unless", "until", "up", "update", "upload", "very",
    "view", "voice", "wait", "walk", "want", "war", "was", "watch",
    "water", "way", "we", "website", "week", "weird", "welcome", "well",
    "were", "what", "when", "where", "which", "while", "who", "whom",
    "whose", "why", "wife", "will", "win", "with", "within", "without",
    "woman", "word", "work", "world", "worst", "would", "write", "wrong",
    "yeah", "year", "yes", "yesterday", "you", "young", "your",
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
    # @pseudo, #salon, /commande. Les points et tirets font partie du
    # pseudo : « @ma_rion.prrx » est un seul nom, et s'arreter au point en
    # faisait corriger la fin en « prix ». Le dernier caractere doit rester
    # une lettre ou un chiffre, pour ne pas avaler le point d'une phrase.
    r"(?<!\w)[@#/]\w(?:[\w.\-]*\w)?",
    r"\b\w*\d\w*\b",            # tout mot contenant un chiffre
]
