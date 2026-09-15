# -*- coding: utf-8 -*-
"""Correcteur d'orthographe francais qui respecte le francais parle."""

# Serie de versions. Le dernier nombre est ajoute a la compilation, a partir
# du nombre de commits : c'est GitHub qui ecrit « version_compilee.py ».
SERIE = "1.0"

try:
    from .version_compilee import VERSION as __version__
except ImportError:  # lance depuis les sources
    __version__ = f"{SERIE}.0+sources"
