"""Helpers de formato para la UI (texto en español, ASCII)."""

from rich.text import Text

from .palette import ACCENT


def money(amount: int) -> str:
    """Formatea un monto como '$1.234.567' (separador de miles con punto)."""
    return "$" + f"{amount:,}".replace(",", ".")


_TR_COL_W = 40  # ancho de cada columna del informe de entrenamiento (2 x 40 = 80)


def _training_cell(line: str) -> Text:
    """Una mejora ('Nombre +0.7 Atributo') como celda: nombre gris + ganancia VERDE."""
    t = Text()
    if " +" in line:
        name, rest = line.split(" +", 1)
        gain, _, attr = rest.partition(" ")
        t.append(f"{name[:18]:<18} ", style="grey70")
        t.append(f"+{gain}", style="bold green")
        t.append(f" {attr[:14]}", style="grey62")
    else:
        t.append(line[:_TR_COL_W], style="grey70")
    return t


def training_report_lines(message: str, max_rows: int, cols: int = 2) -> list[Text]:
    """Formatea un informe de entrenamiento en columnas legibles (aprovecha el ancho).

    El `message` es: una linea de resumen + una mejora por renglon ('Nombre +0.7
    Atributo'). Devuelve el resumen y las mejoras repartidas en `cols` columnas,
    acotado a `max_rows` filas (con '... y N mas' si no entran todas)."""
    parts = message.split("\n")
    summary = parts[0] if parts else ""
    imps = [p.strip() for p in parts[1:] if p.strip()]
    out = [Text(summary, style="white")]
    body_rows = max(0, max_rows - 1)
    if not imps or body_rows == 0:
        return out
    fit = body_rows * cols
    if len(imps) <= fit:
        shown, extra = imps, 0
    else:                                  # deja la ultima fila para el "... y N mas"
        shown, extra = imps[:(body_rows - 1) * cols], len(imps) - (body_rows - 1) * cols
    disp_rows = (len(shown) + cols - 1) // cols
    for r in range(disp_rows):
        line = Text()
        for c in range(cols):
            idx = c * disp_rows + r        # llenado por columnas
            if idx < len(shown):
                cell = _training_cell(shown[idx])
                line.append_text(cell)
                line.append(" " * max(0, _TR_COL_W - len(cell.plain)))
            else:
                line.append(" " * _TR_COL_W)
        out.append(line)
    if extra:
        out.append(Text(f"  ... y {extra} mejoras mas", style="grey50"))
    return out


def hint(*items, sep: str = "   ") -> Text:
    """Linea de ayuda con la TECLA en amarillo (acento) y la descripcion en gris.

    Estandar de atajos: cada item es `(tecla, descripcion)` -> se ve
    `tecla: descripcion` con la tecla resaltada; o un string suelto (texto gris).
    Ej: `hint(("Enter", "elegir"), ("Esc", "cancelar"))`.
    """
    t = Text(no_wrap=True)
    for i, item in enumerate(items):
        if i:
            t.append(sep)
        if isinstance(item, tuple):
            key, label = item
            t.append(key, style=f"bold {ACCENT}")
            if label:
                t.append(": " + label, style="grey62")
        else:
            t.append(item, style="grey62")
    return t


def append_section(
    t: Text,
    title: str,
    rows: list,
    indent: int = 2,
    rule: bool = False,
    width: int = 76,
    title_style: str = "bold green",
) -> None:
    """Agrega una seccion al `Text` `t`: titulo + contenido indentado.

    Estilo sobrio (como la ficha del jugador): un encabezado en verde y las
    lineas debajo con sangria, separadas del resto por una linea en blanco. No
    usa recuadros ASCII. `rows` es una lista de items: string (blanco) o tupla
    `(texto, estilo)`. Con `rule=True` agrega una linea de guiones bajo el titulo.
    """
    t.append(title + "\n", style=title_style)
    if rule:
        t.append("-" * width + "\n", style="grey50")
    pad = " " * indent
    for row in rows:
        text, style = row if isinstance(row, tuple) else (row, "white")
        t.append(pad + text + "\n", style=style)
    t.append("\n")
