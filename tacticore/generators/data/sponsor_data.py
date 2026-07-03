"""Datos crudos para generar marcas patrocinadoras de fantasia (ASCII).

Una marca sale de combinar una raiz con un sufijo (ej. "Nortex", "Delcorp") y se
le asigna un RUBRO/sector de la lista (solo sabor para mostrar). Nada real: todo
inventado, al estilo del resto del mundo del juego.
"""

# Raices de marca (nucleo del nombre).
BRAND_ROOTS = [
    "Nor", "Vel", "Tri", "Zen", "Alba", "Cor", "Fort", "Lumen", "Vertex", "Prima",
    "Astra", "Delta", "Nova", "Orbe", "Quantum", "Sol", "Ferro", "Aqua", "Terra",
    "Vento", "Cima", "Roca", "Faro", "Nimbo", "Krono", "Onda", "Pulso", "Rayo",
    "Ancla", "Brio",
]
# Sufijos de marca (terminacion corporativa).
BRAND_SUFFIXES = [
    "tex", "corp", "sa", "group", "nova", "fon", "energy", "tech", "line", "max",
    "plus", "co", "one", "labs", "prime",
]

# Rubros posibles de la marca (etiqueta que se muestra).
SECTORS = [
    "Bebidas", "Banca", "Telefonia", "Energia", "Seguros", "Automotriz",
    "Aerolinea", "Tecnologia", "Indumentaria", "Alimentos", "Turismo", "Logistica",
]
