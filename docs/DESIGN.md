# Tacticore — Documento de diseño del motor

> Fuente de verdad de las decisiones de fondo. Se va actualizando. Para las
> reglas duras del proyecto ver [CLAUDE.md](../CLAUDE.md).

## 1. Visión y las dos fases

Tacticore tiene **dos fases bien marcadas**, con motores distintos:

1. **Gestión (por turnos / días).** Avanzar el calendario, eventos, entrenos,
   finanzas, mercado, moral, etc. Ritmo pausado, basado en pantallas/menús.
2. **Partido (tiempo real).** Los 22 jugadores y la pelota se mueven en la
   cancha de forma continua y animada; el manager mira y da órdenes en vivo
   (cambios, zonas, tácticas) sin que el juego se bloquee.

Esto NO es Hattrick (que simula el partido como texto). Acá el partido **se
juega**. Eso obliga a un set de atributos y una arquitectura más ricos.

## 2. Decisiones de fondo (resumen)

- **Atributos 1–100 con decimales (float).** Permite progreso fino (entrenos
  de `+0.59`), sin techos rápidos. **Sin etiquetas tipo "pobre/divino"** (eso
  era Hattrick; acá nos diferenciamos). Ver §3.
- **Separación estricta motor ↔ UI.** El motor de partido NO importa Textual;
  expone estado y recibe comandos. La UI solo lee y dibuja. (Igual que el resto
  del proyecto.)
- **Cancha continua + render por celdas.** Los jugadores tienen posición
  `float` en coordenadas de cancha (metros); el render mapea a celdas 80×25.
  Ver §4.
- **Partido determinista por seed + log de comandos** → reproducible. Ver §5/§11.
- **Un solo widget para la cancha** con el Line API de Textual; capas = orden de
  dibujo, no widgets superpuestos. Ver §7.
- **Empezar minimalista e iterar.** La IA y las reglas se construyen de a poco.

## 3. Atributos del jugador (rediseño 1–100 float)

Reemplaza el set "estilo Hattrick" (7 skills 1–20) por uno pensado para tiempo
real. Objetivo: **los suficientes para simular, sin mil columnas**. Propuesta
(~16 de campo + 3 de arquero), todos `float` 1.0–100.0:

**Físicos (movimiento)**
- `speed` — velocidad máxima de carrera
- `acceleration` — qué tan rápido llega a esa velocidad / frena / gira
- `stamina` — resistencia; al bajar el `fitness` caen velocidad y precisión
- `strength` — duelos, aguantar la pelota
- `agility` — cambios de dirección, equilibrio
- `jumping` — alcance en el juego aéreo

**Técnicos (con la pelota)**
- `passing` — precisión y alcance del pase
- `shooting` — potencia y precisión del remate
- `dribbling` — control y conducción en velocidad
- `tackling` — robar / quitar
- `heading` — cabeceo

**Mentales (percepción y decisión)**
- `vision` — radio de percepción + calidad de decisión de pase (ver §6)
- `positioning` — ubicarse sin pelota
- `anticipation` — interceptar / leer la jugada
- `composure` — temple bajo presión (menos errores)
- `work_rate` — cuánto corre / cubre

**Arquero (solo GK)**
- `reflexes`, `handling`, `aerial_reach`

**Ocultos / meta:** `potential` (techo), `injury_proneness`, quizá
`consistency`. **Estado dinámico** (igual que hoy): `form`, `fitness`, `morale`,
`injury`, más posición(es) preferida(s).

Notas:
- El `overall` sigue siendo un promedio ponderado por posición (índice tipo
  TSI), ahora en escala 1–100.
- Se elimina `skills.py` (la escalera nombrada).
- Los **tiers por liga** se reescriben a escala 1–100 (ej. Liga A base ~78,
  Liga E base ~35), manteniendo offset por posición + talento + ruido.

## 4. Modelo de cancha y coordenadas

**Dos sistemas separados:**
- **Lógico (continuo):** la cancha mide ~`105 × 68` (metros). Jugadores y pelota
  tienen posición y velocidad `float` en este espacio. Toda la física/IA usa
  esto → movimiento suave y distancias reales.
- **Render (celdas):** el área jugable dentro del widget (~78×21) es la grilla
  visible. Una función mapea metros → celda al dibujar.

**Grilla tipo roguelike (`pitch.get(x, y)`):** útil, pero con matiz honesto: el
fútbol es **continuo**, no por casillas. Conviene un **híbrido**:
- Regiones/zonas (rectángulos o máscaras de celdas) para posiciones y zonas
  custom → ahí sí pensamos en celdas.
- Entidades (jugadores/pelota) en coordenadas continuas + helpers de consulta
  espacial (`entities_within(pos, radius)`), no un tile-grid puro.

**Zonas (dos conceptos distintos):**
- **Zona de movimiento:** región donde el jugador tiende a moverse según su rol
  (ej. lateral = banda). No excluyente: en casos extremos puede salir.
- **Área de visión:** radio (derivado de `vision`/`positioning`) que define qué
  percibe (pelota, rivales) y, por ende, a qué reacciona.
- **Zonas custom (futuro):** el usuario "pinta" celdas con un cursor para
  redefinir la zona de movimiento de un jugador seleccionado.

## 5. Motor de partido (simulación determinista)

Paquete nuevo `simulation/match/` (sin Textual):

```
simulation/match/
  field.py       # geometria de la cancha, mapeo metros<->celdas, zonas
  entities.py    # MatchPlayer (pos, vel, ...), Ball
  state.py       # MatchState: jugadores, pelota, marcador, reloj, fase
  engine.py      # MatchEngine.step(dt): un tick determinista
  commands.py    # ordenes del manager (cambio, mover zona, tactica) con tick
  events.py      # eventos del partido (gol, tarjeta, corner, lesion, ...)
  ai/            # percepcion -> decision -> steering (ver §6)
  replay.py      # grabar/reproducir (seed + log de comandos)
```

**Tick fijo, desacoplado del render.** El motor avanza en pasos fijos (ej.
`dt = 1/30 s` de tiempo simulado). El render corre a su propio FPS (ej. 15–20)
y, por frame, pide al motor avanzar los ticks que correspondan según la
velocidad de simulación (x1, x2, pausa).

**Determinismo:** todo el azar sale de un `random.Random` con seed. Las órdenes
del manager entran a una **cola de comandos** con el tick en que se aplican. Así
el partido = `seed + lista_de_comandos`. Reproducir = re-correr el motor con la
misma seed y los mismos comandos (no hace falta render). Es la técnica de
*lockstep* determinista de los juegos con replay.

## 6. IA de los jugadores (lo más difícil — minimalista primero)

Pipeline por jugador, por tick: **percibir → decidir → moverse**.

- **Percepción:** juntar entidades dentro del área de visión (pelota,
  compañeros, rivales).
- **Decisión (state machine simple / utilidad):**
  - Equipo CON pelota: el que la tiene puntúa *conducir / pasar / patear*; los
    demás hacen desmarques o sostienen su zona.
  - Equipo SIN pelota: el más cercano presiona; los demás marcan/cubren zona.
  - Pelota suelta: el más cercano la va a buscar.
- **Movimiento (steering behaviors):** `seek`, `arrive`, `pursue`, `separation`
  (no encimarse). Velocidad/aceleración máximas salen de `speed`/`acceleration`,
  moduladas por `fitness`.

**Arranque mínimo (v0):** ir a la pelota + pasar al compañero más libre + patear
si está cerca del arco + arquero que vuelve al arco. Después se suma: anticipar
pases (¿la pelota pasa cerca y suficientemente baja?), decidir pase corto/largo,
gambeta, faltas, etc. **Honestidad:** una IA de fútbol "completa" es enorme; la
clave es que cada comportamiento sea una función chica, determinista y testeable,
y sumarlos de a uno.

## 7. Render del partido en Textual (eficiencia)

Textual instalado: **8.2.7** (Line API disponible).

- **Un único `PitchWidget(Widget)`** que dibuja toda la cancha con el **Line
  API** (`render_line(y) -> Strip`), no muchos widgets hijos (un widget por
  jugador sería carísimo). Mantiene un buffer `(char, style)` por celda que se
  rearma desde `MatchState` cada frame; `render_line` devuelve la fila pedida.
- **Capas = orden de dibujo, no widgets superpuestos.** Se pinta: césped →
  líneas → jugadores → pelota (último, queda "arriba"). Cambiar el ícono del
  jugador (número → carita de ánimo `:)` → punto de color por resistencia) es
  cambiar **qué glifo/color** calcula el buffer según un `view_mode`, no
  superponer capas. Más simple y más barato.
- **Loop de animación:** `set_interval(1/fps, tick)` que avanza el motor y hace
  `self.refresh()` (o refresca solo la región sucia). El motor pesado o la
  generación corren en `run_worker(thread=True)` para no bloquear la UI.
- **Reactividad: con criterio.** `reactive` sirve para valores discretos del HUD
  (marcador, reloj, jugador seleccionado, `view_mode`) que al cambiar disparan
  un refresh chico. **No** para las ~1600 celdas de la cancha (eso va por el
  buffer + refresh manual).
- **Costo:** 22 agentes + pelota con steering simple a 30 ticks/s es trivial en
  CPU; redibujar 78×21 a 15–20 FPS con Strips es holgado. Si algún día pesa, se
  optimiza con región sucia y cache de líneas sin cambios.

## 8. Controles del manager en vivo

- Pausa / velocidad (x1, x2…).
- **Seleccionar jugador**: su número **titila**; con los cursores se ajusta su
  posición/zona "custom".
- Cambios, cambiar zona de un jugador, órdenes/táctica (ej. "arquero al área
  rival en un corner al final").
- Atajos para alternar `view_mode` (número / ánimo / resistencia).
- Ver ficha completa de un jugador en pleno partido.

## 9. Pantallas del partido (full-screen, 80×25)

Como hay poco espacio, son **pantallas completas que se alternan** (estilo ADOM,
igual que las secciones de gestión):
- **Cancha** (la vista en vivo).
- **Estadísticas en vivo**: posesión, tiros (al arco), corners, faltas, fueras
  de juego, laterales, etc.
- **Eventos clave**: línea de tiempo de goles, tarjetas, lesiones, tiros libres…
  (no es el texto de simulación de Hattrick; son hitos marcados en el tiempo).

## 10. Generación de nombres (dataset real por nacionalidad)

- **Source:** `datasets/names/data/<ISO2>.csv` (105 países, formato
  `first_name,last_name,gender,country_code`). ~10GB, **gitignored** (es source
  local, no se distribuye).
- **Estrategia de distribución:** un **paso de build** destila el 10GB en una
  base compacta y versionable (ej. SQLite o CSV chico con N miles de nombres y
  apellidos por país relevante → pocos MB) que SÍ se commitea/distribuye. El
  juego usa esa base, no el 10GB.
- **Muestreo:** determinista por seed. Sobre la base compacta es trivial; sobre
  el CSV grande se puede muestrear por *seek* a offset de byte aleatorio (sin
  cargar el archivo).
- **Nacionalidad:** alinear los códigos de país del juego a **ISO alpha2**
  (AR, BR, ES…) para usar directo el CSV del país.

## 11. Persistencia y reproducibilidad

- **Mundo y partida:** SQLite detrás de `SaveRepository` (interfaz), cifrado
  enchufable después (decisión previa). Todo lo aleatorio nace de la seed.
- **Partidos:** se guardan como `seed + log de comandos` → se re-juegan idénticos
  (incluye las órdenes del manager). **Caveat honesto:** la reproducción exacta
  con `float` está garantizada en la **misma máquina/plataforma**; entre
  plataformas distintas pueden aparecer mínimas derivas de punto flotante. Si
  algún día hace falta replay 100% cross-platform, se pasa a aritmética de punto
  fijo (entero). Por ahora, floats.

## 12. Herramientas / librerías

- **No agregar** un motor de juego ni `numpy` todavía: 22 agentes en Python puro
  rinden de sobra; `numpy` no aceleraría algo que no es cuello de botella y suma
  dependencia. Se reevalúa con profiling si hace falta.
- **No ECS.** Un *entity-component-system* es overkill para 22 entidades y
  complica el mantenimiento; alcanza con dataclasses + funciones claras.
- **Vec2 propio** (pequeña clase de vector 2D) en vez de `numpy`.
- Ya en uso: Textual, pytest. Futuro: SQLCipher/`cryptography` (cifrado),
  quizá `orjson`/`msgpack` para saves.

## 13. Honestidad: límites y riesgos

- **Resolución gráfica:** 80×25 es **grueso**. El movimiento se ve "a saltos" de
  celda; las posiciones `float` mejoran la lógica y el timing, no la resolución
  visual. Es parte del encanto roguelike, pero conviene tenerlo claro.
- **IA realista = mucho trabajo.** Hay que resistir la tentación de modelar todo
  de una; v0 minimalista y sumar.
- **Determinismo float cross-platform:** ver §11.
- **Distribución del dataset:** el 10GB no se distribuye; depende del paso de
  destilado (§10).

## 14. Roadmap por fases (urgente primero)

**Fase A — Fundaciones (refactor ahora para no rehacer después)**
1. Rediseñar atributos a 1–100 `float` + nuevo set (§3); actualizar `Player`,
   generadores y tiers; borrar `skills.py`; actualizar tests.
2. Códigos de país a ISO alpha2 + integrar dataset de nombres (destilado +
   loader por nacionalidad).
3. Módulo de cancha/coordenadas (`field.py`): metros ↔ celdas, regiones/zonas.

**Fase B — Motor de partido (headless, determinista)**
4. `MatchState`/entidades, `MatchEngine.step(dt)`, RNG seed, cola de comandos.
5. Movimiento (steering) + IA v0 (ir a pelota / pase / remate) + goles + saques.
6. Replay (seed + comandos) + tests de determinismo.

**Fase C — UI del partido**
7. `PitchWidget` (Line API + view modes + pelota arriba).
8. `MatchScreen` (loop async, reloj/marcador, pausa/velocidad).
9. Controles del manager (seleccionar/titilar, zonas custom, cambios, eventos
   clave, stats en vivo).

**Fase D — Profundidad**
10. Tarjetas, faltas, pelota parada, lesiones, fuera de juego.
11. Gestión: calendario/eventos, entrenos (usan la granularidad `float`).

## 15. Backlog de ideas futuras

Afinidad entre jugadores (sacar a uno afecta la moral del que queda); moral del
equipo por resultados y otros factores; **clima** (afecta público y el propio
partido); sponsors/patrocinios; mercado de pases; valor de mercado; hinchada;
infraestructura del estadio que recauda; etc.

## 16. Preguntas abiertas

- Set exacto de atributos (§3): ¿ajustamos la lista antes de implementarla?
- Tamaño de la base de nombres destilada (cuántos por país) y formato (SQLite vs
  CSV chico).
- Velocidades de simulación a ofrecer (x1/x2/x4) y FPS de render objetivo.
- ¿Cuántos jugadores por equipo en cancha al inicio (11 reales vs reducido para
  v0)?
