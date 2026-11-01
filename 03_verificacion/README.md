# Verificación cruzada con EES y DWSIM

Plan: bóveda, `04_PROJECTS/active/Ciclo ORC/plan/PLAN_VERIFICACION_ORC_2026-10-31.md`.

| Archivo | Qué es |
|---|---|
| `entradas_puntos.csv` | Entradas en modo R de cada punto (las mismas del Python). Se regenera con `python -m scripts.comparar_verificacion --entradas 03_verificacion/entradas_puntos.csv` |
| `ees/orc_modo_R.txt` | Programa de EES (ecuaciones de D-15/D-16, escritas desde el modelo) |
| `dwsim/GUIA_DWSIM.md` | Cómo armar el diagrama equivalente en DWSIM |

## Pasos

1. Correr cada punto de `entradas_puntos.csv` en EES y en DWSIM (CoolProp y Peng-Robinson).
2. Exportar los resultados a CSV, uno por herramienta:
   - `ees/resultados_ees.csv`
   - `dwsim/resultados_dwsim_coolprop.csv`
   - `dwsim/resultados_dwsim_pr.csv`
3. Con esos CSV, el código los compara contra las corridas de Python y llena la hoja `verificacion` del Excel único (herramienta = EES, DWSIM-CoolProp o DWSIM-PR). Ninguna cifra se copia a mano.

## Columnas de los CSV de resultados

`id_punto, W_net, W_t, W_p, Q_in, Q_out, Q_rec, eta, dh_s, T1, T2, T3, T4, x4, eta_II`

Unidades: kW, kJ/kg, K. **No incluir h ni s absolutas**: cada programa tiene su propio estado de referencia.

## Manifiesto (anotar en `ees/manifiesto.yaml` y `dwsim/manifiesto.yaml`)

Versión del programa, nombre del fluido y de su ecuación de estado, paquete de propiedades, fecha y quién corrió.
