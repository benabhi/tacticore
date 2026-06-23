# Tacticore

Juego de manager de fútbol de fantasía para la terminal, hecho con
[Textual](https://textual.textualize.io/). Mundo generado proceduralmente
(sin equipos ni jugadores reales), pensado para correr en cualquier terminal
al estilo de los roguelikes clásicos: 80×25, solo ASCII y colores ANSI.

## Instalación

```bash
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Correr

```bash
python main.py            # equivalente: python -m tacticore
```

## Nombres por nacionalidad (dataset)

Los nombres y apellidos se generan por país a partir de **pools compactos**
(`tacticore/generators/data/names/<CODIGO>.json`) que **sí están commiteados**:
el juego corre **sin** descargar nada. Esos pools se destilan de un dataset
grande de nombres reales (solo como fuente; los jugadores son de fantasía,
mezclando nombre + apellido).

**Para (re)generar o ampliar esos JSON** (por ejemplo al agregar países o subir
el `TOP_N` para más variedad) hace falta el **dataset completo** (~3 GB,
**no** versionado):

1. Descargarlo desde:
   <https://drive.google.com/file/d/1QDbtPWGQypYxiS4pC_hHBBtbRHk9gEtr/view?usp=sharing>
2. Descomprimirlo y dejar los CSV por país en `datasets/names/data/`, de modo
   que queden archivos como `datasets/names/data/AR.csv`, `BR.csv`, etc. (una
   fila por persona: `first_name,last_name,gender,country_code`).
3. Correr el destilador, que reescribe los JSON compactos:

   ```bash
   python scripts/build_name_pools.py
   ```

Sin ese dataset, el destilador no encuentra los CSV y avisa qué países omite;
**no es necesario para jugar**, solo para regenerar los pools.

Para las directivas y la arquitectura del proyecto ver [CLAUDE.md](CLAUDE.md).
