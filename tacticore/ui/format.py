"""Helpers de formato para la UI (texto en español, ASCII)."""

from rich.text import Text

from .palette import ACCENT


def money(amount: int) -> str:
    """Formatea un monto como '$1.234.567' (separador de miles con punto)."""
    return "$" + f"{amount:,}".replace(",", ".")


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
