"""Paises disponibles para generar el mundo (ligas, nacionalidades, nombres).

Usan nombres reales (paises del ambiente del futbol) como contenedores; los
clubes y jugadores que se generan adentro son de fantasia, pero los NOMBRES de
los jugadores salen del dataset real segun la nacionalidad. Los nombres de pais
van en ASCII (sin acentos) por la directiva 2.

Cada entrada de `COUNTRIES` es (nombre, codigo). El codigo identifica al pais
(nacionalidad, liga) y, por defecto, tambien el pool de nombres
(tacticore/generators/data/names/<codigo>.json).

Algunos paises NO tienen dataset propio de nombres (o comparten cultura de
nombres con un vecino): para esos, `NAME_POOL` mapea el codigo del pais al
codigo del POOL que usan. Asi las naciones britanicas comparten el pool "GB" y,
p. ej., Ucrania usa el pool ruso, sin duplicar archivos. El orden de la lista
importa: con WORLD_COUNTRY_COUNT se toman los primeros N.
"""

COUNTRIES = [
    # Grandes ligas / nucleo futbolero primero (un mundo chico igual queda bueno).
    ("Espana", "ES"),
    ("Inglaterra", "EN"),
    ("Italia", "IT"),
    ("Alemania", "DE"),
    ("Francia", "FR"),
    ("Paises Bajos", "NL"),
    ("Portugal", "PT"),
    ("Argentina", "AR"),
    ("Brasil", "BR"),
    ("Belgica", "BE"),
    ("Turquia", "TR"),
    ("Rusia", "RU"),
    ("Escocia", "SC"),
    ("Grecia", "GR"),
    ("Mexico", "MX"),
    ("Estados Unidos", "US"),
    # Resto de Europa.
    ("Austria", "AT"),
    ("Suiza", "CH"),
    ("Dinamarca", "DK"),
    ("Suecia", "SE"),
    ("Noruega", "NO"),
    ("Polonia", "PL"),
    ("Republica Checa", "CZ"),
    ("Croacia", "HR"),
    ("Serbia", "RS"),
    ("Ucrania", "UA"),
    ("Rumania", "RO"),
    ("Hungria", "HU"),
    ("Bulgaria", "BG"),
    ("Eslovaquia", "SK"),
    ("Eslovenia", "SI"),
    ("Bielorrusia", "BY"),
    ("Finlandia", "FI"),
    ("Islandia", "IS"),
    ("Irlanda del Norte", "NI"),
    ("Republica de Irlanda", "IE"),
    ("Gales", "WA"),
    ("Letonia", "LV"),
    ("Lituania", "LT"),
    ("Israel", "IL"),
    ("Gibraltar", "GI"),
    # Asia / Oceania.
    ("Japon", "JP"),
    ("Corea del Sur", "KR"),
    ("China", "CN"),
    ("Australia", "AU"),
    ("Emiratos Arabes Unidos", "AE"),
    ("India", "IN"),
    ("Indonesia", "ID"),
    ("Malasia", "MY"),
    ("Singapur", "SG"),
    ("Hong Kong", "HK"),
    # Resto de America.
    ("Uruguay", "UY"),
    ("Chile", "CL"),
    ("Colombia", "CO"),
    ("Peru", "PE"),
    ("Canada", "CA"),
    # Africa.
    ("Sudafrica", "ZA"),
    ("Egipto", "EG"),
]

# Codigo de pais -> codigo del POOL de nombres que usa (cuando difiere del propio).
# Las naciones britanicas comparten "GB"; los paises sin dataset propio usan el de
# un vecino de cultura de nombres parecida.
NAME_POOL = {
    "EN": "GB",  # Inglaterra
    "SC": "GB",  # Escocia
    "WA": "GB",  # Gales
    "NI": "GB",  # Irlanda del Norte
    "GI": "GB",  # Gibraltar (territorio britanico)
    "AU": "GB",  # Australia (nombres ingleses)
    "BY": "RU",  # Bielorrusia
    "UA": "RU",  # Ucrania
    "SK": "CZ",  # Eslovaquia
    "LV": "LT",  # Letonia (baltico)
    "RO": "MD",  # Rumania (moldavo = rumano)
}


def pool_code(country_code: str) -> str:
    """Codigo del pool de nombres para un pais (su propio codigo o el alias)."""
    return NAME_POOL.get(country_code, country_code)
