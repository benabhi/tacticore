"""Silabas y piezas para armar nombres de fantasia.

Nada de esto corresponde a nombres reales: se combinan silabas inventadas para
generar nombres de jugadores y clubes ficticios.
"""

# --- Nombres de jugadores ---
# Se combinan 2-3 silabas para el nombre y 2-3 para el apellido.
FIRST_SYLLABLES = [
    "al", "bran", "cor", "dra", "el", "fen", "gor", "hal", "is", "jor",
    "kal", "lor", "mar", "nor", "or", "par", "quin", "ral", "sol", "tor",
    "ul", "val", "wen", "xan", "yor", "zel",
]

LAST_SYLLABLES = [
    "berg", "crest", "dahl", "fen", "gard", "holm", "kov", "lund", "mann",
    "nor", "ovic", "quist", "ridge", "stad", "thorn", "vik", "wood", "zen",
]

# --- Nombres de clubes ---
CLUB_PREFIXES = [
    "FC", "Real", "Athletic", "Sporting", "Inter", "Dynamo", "Olympic",
    "United", "Racing",
]

CLUB_SYLLABLES = [
    "aval", "brid", "corin", "dur", "esten", "frav", "gald", "harn", "ist",
    "jorn", "kel", "lund", "mor", "nard", "oste", "prav", "quel", "rast",
    "sund", "torv", "ulm", "verd", "wess", "zar",
]
