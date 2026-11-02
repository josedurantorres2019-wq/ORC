# Verificación del código ORC contra los papers, EES y DWSIM

*Corrida: 2026-11-01. Revisión de advertencias y fallas, y corrida final: 2026-11-02.*

> **El código y EES reproducen los papers. Solo queda abierta una falla: VP-04 (Yari, R1234yf), con Ẇ_net −3,5 %.** Su origen está localizado en ṁ, pero su causa no se identificó. VP-05 quedó explicado: la diferencia está en las propiedades del isobutano del libro. Las desviaciones de DWSIM son de la herramienta y se probaron aisladas; no vienen del modelo ni de los datos.

## Estado final

| Herramienta | Puntos | Frente al paper | Frente al código | Veredicto |
|---|---|---|---|---|
| Código (Python + CoolProp) | 11 + VP-02 | 25 pasan, 4 explicadas, **1 falla (VP-04)** | — | ✅ |
| EES V10.228 | 11/11 | igual que el código | 115 pasan, 44 explicadas por la EoS | ✅ |
| DWSIM 8.3.4, CoolProp | 11/11 | solo VP-01, VP-05 y VP-06 cerca | falla en estados saturados | ❌ como verificación |
| DWSIM 8.3.4, Peng-Robinson | 10/11 | n-butano, isobutano y amoníaco dentro de ~1 % | falla en la bomba con R134a, R152a, MM y R1234yf | ⚠️ parcial |

La corrida final reprodujo los resultados anteriores **sin ninguna diferencia** (0,0 en W_net) en EES y en los dos paquetes de DWSIM. Pruebas: 107 pasan, más el benchmark (`-m corrida`): 18 pasan y VP-04 queda como xfail estricto.

## Contra el paper: W_net (o W_el) en kW

| Punto | Paper | Código | EES | DWSIM-CoolProp | DWSIM-PR |
|---|---|---|---|---|---|
| VP-03 Yari, n-butano | 1450 | −0,08 % | +0,01 % | +44 % | −0,05 % |
| VP-C-isobutano (Yari) | 1479 | −0,14 % | −0,16 % | −89 % | −0,85 % |
| VP-C-propano (Yari) | 1635 | −0,06 % | −0,18 % | +3,1 % | −3,8 % |
| VP-C-R134a (Yari) | 1448 | −0,22 % | −0,22 % | +50 % | +26 % |
| VP-C-R152a (Yari) | 1476 | −0,26 % | +0,12 % | +11 % | +409 % |
| VP-C-amoniaco (Yari) | 1377 | −0,08 % | −0,07 % | +4,9 % | +0,97 % |
| VP-06 Bombarda, MM + recuperador (W_el) | 1603 | +0,04 % | +0,54 % | +1,2 % | +1,6 % |
| VP-01 Çengel 10-1, agua (η) | 0,26 | +0,08 % | +0,09 % | +0,40 % | −3,4 % |
| VP-05 Çengel 10-29, isobutano | 6140 | +0,67 % ᵃ | +0,51 % ᵃ | +0,63 % ᵃ | −0,88 % |
| VP-13 Campos, n-butano | 32 | −3,1 % ᵇ | −3,0 % ᵇ | +13 % | −3,3 % |
| **VP-04 Yari, R1234yf** | 1816 | **−3,5 %** ᶜ | **−3,2 %** ᶜ | +29 % | error |

ᵃ Explicado (→ 1). ᵇ Los 32 kW de la tesis son la potencia de la turbina; el código da W_t = 32,47 kW (+1,5 %). ᶜ Falla abierta (→ 2).
Todas las variables con su veredicto están en [`reporte_tablas.md`](reporte_tablas.md) y en [`comparacion_herramientas.csv`](comparacion_herramientas.csv).

## Análisis de cada falla y advertencia

### 1. VP-05 (Çengel 10-29): explicado por la EoS del libro

- El enunciado (p. 600, revisado en el PDF) **fija los dos estados de la turbina**: entrada a 3,25 MPa y 145 °C, salida a 400 kPa y 80 °C. Por eso w_t = h3 − h4 depende solo de las propiedades del isobutano; el modelo no interviene.
- Con las respuestas del libro (6,14 MW y 105,5 kg/s), su w_t sale entre **63,9 y 64,1 kJ/kg**. CoolProp da 64,49 y EES V10 64,41. El libro usó las propiedades del EES de su edición.
- El Q_in del código (50,39 MW) cae dentro del rango que implica el libro (50,1–50,6 MW), así que el balance de la fuente cuadra.
- La causa quedó escrita en `01_referencias/casos/cengel_cap10.yaml`, con su evidencia.

### 2. VP-04 (Yari, R1234yf): falla abierta, localizada en ṁ

- **η coincide** (+0,05 pp, dentro de la tolerancia). Como W = η·Q_in, la diferencia está en Q_in, es decir, en ṁ.
- Para dar 1816 kW, el ṁ de Yari tendría que ser 3,6 % mayor. Con las propiedades de CoolProp, eso equivale a un pinch de **9,1 K**; nuestro pinch cae en el punto de burbuja con 10,0 K, como dice el paper.
- **La causa que estaba anotada («EoS de EES 2015») queda refutada.** EES V10 da −3,2 %, y su calor latente a 84 °C es 0,8 % **mayor** que el de CoolProp, en el sentido contrario al necesario.
- Hipótesis no verificadas:
  1. Yari usó otro valor de las propiedades del R1234yf cerca de su T_c (94,7 °C), donde el latente es solo de 70 kJ/kg.
  2. Yari aplicó el pinch de otra forma para este fluido.
- Queda como falla (xfail estricto en `tests/test_benchmark_papers.py`). La nota está en `yari2015_orc_tabla6.yaml`.

### 3. DWSIM con CoolProp: falla en los estados saturados

- **Prueba aislada, hecha toda dentro de DWSIM** (n-butano, 933 kPa): con vapor sobrecalentado, DWSIM da la misma h que CoolProp.
- En cambio, el vapor saturado (definido por P y fracción de vapor = 1) sale 3,2 kJ/kg corrido, y la expansión isentrópica desde él da **53,6 kJ/kg**. CoolProp da 37,2 y DWSIM-PR 37,4.
- En Yari, Bombarda y Campos la entrada a la turbina es vapor saturado y la de la bomba es líquido saturado. Por eso esos puntos salen mal.
- Los que no tienen la entrada a la turbina saturada cuadran: VP-05 y VP-01.

### 4. DWSIM con Peng-Robinson: falla en la bomba con algunos fluidos

- **Prueba aislada de la bomba** (líquido 0,5 K subenfriado, de P_cd a P_ev):
  - Con R134a, MM y R1234yf, T2 sale exactamente **298,15 K**, el valor por defecto de DWSIM: el flash no converge.
  - Con R152a, w_p = 22,0 kJ/kg (CoolProp 1,8).
  - Con n-butano sale bien.
- Cambiar el algoritmo de flash (SingleCompFlash, NestedLoops) no lo corrige.
- Donde la bomba funciona, PR queda a ~1 % del paper, lo esperable por cambiar de EoS.

### 5. EES frente al código: solo la EoS

- En cada punto, la diferencia de Q_in entre EES y el código es igual a la diferencia de Δh entre los reservorios calculada solo con propiedades. Ejemplos: R152a +0,41 % y +0,41 %; MM +0,40 % y +0,33 %; T_sat del MM −0,83 K.
- Los lazos de EES cierran con residuos < 1e-8.

## Pendientes

1. VP-04: buscar en Yari (o en su versión de EES) qué propiedades o qué pinch usó para el R1234yf.
2. DWSIM sirve solo para puntos sin estados saturados y con fluidos cuya bomba funciona en PR. Para verificar en DWSIM habría que definir puntos con sobrecalentamiento y subenfriamiento.
3. EES: los lazos podrían resolverse de forma simultánea con `$VarInfo ... Guess=` en lugar del PROCEDURE, para verificar también el método numérico.

## Archivos de soporte (para mostrar)

| Carpeta | Contenido | Cómo abrirlo |
|---|---|---|
| `ees/archivos_ees/` | 11 archivos `.EES` ya resueltos, uno por punto | doble clic en EES; ventana Solution |
| `ees/puntos/` | el mismo programa en texto (`.txt`) y su salida CSV | EES → Open, o cualquier editor |
| `dwsim/puntos/` | 21 diagramas `.dwxmz` resueltos (`<punto>_coolprop` y `<punto>_pr`) | DWSIM → Open |

En los `.dwxmz`, los calores de los Heater/Cooler quedaron fijos con el valor del lazo ya convergido. Si se recalcula en DWSIM, da el mismo estado. Las corrientes AUX son las auxiliares de la guía, a (P_ev, T_fuente) y (P_cd, T_sumidero).

*Fuente: corridas del 2026-11-01 y del 2026-11-02 con EES V10.228 Professional, DWSIM 8.3.4 y CoolProp. Las entradas son las de `entradas_puntos.csv` (sacadas de cada paper). Revisé en los PDF el enunciado de Çengel 10-29 y la Tabla 6 de Yari. No verificado: la causa de VP-04 y por qué falla el flash de DWSIM.*
