# Verificación cruzada con EES y DWSIM

Plan: bóveda, `04_PROJECTS/active/Ciclo ORC/plan/PLAN_VERIFICACION_ORC_2026-10-31.md`.
Resultado de la primera corrida: [`REPORTE_VERIFICACION_2026-11-01.md`](REPORTE_VERIFICACION_2026-11-01.md).

| Archivo | Qué es |
|---|---|
| `entradas_puntos.csv` | Entradas en modo R de cada punto (las mismas del Python, sacadas de los papers). Se regenera con `python -m scripts.comparar_verificacion --entradas 03_verificacion/entradas_puntos.csv` |
| `ees/orc_modo_R.txt` | Programa base de EES (ecuaciones de D-15/D-16; lazos en el PROCEDURE `lazo`) |
| `ees/puntos/` | Un programa de EES por punto y su salida (los genera `scripts/correr_ees.py`) |
| `ees/archivos_ees/` | **Soporte:** los mismos puntos como archivos `.EES` ya resueltos, para abrirlos en EES |
| `dwsim/GUIA_DWSIM.md` | Diagrama equivalente en DWSIM (lo arma `scripts/correr_dwsim.py`) |
| `dwsim/puntos/` | **Soporte:** diagramas `.dwxmz` resueltos, uno por punto y paquete (CoolProp, PR), para abrirlos en DWSIM |
| `tolerancias.yaml` | Tolerancias Python ↔ herramienta (§7 del plan, V-D) |
| `causas.yaml` | Causas documentadas de las diferencias fuera de tolerancia, con su evidencia |
| `comparacion_herramientas.csv`, `reporte_tablas.md` | Paper, código y herramientas por punto y variable (los genera `scripts/comparar_herramientas.py`) |

## Pasos (desde la raíz del repo)

1. `python -m scripts.correr_ees` → `ees/resultados_ees.csv` (EES sin interfaz: `EES.exe <prog> /solve`).
2. `python -m scripts.correr_dwsim` → `dwsim/resultados_dwsim_coolprop.csv` y `dwsim/resultados_dwsim_pr.csv`.
3. `python -m scripts.comparar_herramientas --guardar` → tabla, reporte de tablas y filas en la hoja `verificacion` del Excel único. Ninguna cifra se copia a mano.

## Columnas de los CSV de resultados

`id_punto, W_net, W_t, W_p, Q_in, Q_out, Q_rec, eta, dh_s, T1, T2, T3, T4, x4` (EES agrega `res_h1, res_rec, N2`; DWSIM, `iter`).

Unidades: kW, kJ/kg, K. **No incluir h ni s absolutas**: cada programa tiene su propio estado de referencia. Sin exergía: el estado muerto disponible venía del Kalina.

## Programas usados

| Herramienta | Versión | Propiedades |
|---|---|---|
| EES | V10.228 Professional (`D:\Desktop\varios\Nueva carpeta\EES`) | fluidos internos de EES; agua `'Water'` |
| DWSIM | 8.3.4 (`D:\DWSIM`), por automatización con pythonnet | paquetes `CoolProp` y `Peng-Robinson (PR)` |

## Cuidados aprendidos

- EES no distingue mayúsculas: `Q_rec` y `q_rec` son la misma variable.
- En EES, el sistema simultáneo arranca las variables en 1 y los lazos no convergen; un `.txt` no guarda valores iniciales.
- Desde Git Bash, `/solve` se convierte en una ruta: lanzar EES desde Python o PowerShell.
- En DWSIM, `AdiabaticEfficiency` del Expander y `Eficiencia` de la Pump van en %.
- El flash PH del paquete CoolProp de DWSIM no reconoce los estados saturados (fracción de vapor 0,990 en vapor saturado).
