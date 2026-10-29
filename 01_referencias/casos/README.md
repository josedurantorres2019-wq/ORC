# Casos de referencia (F2a)

Un archivo `<id>.yaml` por caso publicado que el modelo ORC debe poder reproducir. Cada dato lleva
su procedencia: página/tabla del PDF y `origen`:

- `declarado`: el paper lo da explícitamente.
- `derivado`: se deduce de otros datos del paper (se dice cómo).
- `supuesto`: el paper no lo da; lo elegimos nosotros para poder correr el caso.

Las tolerancias de aceptación **no se fijan aquí** (decisión D-07). En `verificacion_previa` se
anota la desviación que dio un cálculo rápido con CoolProp, solo como información.

| Caso | Fuente | Uso | Reproducible |
|---|---|---|---|
| `yari2015_orc_tabla6` | Yari et al. 2015, Tabla 6 | benchmark ORC simple, 7 fluidos, agua 120 °C | Sí (±0,3 %, salvo R1234yf −3,5 %) |
| `bombarda2010_orc_mm` | Bombarda et al. 2010, Tabla 5 | benchmark ORC recuperado con MM, gases 346 °C | Sí en el ciclo; la fuente necesita c_p de gases |
| `campos2013_tabla4` | Campos Rodríguez et al. 2013, Tabla 4 | solo contraste de orden de magnitud | **No**: la tabla es incoherente con sus presiones |

Extracción completa y comentarios: bóveda de Obsidian,
`04_PROJECTS/active/Ciclo ORC/referencias/00_indice_papers_ORC.md`.
