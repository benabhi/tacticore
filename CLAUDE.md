# Tacticore — Guía del proyecto

Juego de **manager de fútbol de fantasía** para jugar en la terminal, construido
con [Textual](https://textual.textualize.io/). El mundo (clubes, jugadores,
ligas, estadios) se **genera proceduralmente**. Los **clubes, jugadores y
estadios son de fantasía** (nada real); los **países sí usan nombres reales**
(Argentina, Brasil, …) como contenedores, escritos en ASCII sin acentos por la
directiva 2. Cada país tiene **5 ligas** (niveles A a E): la A es la mejor y la
E es donde arrancan los managers nuevos.

## Directivas

> Reglas que aplican a TODO el código del proyecto. Respetarlas siempre.

1. **Resolución fija: 80×25.** Toda la interfaz se diseña para una terminal de
   80 columnas × 25 filas. Las constantes viven en
   [tacticore/config.py](tacticore/config.py) (`SCREEN_WIDTH`,
   `SCREEN_HEIGHT`). Si sobra alguna fila/columna, se reserva para HUD o menús.
2. **Solo caracteres ASCII en pantalla.** Todo lo que se dibuje debe usar
   únicamente ASCII imprimible (`0x20`–`0x7E`). Nada de box-drawing Unicode,
   símbolos ni emojis. Objetivo: que el juego corra en **cualquier** terminal,
   al estilo de los roguelikes viejos (de ahí también el 80×25).
3. **Solo colores ANSI estándar.** Usar únicamente los 16 colores ANSI que trae
   toda terminal (`black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`,
   `white` y sus variantes `bright_*`). Nada de RGB / truecolor (`#rrggbb`),
   porque depende del soporte de la terminal.
   - **Excepción temporal (desarrollo):** las franjas de césped de la cancha
     usan dos verdes RGB provisionales porque en muchas terminales el `green` y
     el `bright_green` se ven casi iguales. Está detrás del flag
     `DEV_TRUECOLOR_GRASS` en
     [ui/widgets/field.py](tacticore/ui/widgets/field.py); **antes de
     cerrar el proyecto hay que ponerlo en `False`** para cumplir la directiva.
4. **Código en inglés.** Identificadores (variables, funciones, clases,
   módulos) siempre en inglés. **Esto incluye los nombres de archivo**:
   `players_screen.py`, no `jugadores_screen.py`. En cambio, el **texto que ve
   el jugador en pantalla va en español** (labels, mensajes), siempre en ASCII.
5. **Comentarios en español.** Comentarios y docstrings en español.

## Stack

- Python ≥ 3.11
- Textual (interfaz de terminal)
- pytest (tests)

## Cómo correr

```bash
# con el venv activado
python main.py            # equivalente: python -m tacticore
```

Entorno de desarrollo (tests, herramientas de Textual):

```bash
pip install -e ".[dev]"
pytest
```

## Estructura

```
tacticore/
├── config.py            # Constantes globales (resolución, rutas, etc.)
├── core/                # Estado del juego, calendario y aleatoriedad
│   ├── game.py          #   GameState: contenedor raíz del estado
│   ├── calendar.py      #   Calendario y avance de fechas
│   └── rng.py           #   Aleatoriedad determinista (con semilla)
├── domain/              # Entidades puras del dominio (dataclasses)
│   ├── enums.py         #   Position, Foot, ...
│   ├── player.py        #   Player
│   ├── club.py          #   Club
│   ├── league.py        #   League / tabla de posiciones
│   └── match.py         #   Match (resultado de un partido)
├── generators/          # Generación procedural (fantasía)
│   ├── data/            #   Datos crudos (sílabas, prefijos, ...)
│   ├── name_generator.py
│   ├── player_generator.py
│   └── club_generator.py
├── simulation/          # Motores de cálculo (sin UI)
│   ├── match_engine.py  #   Simula un partido
│   └── season.py        #   Avanza una temporada / liga
├── persistence/         # Guardado y carga de partidas
│   └── savegame.py
└── ui/                  # Todo lo de Textual
    ├── app.py           #   App principal
    ├── screens/         #   Pantallas (menú, partido, plantilla, ...)
    └── widgets/         #   Widgets reutilizables (cancha, barra de menú, ...)
```

## Convenciones de arquitectura

- **Separación estricta UI ↔ lógica.** `ui/` solo lee el estado y dispara
  acciones; todos los cálculos viven fuera de `ui/`. Ningún módulo de `domain/`,
  `core/`, `simulation/` o `generators/` debe importar Textual.
- **`domain/`**: entidades puras (`dataclass`), sin lógica de UI ni de
  simulación. Son "datos con forma".
- **`generators/`**: cada generador recibe un `random.Random` para ser
  **determinista** (misma semilla → mismo mundo). Los datos de fantasía se
  guardan en `generators/data/`, separados de la lógica.
- **`core/rng.py`**: única fuente de aleatoriedad. No usar el `random` global;
  pasar siempre una instancia para poder reproducir partidas.
- **`simulation/`**: recibe entidades de `domain` y devuelve resultados; no
  muta la UI ni imprime nada.

## Estado actual

- Widget de cancha ([ui/widgets/field.py](tacticore/ui/widgets/field.py))
  con centro exacto (columna y fila centrales) y franjas de césped.
- Barra de menú inferior (placeholder).
- Generadores de nombres / jugadores / clubes: esqueleto inicial funcional.
