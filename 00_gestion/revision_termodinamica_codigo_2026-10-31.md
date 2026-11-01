# Revisión termodinámica del código ORC (2026-10-31)

Revisor: agente `validador-ingenieria`, independiente del autor del código. No modificó archivos.
Base: `src/` contra la formulación D-15 (bóveda, `plan/MODELO_MATEMATICO_ORC_2026-10-30.md`)
y contra CoolProp 8.0.0 `PropsSI`.

**Restricción respetada:** no se resolvió el ciclo con n-butano, R1234yf ni MM; no se corrió
`pytest -m corrida`. Los ciclos completos se probaron solo con agua (Çengel Ej. 10-1 y 10-7, y
casos genéricos). Con los fluidos del estudio solo se llamaron componentes sueltos con estados
genéricos.

## Veredicto: APROBADO CON CORRECCIONES. Las correcciones de código ya están aplicadas

| Módulo | Masa | Energía | Unidades y signos | Estados vs CoolProp | 2.ª ley |
|---|---|---|---|---|---|
| `coolprop_adapter` | — | — | OK | OK (ΔT = Δs = 0; fase y título correctos en 4 fluidos, también cerca de saturación y en supercrítico) | — |
| bomba / turbina | OK | OK | OK | OK (diferencia 0 frente a PropsSI) | OK |
| evaporador R / F | OK | OK (F: Q̇_in = ṁ_f c̄_p ΔT_f, error 0) | OK | OK | OK (ΔT_min = 10,000000 K con 40 y con 4000 tramos) |
| condensador R / F | OK | OK | OK | OK | OK (ver F1) |
| recuperador | OK | OK | **D2** | OK | **D1** → corregido |
| lazo del recuperador (R) | OK | N2 ≈ 1e-11 | OK | OK | OK (contracción, factor < 0,15) |
| Brent en T_cd (F) | OK | N2 ≈ 1e-16 | OK | OK | OK |
| exergía R / F | — | — | OK | — | Çengel: Ė_d,evap +0,05 %, Ė_d,cond −0,26 %, η_II del libro +0,09 %; cierre ≈ 1e-16 |
| restricciones | — | — | — | — | correspondencia con §4.1 correcta |

## Discrepancias y lo que se hizo

| # | Severidad | Problema | Estado |
|---|---|---|---|
| D1 | mayor | El q_max del recuperador (§2.3) usaba solo el lado caliente. Con ΔT_sc > 0 se cruzaban las temperaturas (T4 − T2r = −99 K en n-butano). | **Corregido** en `components/recuperador.py`: q_max = mín de los dos lados. Es una **desviación de D-15 §2.3 pendiente de aprobación**. Si el lado caliente limita, las dos fórmulas dan lo mismo. |
| D2 | mayor | Con T4 ≤ T2 (escape húmedo) el recuperador pasaba calor del lado frío al caliente y S4 no saltaba. | **Corregido:** `CicloSinSolucionError` en el recuperador; S4 se evalúa también con Q̇_rec < 0. |
| D3 | menor | Los puntos inexistentes salían como `ValueError` o `PropertyRangeError`. | **Corregido:** `src/errores.py` con `CicloSinSolucionError`, que ahora lanzan el evaporador F y el condensador. |
| D4 | menor | El modo F aceptaba a la vez T_cd y el agua finita. | **Corregido:** se exige uno solo de los dos. |
| D5 | menor | T_fpp se reportaba en la burbuja aunque el pinch estuviera en otro punto. | **Corregido:** T_fpp se toma en el punto que limita. |
| D6 | menor | La consola cp1252 de Windows fallaba al imprimir Δ, ṁ y −. | **Corregido** en `scripts/punto_modo_R.py`. |

## Problemas de la formulación (deciden el usuario y el profesor; no se tocó el código)

- **F1 (mayor).** En modo F, el cierre `T_sat(P_cd) = T_w2 + ΔT_pp,cd` no es el pinch cuando 4r
  llega sobrecalentado. El pinch real está en el punto de rocío, así que el cierre deja un ΔT real
  mayor (+1,7 / 5,2 / 10,6 K con 10 / 30 / 60 K de sobrecalentamiento). Eso sobreestima T_cd y
  subestima Ẇ_net. Propuesta: cerrar con `dT_min` del perfil, que ya se calcula, igual a
  ΔT_pp,cd. No afecta a Yari (T_cd dada) ni al modo R. Hoy el código sigue D-15 y reporta
  `dT_min_cd`.
- **F2.** Llevar a §2.3 el q_max de dos lados (D1).
- **F3 (menor).** La exergía de una fuente de c̄_p constante es exacta con ΔP = 0. El error está
  solo en el c_p de los gases (D-08).
- **F4 (menor).** Escribir en §2.4 el sumidero-reservorio que se usa cuando T_cd es dato (modo F).
  El código ya lo implementa y el cierre es una identidad.
- **F5 (menor).** O2 tiene dos definiciones: «ΔT_sc ≥ ΔT_sc,min» en §4.1 y
  «T_sat(P_cd) > T_amb_max» en el YAML y en el código. Además, S6 obliga a ΔT_sc ≤ ΔT_cd, de modo
  que con las sensibilidades del YAML (ΔT_sc de 8 a 20 K y ΔT_cd de 5 a 15 K) varias
  combinaciones salen INVIABLE.
- **F6 (menor).** En modo F, S8 contra 1 − T_w1/T_f1 es una cota débil. Sirve como filtro grueso.

## Pruebas

- Suite por defecto: **104 pasan, 9 deseleccionadas** (`corrida`).
- Las pruebas que se añadieron con agua (`tests/test_ciclo_agua.py`) cubren:
  - el lazo del recuperador;
  - el modo F con Brent y con T_cd dada;
  - la exergía del modo F;
  - las rutas de error.
- En `test_components.py` se añadieron pruebas de D1 y D2.
- **Pendiente, porque requiere corrida:**
  - `pytest -m corrida`, para la convergencia y los cierres con n-butano, R1234yf y MM;
  - el efecto de F1 en los benchmarks;
  - la comprobación «fluidos secos: T4 > T_sat(P_cd)».
