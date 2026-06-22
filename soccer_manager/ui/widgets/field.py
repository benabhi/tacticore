"""Widget de cancha de futbol.

Se dibuja SOLO con caracteres ASCII y colores ANSI estandar, para que corra en
cualquier terminal (estilo roguelike clasico). Ver las directivas en CLAUDE.md.

Para que la cancha tenga un centro EXACTO (una unica columna central y una
unica fila central, que es desde donde se saca la pelota), las dimensiones
internas deben ser IMPARES. Por eso, dentro del area asignada, se dibuja en el
mayor tamano impar que entra; lo que sobra (1 columna / 1 fila) se rellena con
cesped para que el area quede pareja.
"""

import math

from rich.text import Text
from textual.widget import Widget

# --- Caracteres de la cancha (ASCII puro) ---
CH_HLINE = "-"      # lineas horizontales
CH_VLINE = "|"      # lineas verticales
CH_JUNCTION = "+"   # esquinas y cruces
CH_CIRCLE = "."     # circulo central (punteado)
CH_PENALTY = "o"    # puntos de penal
CH_KICKOFF = "O"    # punto central (saque)

# --- Colores del cesped ---
# Franjas de corte: bandas verticales alternadas (claro / oscuro), simetricas
# respecto a la columna central.
STRIPE_WIDTH = 9             # ancho de cada franja, en columnas

# EXCEPCION TEMPORAL A LA DIRECTIVA 3 (ver CLAUDE.md): la directiva pide solo
# colores ANSI, pero en muchas terminales el verde normal y el brillante se ven
# casi iguales y las franjas no se distinguen. Mientras desarrollamos usamos dos
# verdes RGB para poder verlas. Antes de cerrar el proyecto hay que volver a los
# ANSI: poner DEV_TRUECOLOR_GRASS = False.
DEV_TRUECOLOR_GRASS = True

if DEV_TRUECOLOR_GRASS:
    GRASS_LIGHT = "#3c9a3c"   # provisional (no ANSI)
    GRASS_DARK = "#2b7a2b"    # provisional (no ANSI)
else:
    GRASS_LIGHT = "bright_green"
    GRASS_DARK = "green"
LINE_COLOR = "bright_white"

GRASS_LIGHT_STYLE = f"on {GRASS_LIGHT}"
GRASS_DARK_STYLE = f"on {GRASS_DARK}"
LINE_LIGHT_STYLE = f"{LINE_COLOR} on {GRASS_LIGHT}"
LINE_DARK_STYLE = f"{LINE_COLOR} on {GRASS_DARK}"


def build_field(width: int, height: int) -> list[str]:
    """Devuelve la cancha como lista de filas (strings).

    `width` y `height` se fuerzan a impares para garantizar un centro unico.
    """
    # Forzar dimensiones impares -> centro exacto en width // 2 y height // 2.
    if width % 2 == 0:
        width -= 1
    if height % 2 == 0:
        height -= 1
    width = max(width, 21)
    height = max(height, 11)

    grid = [[" "] * width for _ in range(height)]

    cx = width // 2   # columna central (unica porque width es impar)
    cy = height // 2  # fila central   (unica porque height es impar)

    def hline(row: int, c0: int, c1: int, ch: str = CH_HLINE) -> None:
        for c in range(c0, c1 + 1):
            grid[row][c] = ch

    def vline(col: int, r0: int, r1: int, ch: str = CH_VLINE) -> None:
        for r in range(r0, r1 + 1):
            grid[r][col] = ch

    # --- Borde exterior (lineas de banda y de fondo) ---
    hline(0, 0, width - 1)
    hline(height - 1, 0, width - 1)
    vline(0, 0, height - 1)
    vline(width - 1, 0, height - 1)
    grid[0][0] = CH_JUNCTION
    grid[0][width - 1] = CH_JUNCTION
    grid[height - 1][0] = CH_JUNCTION
    grid[height - 1][width - 1] = CH_JUNCTION

    # --- Linea de mitad de cancha (vertical, por la columna central) ---
    vline(cx, 1, height - 2)
    grid[0][cx] = CH_JUNCTION
    grid[height - 1][cx] = CH_JUNCTION

    # --- Areas: penal (grande) y de meta (chica), espejadas a cada lado ---
    def draw_box(width_box: int, half_height: int, left_side: bool) -> None:
        """Dibuja un area rectangular pegada a la linea de fondo."""
        r0, r1 = cy - half_height, cy + half_height
        if left_side:
            back, front = 0, width_box
        else:
            back, front = width - 1, width - 1 - width_box
        hline(r0, min(back, front), max(back, front))
        hline(r1, min(back, front), max(back, front))
        vline(front, r0 + 1, r1 - 1)
        # En ASCII todas las esquinas y uniones son el mismo caracter.
        grid[r0][front] = CH_JUNCTION
        grid[r1][front] = CH_JUNCTION
        grid[r0][back] = CH_JUNCTION
        grid[r1][back] = CH_JUNCTION

    # Area penal grande.
    draw_box(width_box=8, half_height=4, left_side=True)
    draw_box(width_box=8, half_height=4, left_side=False)
    # Area de meta chica.
    draw_box(width_box=4, half_height=2, left_side=True)
    draw_box(width_box=4, half_height=2, left_side=False)

    # Puntos de penal.
    grid[cy][6] = CH_PENALTY
    grid[cy][width - 1 - 6] = CH_PENALTY

    # --- Circulo central (elipse: la celda del terminal es ~2:1) ---
    radius_x, radius_y = 6, 3
    for deg in range(0, 360, 3):
        angle = math.radians(deg)
        x = round(cx + radius_x * math.cos(angle))
        y = round(cy + radius_y * math.sin(angle))
        if 0 < x < width - 1 and 0 < y < height - 1 and grid[y][x] == " ":
            grid[y][x] = CH_CIRCLE

    # --- Punto central (saque): centro EXACTO de filas y columnas ---
    grid[cy][cx] = CH_KICKOFF

    return ["".join(row) for row in grid]


def paint_field(rows: list[str], width: int, height: int) -> Text:
    """Convierte la grilla de chars en un `Text` con franjas de cesped.

    Cada columna elige su tono segun la banda a la que pertenece; las bandas se
    miden como distancia a la columna central, asi quedan simetricas. Las
    celdas que sobran (la cancha es impar) se rellenan con cesped para cubrir
    todo el area asignada.
    """
    text = Text(no_wrap=True)
    if not rows:
        return text
    cx = len(rows[0]) // 2
    for r in range(height):
        row = rows[r] if r < len(rows) else ""
        for c in range(width):
            ch = row[c] if c < len(row) else " "
            band = (abs(c - cx) + STRIPE_WIDTH // 2) // STRIPE_WIDTH
            light = band % 2 == 0
            if ch == " ":
                style = GRASS_LIGHT_STYLE if light else GRASS_DARK_STYLE
            else:
                style = LINE_LIGHT_STYLE if light else LINE_DARK_STYLE
            text.append(ch, style=style)
        if r != height - 1:
            text.append("\n")
    return text


class SoccerField(Widget):
    """Renderiza la cancha ocupando el area que se le asigne."""

    def render(self) -> Text:
        w, h = self.size.width, self.size.height
        return paint_field(build_field(w, h), w, h)
