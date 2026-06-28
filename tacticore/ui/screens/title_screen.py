"""Pantalla de titulo: ASCII-art del nombre, slogan, prompt parpadeante.

Estilo arcade viejo. Toda la portada se arma como una "escena" de 80x25: se
dibuja en una grilla de caracteres (con color por celda) y se vuelca a un unico
`Static`. Asi el titulo va arriba, el slogan debajo, el prompt parpadeante mas
abajo, y al pie una fila de cesped ASCII con la pelota apoyada en un costado.

Al presionar Enter: si hay una partida guardada, la carga y va a la Oficina
("Continuar"); si no, arranca una partida nueva (Carga -> Crea tu club).
"""

import random

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...persistence import savegame
from ..art import render_banner
from ..palette import GRASS_DARK, GRASS_LIGHT, LINE, MUTED
from .base_screen import BaseScreen

_W, _H = 80, 25

_SLOGAN = "Manager de futbol para nerds"
_PROMPT_NEW = "Presiona <ENTER> para comenzar"
_PROMPT_CONTINUE = "Presiona <ENTER> para continuar"

# Pelota de futbol en ASCII. Los pentagonos (caracteres '@' y 'a') van en un
# tono oscuro y el resto del contorno en blanco, asi se lee como pelota.
_BALL = [
    r"    _,...,_",
    r"  .'@/   \@'.",
    r" //  \___/  \\",
    r"|@\__/a@a\__/a|",
    r"|a/  \@@@/  \@|",
    r" \\__/   \__//",
    r"  `.a\___/a.'",
    "    `'\"\"\"\"`",
]

# Cesped: filas de "pasto" ASCII, generadas UNA vez de forma determinista para
# que no parpadeen al re-renderizar la escena (solo cambia el prompt). Dos verdes
# alternados dan textura. La fila de abajo es densa; arriba van "puntas" mas
# ralas para que el cesped se vea mas alto.
def _make_grass(density: float, glyphs: str, seed: int) -> tuple[list, list]:
    """Devuelve (caracteres, estilos) de una fila de cesped de 80 columnas.

    `density` es la probabilidad de que una columna tenga una brizna (1.0 = fila
    llena; menos = puntas sueltas, con espacios entre medio).
    """
    rnd = random.Random(seed)
    chars: list = []
    styles: list = []
    for _ in range(_W):
        if rnd.random() < density:
            chars.append(rnd.choice(glyphs))
            styles.append(GRASS_LIGHT if rnd.random() < 0.5 else GRASS_DARK)
        else:
            chars.append(" ")
            styles.append(None)
    return chars, styles


_GRASS_CHARS, _GRASS_STYLES = _make_grass(1.0, "`'.,vw", 20260626)  # fila densa


class TitleScreen(BaseScreen):
    """Portada del juego."""

    BINDINGS = [("enter", "start", "Comenzar")]

    CSS = """
    #scene {
        width: 80;
        height: 25;
    }
    """

    def compose_viewport(self) -> ComposeResult:
        self._blink_on = True
        # El prompt cambia segun haya o no una partida guardada.
        self._prompt = _PROMPT_CONTINUE if savegame.save_exists() else _PROMPT_NEW
        yield Static(self._build_scene(self._blink_on), id="scene")

    def on_mount(self) -> None:
        # Parpadeo del prompt cada medio segundo (re-dibuja la escena).
        self.set_interval(0.5, self._toggle_blink)

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.query_one("#scene", Static).update(self._build_scene(self._blink_on))

    # --- Armado de la escena (grilla de caracteres con color por celda) ---
    def _build_scene(self, blink_on: bool) -> Text:
        grid = [[" "] * _W for _ in range(_H)]
        style = [[None] * _W for _ in range(_H)]

        def place(row, col, lines, sty):
            """Estampa lineas en la grilla; `sty` es un estilo o una funcion(ch)."""
            for dr, line in enumerate(lines):
                for dc, ch in enumerate(line):
                    r, c = row + dr, col + dc
                    if 0 <= r < _H and 0 <= c < _W and ch != " ":
                        grid[r][c] = ch
                        style[r][c] = sty(ch) if callable(sty) else sty

        # Titulo: ASCII-art centrado, subido en el tercio superior.
        banner = render_banner("TACTICORE")
        bw = len(banner[0])
        place(4, (_W - bw) // 2, banner, "bold green")

        # Slogan debajo del titulo.
        place(10, (_W - len(_SLOGAN)) // 2, [_SLOGAN], "grey62")

        # Prompt parpadeante (su texto depende de si hay partida guardada).
        if blink_on:
            place(13, (_W - len(self._prompt)) // 2, [self._prompt], "bold yellow")

        # Cesped: una unica fila densa abajo. Se dibuja ANTES que la pelota para
        # que su base quede apoyada encima.
        for c in range(_W):
            grid[_H - 1][c] = _GRASS_CHARS[c]
            style[_H - 1][c] = _GRASS_STYLES[c]

        # Pelota apoyada en el cesped, en el costado derecho (posicion original).
        # Se dibuja el cuerpo y la curva inferior `.a\___/a.', pero NO la base
        # `'""""`: esa fila de mas abajo del dibujo es, justamente, el cesped.
        ball_color = lambda ch: MUTED if ch in "@a" else LINE
        place(_H - len(_BALL), 61, _BALL[:-1], ball_color)

        return self._grid_to_text(grid, style)

    @staticmethod
    def _grid_to_text(grid, style) -> Text:
        """Agrupa celdas contiguas del mismo estilo en spans de un `Text`."""
        t = Text()
        for r in range(_H):
            c = 0
            while c < _W:
                st = style[r][c]
                buf = grid[r][c]
                c += 1
                while c < _W and style[r][c] == st:
                    buf += grid[r][c]
                    c += 1
                t.append(buf) if st is None else t.append(buf, style=st)
            if r < _H - 1:
                t.append("\n")
        return t

    def action_start(self) -> None:
        # Import local para evitar imports circulares.
        from .office_screen import OfficeScreen

        if self.app.game is not None:
            # Ya hay una partida en curso en memoria.
            self.app.switch_screen(OfficeScreen())
        elif savegame.save_exists():
            # Continuar: cargar la partida guardada y entrar a la Oficina.
            self.app.game = savegame.load_game()
            self.app.switch_screen(OfficeScreen())
        else:
            # Partida nueva: generar el mundo.
            from .loading_screen import LoadingScreen

            self.app.switch_screen(LoadingScreen())
