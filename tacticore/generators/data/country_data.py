"""Paises disponibles para generar el mundo.

Usan nombres reales (paises conocidos del ambiente del futbol) como
contenedores; los clubes y jugadores que se generan adentro son de fantasia,
pero los NOMBRES de los jugadores salen del dataset real segun la nacionalidad.
Los nombres de pais van en ASCII (sin acentos) por la directiva 2.

Cada entrada es (nombre, codigo ISO alpha2). El codigo coincide con el archivo
del dataset (datasets/names/data/<CODIGO>.csv) y con el pool destilado
(tacticore/generators/data/names/<CODIGO>.json). El orden importa: con
WORLD_COUNTRY_COUNT se toman los primeros N.
"""

COUNTRIES = [
    ("Argentina", "AR"),
    ("Brasil", "BR"),
    ("Espana", "ES"),
    ("Inglaterra", "GB"),
    ("Italia", "IT"),
    ("Alemania", "DE"),
    ("Francia", "FR"),
    ("Paises Bajos", "NL"),
    ("Portugal", "PT"),
    ("Uruguay", "UY"),
    ("Mexico", "MX"),
    ("Colombia", "CO"),
    ("Belgica", "BE"),
    ("Chile", "CL"),
    ("Estados Unidos", "US"),
    ("Japon", "JP"),
]
