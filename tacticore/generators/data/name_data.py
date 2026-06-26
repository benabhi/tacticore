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

# --- Nombres de clubes (fantasia) ---
# Un nombre de club se arma combinando un TOPONIMO inventado (la pieza central,
# p. ej. "Caldton") con descriptores genericos de futbol opcionales, delante
# (CLUB_PREFIXES: "Real Caldton") o detras (CLUB_SUFFIXES: "Caldton United").
# El toponimo sale de un comienzo (TOPO_HEADS) + un infijo opcional (TOPO_INFIXES)
# + un final (TOPO_TAILS). Los finales son de varias culturas (-ton ingles,
# -berg aleman, -grad eslavo, -vik nordico, -polis griego...) para que el mundo
# se sienta variado. El espacio combinatorio es de varios millones de nombres.

# Descriptores genericos (no son clubes reales): van delante del toponimo.
CLUB_PREFIXES = [
    "FC", "AC", "SC", "CD", "CF", "Real", "Athletic", "Sporting", "Inter",
    "Dynamo", "Olympic", "Racing", "Club", "Deportivo", "Atletico", "Union",
    "Nacional", "Rapid", "Lokomotiv", "Spartak", "Standard", "Estrella",
]

# Descriptores genericos que van detras del toponimo.
CLUB_SUFFIXES = [
    "United", "City", "FC", "Rovers", "Wanderers", "Athletic", "Town",
    "County", "Albion", "Star", "Borough", "Vale", "Rangers", "Forest",
    "Saints", "Stars",
]

# Comienzos del toponimo (capitalizados). Piezas inventadas para evitar caer en
# nombres de clubes/ciudades reales.
TOPO_HEADS = [
    "Aval", "Ash", "Brael", "Brom", "Cald", "Carn", "Dun", "Eld", "Fen",
    "Glen", "Grim", "Hald", "Kel", "Lang", "Mor", "Nord", "Oster", "Pol",
    "Rav", "Stor", "Thal", "Vard", "Wend", "Yar", "Zell", "Bram", "Drav",
    "Esk", "Falk", "Garn", "Hel", "Jor", "Kron", "Lind", "Marn", "Nev",
    "Orm", "Pent", "Rast", "Sten", "Torv", "Ulv", "Vorn", "Wess", "Zar",
    "Bel", "Dorn", "Elm", "Frith", "Gald", "Harn", "Korn", "Lorn", "Mald",
    "Norv", "Pern", "Quel", "Rund", "Selm", "Tarn", "Velt", "Wold", "Yarl",
    "Zorn", "Cresh", "Asp", "Skel",
]

# Infijos opcionales (alargan el toponimo).
TOPO_INFIXES = [
    "ing", "en", "er", "ber", "ner", "ling", "wer", "an", "as", "or", "ten",
]

# Finales del toponimo (de varias culturas).
TOPO_TAILS = [
    "ton", "ham", "ford", "field", "bury", "burgh", "dale", "wick",
    "mouth", "borough", "vik", "holm", "stad", "by", "fell", "berg",
    "burg", "heim", "stein", "furt", "grad", "ovia", "polis", "port",
    "haven", "moor", "gate", "cliff", "wald", "mar", "ster", "shire",
    "thorpe", "ness", "ridge", "worth", "combe", "gard", "stead", "ville",
]

# --- Apodos / alias (raros, ej. "La Pulga") ---
# Se arman como "El/La <sustantivo> [<adjetivo>]". Los sustantivos y adjetivos
# van separados por genero para que concuerden con el articulo (El Toro Negro /
# La Pulga Negra). El espacio combinatorio es de ~1000 alias distintos.
NICK_EL_NOUNS = [
    "Toro", "Mago", "Pibe", "Loco", "Tanque", "Principe", "Matador", "Gato",
    "Rayo", "Tigre", "Leon", "Lobo", "Halcon", "Cometa", "Trueno", "Huracan",
    "Misil", "Canon", "Tractor", "Pulpo", "Bicho", "Mono", "Zorro", "Paton",
    "Cabezon", "Mortero", "Fenomeno", "Verdugo", "Brujo", "Pistolero", "Angel",
    "Demonio", "Duende", "Gigante", "Coloso", "Emperador", "Faraon", "Vikingo",
    "Pirata", "Capitan", "Profesor", "Doctor", "Artista", "Genio", "Maestro",
    "Diamante", "Relampago", "Cohete", "Tornado", "Vendaval",
]
NICK_LA_NOUNS = [
    "Pulga", "Joya", "Bestia", "Roca", "Bala", "Flecha", "Sombra", "Chispa",
    "Perla", "Arana", "Hormiga", "Fiera", "Maquina", "Furia", "Niebla",
    "Pantera", "Cobra", "Llama", "Bomba", "Saeta", "Tromba", "Avispa",
]
NICK_EL_ADJ = [
    "Negro", "Loco", "Salvaje", "Magico", "Eterno", "Veloz", "Letal", "Fino",
    "Rojo", "Dorado", "Maldito", "Divino", "Fantasma", "Volador", "Imparable",
]
NICK_LA_ADJ = [
    "Negra", "Loca", "Salvaje", "Magica", "Eterna", "Veloz", "Letal", "Fina",
    "Roja", "Dorada", "Maldita", "Divina", "Fantasma", "Voladora", "Imparable",
]

# --- Nombres de hinchadas / grupos de fans (ej. "La Furia Roja") ---
# Combinatorios, separados por genero para concordar con el articulo.
FAN_ANIMALS = [
    "Leones", "Lobos", "Toros", "Halcones", "Cuervos", "Tiburones", "Dragones",
    "Diablos", "Gigantes", "Titanes", "Osos", "Pumas", "Jaguares", "Buitres",
    "Demonios", "Guerreros",
]
FAN_ADJECTIVES = [
    "Fieles", "Valientes", "Indomables", "Bravos", "Eternos", "Rebeldes",
    "Locos", "Salvajes", "Imparables", "Leales", "Inmortales", "Intrepidos",
    "Audaces", "Invencibles",
]
FAN_LA_NOUNS = [
    "Banda", "Furia", "Legion", "Marea", "Guardia", "Horda", "Pena", "Brigada",
    "Tribu", "Barra", "Hinchada", "Pasion", "Fiebre", "Garra",
]
FAN_MASC_COLLECTIVE = ["Comando", "Frente", "Clan", "Bloque", "Ultras"]
FAN_FEM_MODIFIERS = [
    "Roja", "Negra", "Blanca", "Dorada", "Azul", "Verde", "del Norte",
    "del Sur", "del Este", "del Oeste", "de Hierro", "de Acero", "Eterna",
    "Brava",
]
FAN_MASC_MODIFIERS = [
    "Rojo", "Negro", "Blanco", "Dorado", "Azul", "Verde", "Norte", "Sur",
    "Este", "Oeste", "de Hierro", "de Acero", "Eterno", "Bravo",
]
