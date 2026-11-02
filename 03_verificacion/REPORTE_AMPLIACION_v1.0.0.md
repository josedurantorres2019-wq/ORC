# Ampliación de la verificación sobre el código v1.0.0

*2026-11-02. Plan en la bóveda: `04_PROJECTS/active/Ciclo ORC/plan/PLAN_VERIFICACION_AMPLIACION_v1.0.0_2026-11-02.md` (decisiones A-1…A-5 aprobadas).*

> **El código v1.0.0 resiste las ocho familias de pruebas nuevas, y ningún resultado apunta a un error del modelo.**
>
> - **Óptimo de T3:** reproduce el de Yari en los 7 fluidos (T3* ±0,62 K, Ẇ_max ±0,26 %).
> - **Curvas de la Fig. 5:** coincide punto a punto en 64 de 70, contando los explicados.
> - **Estados:** coincide estado por estado con Çengel.
> - **Lazos:** convergen en todo el rango probado.
> - **Método numérico:** da lo mismo resuelto por Newton simultáneo en EES.
>
> Quedan **dos hallazgos para la v1.0.1** (H-1 y H-2, § 3). VP-04 sigue abierto, pero su causa quedó acotada a las propiedades del R1234yf que usó Yari.

**Regla de congelamiento cumplida:** `git diff v1.0.0 -- src scripts/*.py` vacío. Todo lo nuevo son archivos nuevos: casos YAML, `scripts/v1/`, pruebas y la plantilla de EES simultánea.

## 1. Estado por familia

| Familia | Qué se probó | Resultado |
|---|---|---|
| F1 · Puntos nuevos | Çengel Ej. 10-3 a/b/c, Prob. 10-26; Vera R113 (V5) | 11/11 de Çengel pasan. Vera: bomba +0,19 % (pasa); Ẇ_eje +0,74 %, explicado por el redondeo de sus presiones (F6) |
| F2 · Óptimo y tendencias | Yari Tabla 6 (T3 de Ẇ máxima), Fig. 5 completa (70 puntos digitalizados del PDF vectorial), Campos 2014 (sobrecalentamiento) | Óptimo: 7/7. Fig. 5: 59 pasan, 5 explicados, 6 fallan (todos del R1234yf = VP-04). Al subir T3, η sube y ṁ baja en los 7 fluidos. Con 0→20 K de sobrecalentamiento, Ẇ baja de 31,00 a 29,24 kW, como dice Campos |
| F3 · Estados | h1…h4, s3, x4 de Çengel Ej. 10-1 y 10-3 | 4/4 ciclos (h ±0,5 kJ/kg, x ±0,002) |
| F4 · Metamórficas | escala con ṁ, η_t ↑, ε_rec = 0, máquinas ideales, cierres de energía y exergía en 21 puntos | 84 pasan, 7 no aplican, 14 xfail por H-1 |
| F5 · Robustez del lazo | ε_cond de 0,50 a 0,999 (VP-03, VP-14); ε_rec de 0 a 0,99 (VP-06) | Todo converge: 4–18 iteraciones; estado 1 desde x = 0,40 hasta 56 K subenfriado; Q_rec creciente; sin saltos |
| F6 · Incertidumbre de entradas | Monte Carlo del redondeo de los datos publicados (400 muestras) | Yari: U95 ≤ 0,04 %; las tolerancias de ±0,5 % son sanas. Bombarda: U95 de 2,4–3,5 %, mayor que la tolerancia de ±2 % (el redondeo de 0,12 bar domina). Vera: U95 de 1,2 % |
| F7 · EES simultáneo (Newton) | los lazos resueltos por EES sin PROCEDURE | ver § 2 |
| F8 · VP-04 | ¿qué supuesto único da 1816 kW? ¿reproduce la forma de la curva? | Ninguno (§ 3) |

**Total contra los papers:** 51 pasan, 5 explicadas y 1 falla (VP-04), de 57 comparaciones.

## 2. EES simultáneo (F7)

EES resolvió los lazos (h1 y q_rec) con **Newton sobre el sistema completo**, sin el PROCEDURE de sustitución sucesiva. Los valores iniciales son los estados del código corridos por el desfase de entalpía de EES: no son la solución de EES, porque las EoS difieren.

| Resultado | Puntos |
|---|---|
| **Converge a la misma solución que el PROCEDURE** (ΔẆ, ΔQ_in y ΔT = 0 en las 9 cifras que exporta EES) | **17 de 22**: VP-01, 03, 05, 13, 14, 15, 16a/b/c, 17, C-isobutano, C-propano, C-R134a, C-amoniaco, T7-nbutano, T7-isobutano, T7-amoniaco |
| No converge (diálogo de error de EES) | VP-06 (MM con recuperador: la función `Min` del q_max no es derivable), VP-04 (R1234yf cerca de T_c), VP-C-R152a, VP-T7-R152a y VP-18 (R113) [causa no diagnosticada] |

**Conclusión:** donde los dos métodos convergen, el resultado no depende del método numérico. Eso verifica la sustitución sucesiva del código. Donde Newton no converge, no hay contradicción, solo falta de convergencia; el PROCEDURE de EES y el código sí resuelven esos 5 puntos.

## 3. Hallazgos

| ID | Qué | Evidencia | Destino |
|---|---|---|---|
| **H-1** | `recuperador.resolver` rechaza ε_rec = 0 con `CicloSinSolucionError` cuando T4 ≤ T2, aunque ε_rec = 0 significa que no hay recuperador | 14 de 20 puntos (F4). Donde T4 > T2, el resultado es idéntico a «sin recuperador» | v1.0.1: no evaluar el pinch del recuperador con ε_rec = 0 |
| **H-2** | Yari se contradice: la Tabla 6 da el máximo del R134a en 94,9 °C y 1448 kW, pero en su Fig. 5 ese es el **extremo** de la curva. El máximo de la figura está en 81,7 °C y 1581 kW | El código coincide con los dos datos: 1444,8 kW a 94,9 °C y máximo en 81,0 °C, 1579 kW | Es del paper, no del código. Se registra en la nota de Yari |
| VP-04 | La diferencia del R1234yf crece suave de −0,7 % a 65 °C hasta −3,5 % a 84 °C al acercarse a T_c | F8: ningún supuesto único reproduce la curva. El pinch de 9,06 K arregla los 84 °C pero deja +1,4 % a 65 °C; η_t y T_cond quedan peor | Sigue como falla. Causa más probable: las propiedades del R1234yf de Yari cerca de T_c [NV] |

**Métodos ajustados después de ver un resultado** (se dice para no ocultarlo):

1. **F2:** el barrido se limitó al rango de T3 que grafica Yari. Fuera de él, cerca de T_c, el supuesto de pinch en el punto de burbuja produce un artefacto (ṁ → ∞ cuando el latente → 0).
2. **F2:** en los puntos de 109 °C se agregó la incertidumbre de lectura en T3 (|dẆ/dT3|·0,2 °C). Esos 4 puntos quedan como «explicado».
3. **F6:** las T de condensación de Yari (40 °C) y Campos (37 °C) eran supuestos exactos, no datos redondeados, y se sacaron del Monte Carlo.
4. **Causas de T7-R152a, VP-05 y VP-18:** se encontraron después de su corrida. Ninguna tolerancia se cambió.

## 4. Archivos

| Archivo | Qué es |
|---|---|
| `01_referencias/casos/cengel_cap10_ampliacion.yaml`, `vera2018_r113.yaml` | casos nuevos (F1) |
| `01_referencias/casos/yari2015_fig5_digitalizada.csv` | Fig. 5 de Yari digitalizada de los marcadores vectoriales del PDF |
| `scripts/v1/barrido_optimo_T3.py` | F2 → `v1/optimo_T3.csv`, `v1/curvas_fig5.csv`, `v1/tendencias.csv` |
| `scripts/v1/robustez_lazo.py` | F5 → `v1/robustez_lazo.csv` |
| `scripts/v1/correr_ees_simultaneo.py` + `ees/orc_modo_R_simultaneo.txt` | F7 → `v1/ees_simultaneo.csv`, `ees/simultaneo/` |
| `scripts/v1/sensibilidad_vp04.py` | F8 → `v1/sensibilidad_vp04.csv` |
| `scripts/v1/incertidumbre_entradas.py` | F6 → `v1/incertidumbre_entradas.csv` |
| `scripts/v1/correr_herramientas_extra.py` | corre EES y DWSIM con R113 sin editar los scripts congelados |
| `tests/test_estados_cengel.py`, `tests/test_metamorficas_v1.py` | F3 y F4 |

*Fuente: corridas del 2026-11-02 sobre el commit etiquetado `v1.0.0`, con CoolProp, EES V10.228 y DWSIM 8.3.4. PDF revisados: Çengel cap. 10 (pp. 564, 570-572, 599) y Yari 2015 (Tablas 6-7, Fig. 5). No verificado: la causa de VP-04.*
