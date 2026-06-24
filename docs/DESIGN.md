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
- **Selección de país en "nuevo juego" (pendiente):** al crear la partida,
  además del nombre del club, el jugador **elige el país**. Eso define en qué
  país arranca su club (en la liga E) y la nacionalidad de su cantera. La UI
  debe ser una **pantalla full-screen seleccionable, en varias columnas, sin
  scroll** (se planean muchos países al final del desarrollo; mantener la
  prioridad de pantallas completas estilo ADOM).

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
4. [hecho] `MatchState`/entidades, `MatchEngine.step(dt)`, RNG seed.
5. IA v0: [hecho] B3.1 steering (ir a pelota) · [hecho] B3.2 posesion/pase/
   remate · [hecho] B3.3 goles + saque tras gol + arquero que ataja/despeja.
6. [hecho] B4: Replay (seed + cola de comandos sellados por tick) + tests de
   determinismo (vivo y grabado dan el mismo partido). Comando concreto:
   `SetPlayerZone` (mover la zona de un jugador). Agregar una orden nueva =
   una dataclass `Command` con su `apply`.
   - [pendiente] **Sustitucion** como comando: necesita modelar el banco de
     suplentes en `MatchState` (hoy solo estan los que estan en cancha).

> **Tuning pendiente (no es B3.3):** la *tasa de goles* depende de constantes
> (alcance del arquero, velocidad/puntería del remate, presion). Hoy esta
> calibrada a ojo para que haya goles con variedad; el balance fino llega cuando
> existan marca/defensa de verdad y el arquero escale por atributos (Fase C/D).

**Fase C — UI del partido**
7. [hecho] `MatchPitch` (widget): dibuja jugadores (numeros por equipo) + pelota
   encima sobre la cancha; funciones puras + tests headless. Faltan view modes
   (cara de animo / color de stamina) y, si hace falta, pasar a Line API.
8. [en progreso] `MatchScreen`: loop con `set_interval`, HUD marcador/reloj,
   pausa (ESPACIO) y salir (Q). Demo: `scripts/watch_match.py`.
9. [pendiente] Controles del manager (seleccionar/titilar, zonas custom, cambios,
   eventos clave, stats en vivo) -> emiten comandos del motor (B4).

> **Diferido a pedido (NO olvidar):** se prioriza la jugabilidad del motor
> (abajo) antes de la UI de manager. Pendientes anotados para retomar:
> - **Velocidad ajustable** del partido (x0.5 / x1 / x2) en `MatchScreen`.
> - **Seleccion de jugador** (titila) que muestra su **dorsal/nombre real** en el
>   HUD (resuelve mostrar dorsales de 2 digitos sin pelear con la celda).
> - **Resaltar al que tiene la pelota** (mas alla del color, ej. fondo o marca).
> - Integrar `MatchScreen` al flujo del juego (hoy es una pantalla suelta).

**Fase G — Jugabilidad del partido (motor, PRIORIDAD ACTUAL)**

Se adelanta lo "jugable" del partido (parte de lo que estaba en Fase D) y se hace
**de a poco**, con pocos jugadores (7v7 actual, o menos) para iterar rapido. Cada
paso es determinista y testeable headless, y se mira con `watch_match.py`. Orden
por dependencias:

- **G0. Arbitro (presencia).** Una entidad mas en `MatchState` que **sigue la
  jugada a distancia**: se mueve hacia un punto offset de la pelota manteniendo
  una separacion (nunca la toca ni la disputa). Se dibuja como un **`@` amarillo**
  (color `REF` en la paleta). Determinista (deriva de la pelota), no afecta la
  simulacion. Primer paso chico y visible; arma el molde de "entidad no jugador"
  que despues usa la logica de faltas/offside (G4/G6).
- **G1. Salidas del campo + reanudaciones.** Hoy la pelota se frena al borde.
  Trackear el "ultimo toque" (que equipo). Lateral por la banda -> saque de banda
  del rival; por la linea de fondo -> corner (ultimo toque defensa) o saque de
  arco (ultimo toque ataque). Estado de "balon parado" + quien lo ejecuta.
  *Self-contained, no necesita la IA dura; arma el andamiaje de balon parado que
  reusan faltas y tiros libres.*
- **G2. Marca / defensa.** Hoy solo persigue 1 por equipo; el resto sostiene
  posicion. Que los defensores marquen/cubran al rival cercano -> mas jugadores
  en juego, intercepciones y pelotas sueltas a disputar. *Es el paso que mas
  "vivo" pone al partido (y el mas dificil): empezar minimal.*
  - **Modelo extensible (decidido):** la marca es una **asignacion por defensor**
    = `ZONA` (cuida area, engancha al que entra) o `MARCAR(rival)` (hombre a
    hombre). De ahi salen zonal / hombre / hibrido / doble-marca (varios al mismo
    rival), sin rehacer. La IA consulta "asignacion de este defensor": hoy
    siempre devuelve el **default automatico (zonal con enganche)**; mas adelante
    el manager la fija por **comando** `SetMarking(jugador, ...)` (estilo
    `SetPlayerZone`, replayable) desde la UI de tactica.
  - **Atributos (siempre):** `speed`/`acceleration` = velocidad de cierre;
    `positioning` = ubicacion goal-side; `anticipation` = reaccion/tightness;
    `work_rate` = radio de zona / cuanto sale a cubrir. `strength`/`tackling` =
    duelo y robo -> G4 (G2 solo posiciona y presiona, no roba).
- **G3. Pases cortos vs largos + intercepcion.** [hecho] El que tiene la pelota,
  presionado, elige corto (seguro) o largo (cambio de juego); el largo solo si
  tiene `vision`. El pase lleva error segun `passing` (mayor en los largos): un
  pase desviado se intercepta o sale (lateral) -> pelota a buscar. Resultado:
  los cambios de posesion saltaron de ~2 a ~31 en 5 min.
  - [hecho] **Desmarques (movimiento off-ball del ataque):** los atacantes sin
    pelota suben hacia el arco y buscan espacio (segun `work_rate`) mientras su
    equipo tiene la pelota. Subio de ~5.7 a ~8.5 de 14 jugadores en movimiento.
- **G4. Quite + faltas + tiros libres.** [hecho] Un defensor pegado al que lleva
  la pelota intenta el quite: exito (`tackling` vs `dribbling` +`strength`) gana
  la pelota ("Quite"); el fallo puede ser falta -> tiro libre del rival (reusa el
  balon parado de G1), o penal si la falta es dentro del area. Tarjetas mas
  adelante.
- **G5. Rebotes y pelotas sueltas "raras".** [hecho] El arquero ante un remate
  puede **atajar limpio** o dar **rebote** segun `handling`: la pelota queda viva
  y los atacantes (que suben con G3.x) la pelean -> segundas jugadas y goles de
  rebote. Eventos "Atajada"/"Rebote".
  - [pendiente, pulido] tiros que pegan en el palo (necesita geometria de palos),
    remates tapados por un defensor en la trayectoria, control fallido del que
    recibe. (Sabor extra; el grueso ya emerge.)
- **G6. Rarezas.** [hecho] **Offside** (al pasar a un companero adelantado al
  anteultimo defensor -> tiro libre indirecto de la defensa) y **mano**
  (extremadamente rara al controlar una pelota rapida -> tiro libre o penal del
  rival). Eventos "Offside"/"Mano".

**Fase D — Profundidad (resto)**
10. Tarjetas, lesiones (las faltas/pelota parada/offside se adelantan a Fase G).
11. Gestión: calendario/eventos, entrenos (usan la granularidad `float`).
12. **Cansancio en partido:** el `fitness` baja al correr/esprintar durante el
    partido y modula `max_speed` y la precisión de pase/remate (se nota el
    desgaste sobre el final). Hoy `fitness` esta fijo en 100.

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
- [resuelto] Jugadores por equipo: **11v11** (formacion 4-3-3, `FORMATION_11`).
  El 7v7 queda solo para pruebas.

## 17. Pendientes — checklist vivo (no perder)

Resumen unico de lo que falta. **Principio transversal:** toda conducta del
partido usa los **atributos** del jugador (no constantes uniformes).

**Jugabilidad del motor (Fase G) — prioridad actual.** Hecho: G0 arbitro, G1
reanudaciones, G2 marca zonal, G3 pases corto/largo, G3.x desmarques, G4
quite/faltas/tiros libres, G5 rebotes/atajadas del arquero, G6 offside/mano,
pausa de pelota muerta + reposicionamiento. Falta:
- [x] **Pelota muerta (pausa + reposicionamiento):** todos los balones parados
      (lateral, corner, saque de arco, falta, tiro libre, saque del medio tras
      gol, atajada del arquero) tienen una pausa (`_restart_timer`) durante la
      cual la pelota queda quieta y los jugadores se acomodan: el ejecutante
      camina hasta la pelota (linea/corner/punto), se arma **barrera** en tiros
      libres a media distancia, y el equipo que saca cerca del area se tira al
      ataque. Antes era instantaneo.
- [x] **11v11 + decision de ataque + arquero batible:** el juego arranca 11v11
      (4-3-3). El que ataca **se acerca** segun su `shooting` (mal definidor
      gambetea para llegar al area; `ai.shoot_range`) en vez de patear de 25m
      siempre; busca el **pase de gol** a un companero mejor ubicado, salvo que
      decida **jugarla individual** (mas probable en gambeteadores: `dribbling`
      vs `vision`). Y a un remate **se le puede escapar al arquero** aunque vaya a
      su glifo (segun `reflexes`/`handling`) -> posible gol (evento "escapa").
  - [x] **Distribucion del arquero con variantes:** saca corto a un companero
        libre (segun `passing`/`composure` y presion) o revienta largo. Ademas el
        arquero hace de **libero**: sube hacia el borde del area grande cuando su
        equipo ataca y vuelve a la linea al defender (puede quedar mal parado en
        un contragolpe). Arqueros en **magenta** (tono claro al tener la pelota).
  - [ ] **Pulido del balon parado (resto):** corners con corredores diferenciados
        (unos al primer palo/corto, otros al area por el largo); saque rapido "de
        sorpresa" como **orden** del manager (saltarse la pausa).
- [ ] **G5 pulido:** tiros al palo (geometria de palos), remates tapados por un
      defensor, control fallido del que recibe.
- [ ] **Arbitro en diagonal (pulido):** hoy sigue la pelota de frente a ~12m;
      los arbitros reales corren en diagonal y se mantienen a un costado para no
      entorpecer. Verificado: a lo largo recorre toda la cancha, pero a lo ancho
      queda en la franja central porque la pelota no se abre (mismo motivo que
      los pocos laterales/corners).
- [x] **Log de eventos estructurado (base):** `MatchState.log` acumula
      `MatchEvent(tick, clock, kind, team, player)` en cada momento (gol, remate,
      despeje, atajada, rebote, quite, falta, offside, mano, lateral, corner,
      saque de arco). `narration.narrate(event)` arma la linea de relato (ES,
      <=80) que se muestra en la fila de abajo del `watch_match`. Es el cimiento
      de stats en vivo y de la moral.
  - [ ] **Pendiente (relato rico):** variantes/aleatoriedad por evento, mas tipos
        (tarjetas cuando existan), `kind` de accion (chilena/cabezazo con el eje z),
        y metadata para stats (pases ok/err, remates al arco, etc.).
- [ ] **Juego aereo (eje z / altura de la pelota):** prerequisito para distinguir
      cabezazo / chilena / volea / centros / duelos aereos. Hoy la pelota es 2D
      sin altura; `heading`/`jumping`/`aerial_reach` ya existen pero no se usan.
      Las acciones a ras del piso (barrida vs quite de pie, remate colocado vs
      potente) se etiquetan barato con el log de eventos, sin necesidad del z.
- [ ] **Tarjetas y lesiones** (Fase D 10).
- [ ] **Cansancio en partido:** `fitness` baja al correr y modula `max_speed` y
      precision de pase/remate (hoy fijo en 100). (Fase D 12).
- [x] **Edad real (envejecimiento):** `Player` guarda `birth_date` + `nationality`;
      la edad se calcula contra la fecha del juego (`age_on(today)`), asi envejece
      solo al avanzar el calendario. Ver `scripts/show_squad.py`.
  - [ ] **Efectos de la edad (pendiente):** la edad modula la **velocidad de
        entreno** (jovenes suben mas rapido, cerca del `potential`) y el **declive**
        de atributos en veteranos (de a poco bajan). Mecanica indispensable.
- [ ] **Tuning de tasa de goles:** calibrar cuando exista quite real (G4) y el
      arquero escale por atributos. Hoy a ojo (ver nota en Fase B).

**UI del partido (Fase C) — diferido a pedido (retomar despues del motor).**
- [ ] **Velocidad ajustable** en vivo (x0.5 / x1 / x2) en `MatchScreen`.
- [ ] **Seleccion de jugador** (titila) que muestra su **dorsal/nombre real** en
      el HUD -> resuelve mostrar dorsales de 2 digitos sin pelear con la celda
      (hoy todos los jugadores son un solo glifo `@`; `player_glyph` quedo listo).
- [ ] **Resaltar al que tiene la pelota** mas alla del color (ej. fondo/marca).
- [ ] **View modes:** numero -> cara de animo -> color por stamina.
- [ ] **Controles del manager en vivo:** zonas custom, cambios, eventos clave,
      pantalla de stats en vivo -> todos emiten **comandos** del motor (B4).
- [ ] **Integrar `MatchScreen` al flujo del juego** (hoy es pantalla suelta que
      abre `scripts/watch_match.py`).

**Tactica / comandos (cuelgan de B4, replayable).**
- [ ] **`SetMarking(jugador, ZONA | MARCAR(rival))`:** marca manual hombre a
      hombre / hibrida / doble-marca (el "seam" `marking_assignment` ya existe).
- [ ] **Sustitucion como comando:** necesita modelar el **banco de suplentes** en
      `MatchState` (hoy solo viven los 7 en cancha).
- [ ] **Pateador de penales:** hoy el penal es **basico** (la pelota se planta en
      el punto y el atacante mas cercano remata; el arquero puede atajar). Falta:
      (a) **pateador por defecto** del equipo elegido en la tactica; (b) override
      **en vivo** para que el manager elija quien patea segun su criterio; (c)
      secuencia de penal de verdad (pateador vs arquero, resto fuera del area).

**Infra / pendientes tecnicos.**
- [ ] **Persistencia SQLite (+ encriptacion):** interfaz primero, cifrado despues.
- [ ] **Determinismo de floats cross-plataforma** para replays portables entre
      PCs: fixed-point o guardar checksum y caer a "ver resultado" si no matchea.
      (Hoy el replay es exacto en la misma maquina.)
- [ ] **Directiva 3 / paleta:** modo `TRUECOLOR=False` (fallback ANSI 16) para
      terminales viejas; default truecolor (ver `ui/palette.py`).

**Backlog de gestion / mundo (Fase D 11 y §15).** Calendario/eventos, entrenos;
afinidad entre jugadores, moral, clima, sponsors, mercado de pases, valor de
mercado, hinchada, infraestructura del estadio. Nacionalidad selectable en la
pantalla de nuevo juego (meter al equipo en la liga del pais).
