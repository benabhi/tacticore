# Tacticore — Guía del proyecto

Juego de **manager de fútbol de fantasía** para jugar en la terminal, construido
con [Textual](https://textual.textualize.io/). El mundo (clubes, jugadores,
ligas, estadios) se **genera proceduralmente**. Los **clubes, jugadores y
estadios son de fantasía** (nada real); los **países sí usan nombres reales**
(Argentina, Brasil, …) como contenedores, escritos en ASCII sin acentos por la
directiva 2. Cada país tiene **5 ligas** (niveles A a E): la A es la mejor y la
E es donde arrancan los managers nuevos.

El juego tiene **dos fases**: gestión por turnos (días/eventos) y **partidos en
tiempo real** (los jugadores se mueven en la cancha y el manager da órdenes en
vivo). El plan del motor, el rediseño de atributos a **escala 1–100 con
decimales**, el modelo de cancha continua, la IA y la estrategia de render viven
en **[docs/DESIGN.md](docs/DESIGN.md)** — leerlo antes de tocar atributos,
generadores o el motor de partido.

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
3. **Colores: paleta central, truecolor por defecto con fallback ANSI 16.**
   Todos los colores se definen por su ROL en un único lugar:
   [ui/palette.py](tacticore/ui/palette.py). Hay dos modos:
   - **TRUECOLOR (por defecto):** valores RGB. Se eligió porque muchos ANSI
     `bright_*` vs normales se ven casi iguales en terminales modernas (nos pasó
     con las franjas de césped y con el resaltado del que lleva la pelota), y
     pelear con eso color por color era un parche eterno.
   - **ANSI 16 (`TRUECOLOR=False`):** fallback para correr en cualquier terminal
     vieja (la idea original). Usa colores de **hue distinto** (no pares
     `bright`/normal) para que igual se entiendan.
   - Regla práctica: **nunca** distinguir dos cosas solo por `bright_x` vs `x`;
     agregar/editar colores **siempre** en `palette.py`, nunca hardcodeados en
     los widgets. El código de pantalla referencia los nombres de la paleta.
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
