"""Paleta de colores del juego, centralizada en un solo lugar.

Problema: muchos colores ANSI "brillantes" y "normales" se ven casi iguales en
varias terminales (nos paso con las franjas del cesped y con el jugador que
lleva la pelota). Pelear con eso color por color es un parche eterno.

Solucion: definir aca cada color por su ROL, con dos modos:

- TRUECOLOR (por defecto): valores RGB, que SI se distinguen bien. Resuelve la
  legibilidad en terminales modernas (la enorme mayoria hoy).
- ANSI 16 (fallback, TRUECOLOR=False): para correr en cualquier terminal vieja
  (la idea original / directiva 3). Usa colores de HUE distinto (no pares
  brillante/normal) para que igual se entiendan aunque la terminal mezcle brillos.

Asi cumplimos lo de "ASCII + correr en cualquier lado" sin pelear todo el tiempo
con colores que no se ven. Cambiar de modo es una sola linea (`TRUECOLOR`).

Mas adelante se puede autodetectar el soporte de la terminal (Rich expone el
`color_system`) y elegir el modo solo; por ahora es un flag explicito.
"""

# Modo de color. True = RGB (recomendado en terminales modernas).
TRUECOLOR = True

if TRUECOLOR:
    # Cesped: dos verdes que se distinguen de verdad.
    GRASS_LIGHT = "#3c9a3c"
    GRASS_DARK = "#2b7a2b"
    LINE = "#f0f0f0"
    # Equipos: tono base y tono "tiene la pelota" (claramente mas claro).
    HOME = "#3a7bd5"
    HOME_BALL = "#a9d8ff"
    AWAY = "#e0473b"
    AWAY_BALL = "#ffb0a4"
    # Pelota suelta (en disputa / viajando).
    BALL = "#ffe14d"
    # Arqueros: magenta para diferenciarlos de los jugadores de campo.
    GK = "#c060d0"
    GK_BALL = "#e6a8f0"
    # Arbitro: amarillo mas dorado/apagado para no confundirse con la pelota.
    REF = "#caa63a"
    # Texto secundario (ej. el reloj del relato): gris tenue.
    MUTED = "#8a8a8a"
    # Acento de UI: resalta atajos de teclado (la letra dentro de [X]) y detalles.
    # Ambar que contrasta tanto sobre el verde de la barra como sobre el negro.
    ACCENT = "#ffd24a"
    # Fondo de la barra informativa superior: azul pizarra oscuro. La columna del
    # nombre de pantalla queda en negro encima -> se ve como una pestaña.
    BAR_BG = "#26364a"
    # Etiquetas cortas / badges (ej. el codigo de pais "(AR)"): cian suave.
    TAG = "#5fc9d6"
    # Nivel/division (ej. la letra de liga A-E): lila suave, distinto del TAG.
    TIER = "#c084fc"
    # Colores de identidad de club (identicon, versus, listas). Hues bien distintos
    # entre si; el de cada club sale de un hash de su nombre.
    IDENTICON_COLORS = [
        "#d64545", "#e0823a", "#d9b13a", "#9bbe3a", "#4fa84f", "#3aa98c",
        "#3a9bd6", "#4a73d6", "#7a5ad0", "#a64fc0", "#c84c98", "#d65a7e",
        "#b07a4a", "#5f93a8",
    ]
else:
    # Fallback ANSI 16: HUE distinto para cada rol, evitando depender del
    # contraste brillante/normal (que algunas terminales no muestran).
    GRASS_LIGHT = "bright_green"
    GRASS_DARK = "green"
    LINE = "bright_white"
    HOME = "blue"
    HOME_BALL = "bright_cyan"
    AWAY = "red"
    AWAY_BALL = "bright_magenta"
    BALL = "yellow"
    GK = "magenta"
    GK_BALL = "bright_magenta"
    REF = "yellow"
    MUTED = "bright_black"
    # Acento de UI: resalta atajos de teclado (la letra dentro de [X]) y detalles.
    ACCENT = "yellow"
    # Fondo de la barra informativa superior.
    BAR_BG = "blue"
    # Etiquetas cortas / badges (ej. el codigo de pais).
    TAG = "cyan"
    # Nivel/division (la letra de liga A-E).
    TIER = "magenta"
    # Identidad de club en ANSI: hues distintos (el dos-tonos del identicon lo dan
    # los caracteres #/:, no el par brillante/normal). Si dos clubes caen en el
    # mismo color, igual se distinguen por el glifo y el patron.
    IDENTICON_COLORS = [
        "red", "green", "yellow", "blue", "magenta", "cyan",
        "bright_red", "bright_green", "bright_yellow", "bright_blue",
        "bright_magenta", "bright_cyan",
    ]
