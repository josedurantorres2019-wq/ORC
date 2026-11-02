# Verificación del código ORC contra los papers, EES y DWSIM (2026-11-01)

> **El código reproduce los papers y EES reproduce al código.** El código pasa 25 de 29 comparaciones con los papers, 3 tienen la causa documentada y falla 1 (VP-05, W_net +0,67 %, igual en las tres herramientas). EES coincide con el código en W_net dentro de **0,5 %** en los 11 puntos, y toda la diferencia viene de sus propiedades, no de las ecuaciones. **DWSIM no sirve como verificación con estos puntos**: su flash falla justo en saturación (CoolProp) y da resultados sin sentido físico en 3 puntos (PR).

## Estado

| Herramienta | Puntos | Frente al paper | Frente al código | Veredicto |
|---|---|---|---|---|
| Código (Python + CoolProp) | 11 + VP-02 | 25 pasan, 3 explicadas, 1 falla | — | ✅ |
| EES V10.228 | 11/11 | igual que el código (1 falla: VP-05) | 115 pasan, 44 explicadas por EoS, 0 sin causa | ✅ |
| DWSIM 8.3.4, CoolProp | 11/11 | solo VP-01 y VP-05 cerca (≤ 0,6 %) | 86 pasan, 61 explicadas (flash), 13 fallan | ❌ |
| DWSIM 8.3.4, Peng-Robinson | 10/11 (VP-04 da error) | 4 Yari dentro de ~1 %; R134a y R152a sin sentido | 94 pasan, 8 explicadas, 44 fallan | ⚠️ |

## Riesgos y hallazgos

1. **VP-05 (Çengel 10-29) falla en las tres herramientas.** Código +0,67 %, EES +0,51 %, DWSIM-CoolProp +0,63 %, con estados lejos de la saturación. Al coincidir motores independientes, la causa probable está en las entradas sacadas del libro (η_t derivada de T4 = 80 °C) o en el redondeo del libro. **No verificado.**
2. **El flash PH del paquete CoolProp de DWSIM falla en saturación.** Con la h de vapor saturado de CoolProp, DWSIM da fracción de vapor 0,990 en vez de 1, y la expansión sale 53,1 kJ/kg contra 37,2. Los estados 1 y 3 de casi todos los papers son saturados. Comprobado solo con n-butano; para los demás fluidos es inferido.
3. **DWSIM-PR da resultados sin sentido físico** en VP-06 (MM), VP-C-R134a (η = 0,76) y VP-C-R152a (η = 1,81), y falla con un error en VP-04 (R1234yf). La causa no se buscó.
4. **Las diferencias entre EES y el código son de EoS.** En cada punto, la diferencia de Q_in es igual a la de Δh entre los dos reservorios calculada solo con propiedades (R152a +0,41 % y +0,41 %; MM +0,40 % y +0,33 %; T_sat del MM −0,83 K). Superan la tolerancia de ±0,1 % y ±0,1 K en MM, R152a y R1234yf.

## Contra el paper: W_net (o W_el) en kW

| Punto | Paper | Código | EES | DWSIM-CoolProp | DWSIM-PR |
|---|---|---|---|---|---|
| VP-03 n-butano (Yari) | 1450 | 1448,8 (−0,08 %) | 1450,1 (+0,01 %) | 2092,5 (+44 %) | 1449,3 (−0,05 %) |
| VP-04 R1234yf (Yari) | 1816 | 1752,8 (−3,48 %)ᵃ | 1758,3 (−3,18 %)ᵃ | 2336,7 (+29 %) | error |
| VP-C-isobutano (Yari) | 1479 | 1476,9 (−0,14 %) | 1476,6 (−0,16 %) | 165,7 (−89 %) | 1466,4 (−0,85 %) |
| VP-C-propano (Yari) | 1635 | 1634,1 (−0,06 %) | 1632,1 (−0,18 %) | 1685,8 (+3,1 %) | 1573,3 (−3,8 %) |
| VP-C-R134a (Yari) | 1448 | 1444,8 (−0,22 %) | 1444,8 (−0,22 %) | 2164,7 (+50 %) | 1821,8 (+26 %) |
| VP-C-R152a (Yari) | 1476 | 1472,1 (−0,26 %) | 1477,8 (+0,12 %) | 1636,7 (+11 %) | 7506,2 (+409 %) |
| VP-C-amoniaco (Yari) | 1377 | 1375,9 (−0,08 %) | 1376,0 (−0,07 %) | 1444,9 (+4,9 %) | 1390,3 (+0,97 %) |
| VP-06 MM + recuperador (Bombarda), W_el | 1603 | 1603,6 (+0,04 %) | 1611,6 (+0,54 %) | 1622,8 (+1,2 %) | 1627,8 (+1,6 %)ᵇ |
| VP-13 n-butano (Campos) | 32 | 31,00 (−3,1 %)ᵃ | 31,04 (−3,0 %)ᵃ | 36,06 (+13 %) | 30,94 (−3,3 %)ᵃ |
| VP-05 isobutano (Çengel 10-29) | 6140 | 6181,1 (+0,67 %) | 6171,6 (+0,51 %) | 6178,6 (+0,63 %) | 6085,8 (−0,88 %) |
| VP-01 agua (Çengel 10-1), η | 0,26 | 0,2602 (+0,08 %) | 0,2602 (+0,09 %) | 0,2610 (+0,40 %) | 0,2513 (−3,4 %) |

ᵃ Causa documentada en el YAML del caso: VP-04, EoS de EES 2015 cerca de T_c; VP-13, los 32 kW de la tesis son potencia de turbina.
ᵇ El W_el de VP-06 en PR queda cerca, pero Q_out sale +69 %: el punto no es válido.

Todas las variables (η, Q_in, Q_out, Δh_s, ṁ) están en [`reporte_tablas.md`](reporte_tablas.md), y la tabla completa con errores y veredictos en [`comparacion_herramientas.csv`](comparacion_herramientas.csv).

## Comentario por herramienta

- **Código.** Reproduce los ciclos publicados de los tres fluidos del proyecto (n-butano, R1234yf y MM con recuperador) dentro de tolerancia o con causa documentada. Solo queda abierto VP-05.
- **EES.** Es una comprobación independiente de las ecuaciones y de las propiedades. Con las mismas entradas da el mismo ciclo; la diferencia máxima con el código es 0,49 % en energía y 1,47 K en T (MM), y sale íntegra de la EoS. Los lazos se iteran en un PROCEDURE de EES (sustitución sucesiva, como el código), porque un `.txt` no guarda valores iniciales y el sistema simultáneo no arranca desde 1. EES calcula los residuos de las ecuaciones originales del cierre, y todos dan < 1e-8.
- **DWSIM.** El diagrama con bloques (Pump, Heater, Expander, Cooler y el lazo como Recycle) funciona. Donde los estados no están en saturación, coincide: VP-05 con CoolProp da −0,04 % en W_net frente al código. Con los puntos de los papers, que están en saturación, no es concluyente por el flash. Con PR, los 4 puntos de Yari que sí convergen bien quedan dentro de ~1 % del paper, lo esperable por cambiar de EoS.

## Cómo se hizo

- **Entradas:** las mismas del código, sacadas de los papers (`01_referencias/casos/*.yaml` → `entradas_puntos.csv`). Ninguna se escribió a mano.
- **Sin exergía:** el estado muerto disponible venía del Kalina.
- **Agua (VP-01):** `'Water'` en EES; en DWSIM, los paquetes CoolProp y PR, sin IAPWS.
- **Tolerancias:** las del §7 del plan, aprobadas en V-D (`tolerancias.yaml`). Causas con su evidencia: `causas.yaml`.
- **Comandos:** `python -m scripts.correr_ees`, `python -m scripts.correr_dwsim`, `python -m scripts.comparar_herramientas --guardar` (387 filas en la hoja `verificacion` del Excel).

*Fuente: corridas del 2026-11-01 con EES V10.228 Professional, DWSIM 8.3.4 y CoolProp (código). No verificado: la causa de VP-05 y la de los resultados sin sentido de DWSIM-PR. El fallo del flash de DWSIM se probó solo con n-butano.*
