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
