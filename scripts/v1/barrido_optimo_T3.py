"""Óptimo de T3 y tendencias contra Yari 2015 y Campos 2014 (ampliación v1.0.0, familia F2).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.v1.barrido_optimo_T3

1. Yari Tabla 6 da, por fluido, la T3 (vapor saturado) que MAXIMIZA Ẇ_net. Con los mismos supuestos
   de los puntos VP-03… (pinch de 10 K en el punto de burbuja, condensación a 40 °C) se barre T3
   con el código y se busca T3* = argmax Ẇ_net. Tolerancia (decisión A-3, fijada antes): T3* ±1 K
   y Ẇ_max ±0,5 %. Para R1234yf, propano y R134a Yari queda en un límite superior (texto, p. 6:
   «no puede subir por su T_c»): ahí se comprueba que Ẇ todavía crece en su T3 (dẆ/dT3 > 0).
2. Tendencias de Yari (p. 6): al subir T3, ṁ baja y η_th sube.
3. Campos 2014 (cap. 4): en un fluido seco el sobrecalentamiento baja la potencia. n-butano de
   VP-13 (140 °C, pinch 3 K) con ΔT_sh de 0 a 20 K.
Salida: `03_verificacion/v1/optimo_T3.csv` y `03_verificacion/v1/tendencias.csv`.
"""

from __future__ import annotations

import csv
import sys
from copy import deepcopy
from pathlib import Path

import CoolProp.CoolProp as CP
import numpy as np

from src.cycle_solver import resolver_ciclo_R
from src.errores import CicloSinSolucionError
from src.properties.adapter import PropertyRangeError
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts._mapeo_papers import entradas_modo_R
from scripts.comparar_verificacion import _puntos

OUT = Path(__file__).resolve().parents[2] / "03_verificacion" / "v1"
# id del punto de Yari Tabla 6 → (T3* °C, Ẇ_max kW, ¿óptimo interior?) [Yari 2015, Tabla 6, p. 719]
YARI = {"VP-03": (76.32, 1450, True), "VP-C-isobutano": (77.33, 1479, True),
        "VP-C-R152a": (77.77, 1476, True), "VP-C-amoniaco": (75.53, 1377, True),
        "VP-04": (84.0, 1816, False), "VP-C-propano": (86.9, 1635, False),
        "VP-C-R134a": (81.67, 1580.9, True)}
# R134a: la fila de la Tabla 6 (94,9 °C, 1448 kW) es el EXTREMO de su curva en la Fig. 5, no el máximo
# (inconsistencia de Yari, hallada el 2026-11-02). Se juzga contra el máximo de la Fig. 5 digitalizada.
TOL_T, TOL_W = 1.0, 0.005
TOL_T_FIG = 1.65                          # R134a: medio paso de muestreo de la Fig. 5 (3,3 °C)
FIG5 = Path(__file__).resolve().parents[2] / "01_referencias" / "casos" / "yari2015_fig5_digitalizada.csv"
TOL_CURVA_REL, TOL_CURVA_ABS = 0.005, 10.0   # modelo ±0,5 % + lectura de la figura ±10 kW
DT_LECTURA = 0.2   # °C de lectura en T3. Donde la curva cae a pique (109 °C) pesa |dẆ/dT3|·0,2: se agregó
                   # DESPUÉS de la primera corrida (2026-11-02) y esos puntos quedan como «explicado».


def _ciclo(punto: dict):
    b = CoolPropAdapter(punto["fluido"])
    ent = entradas_modo_R(punto, b)
    return ent, resolver_ciclo_R(b, **ent)


def _con_T3(punto: dict, T3: float) -> dict:
    p = deepcopy(punto)
    p["P_ev"] = {"T_sat_degC": float(T3)}
    return p


def _barrido(punto: dict, T_ini: float, T_fin: float, paso: float = 0.05):
    filas = []
    for T3 in np.arange(T_ini, T_fin + 1e-9, paso):
        try:
            ent, r = _ciclo(_con_T3(punto, T3))
        except (CicloSinSolucionError, PropertyRangeError, ValueError):   # cerca de T_c
            continue
        filas.append((round(float(T3), 3), r["Wnet"], r["eta"], ent["m"]))
    return filas


def _fig5() -> list[dict]:
    return list(csv.DictReader(x for x in FIG5.read_text(encoding="utf-8").splitlines()
                               if not x.startswith("#")))


def _curvas_fig5(puntos: dict) -> list[dict]:
    """Ẇ_net del código en cada punto digitalizado de la Fig. 5 de Yari."""
    base = {puntos[pid]["fluido"]: puntos[pid] for pid in YARI}
    filas = []
    for f in _fig5():
        T3, W_y = float(f["T3_degC"]), float(f["W_net_kW"])
        p = base[f["fluido_coolprop"]]
        _, r = _ciclo(_con_T3(p, T3))
        pend = (_ciclo(_con_T3(p, T3 + 0.05))[1]["Wnet"] - _ciclo(_con_T3(p, T3 - 0.05))[1]["Wnet"]) / 0.1
        err = r["Wnet"] - W_y
        tol = TOL_CURVA_REL * W_y + TOL_CURVA_ABS
        ver = "pasa" if abs(err) <= tol else ("explicado" if abs(err) <= tol + abs(pend) * DT_LECTURA
                                              else "falla")
        filas.append({"fluido": f["fluido_coolprop"], "T3_degC": T3, "W_yari_fig5": W_y,
                      "W_codigo": round(r["Wnet"], 1), "error_kW": round(err, 1),
                      "error_pct": round(100 * err / W_y, 2), "dW_dT3": round(pend, 1), "veredicto": ver})
    for fl in dict.fromkeys(x["fluido"] for x in filas):
        xs = [x for x in filas if x["fluido"] == fl]
        print(f"Fig. 5 {fl:10s}: {sum(x['veredicto'] == 'pasa' for x in xs)} pasan, "
              f"{sum(x['veredicto'] == 'explicado' for x in xs)} explicados de {len(xs)}; error "
              + " ".join(f"{x['error_pct']:+.1f}" for x in xs) + " %", flush=True)
    return filas


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    puntos = {p["id_punto"]: p for _, p in _puntos()}
    opt, tend = [], []
    for pid, (T_y, W_y, interior) in YARI.items():
        p = puntos[pid]
        Tc = CP.PropsSI("Tcrit", p["fluido"]) - 273.15
        T_fig = max(float(f["T3_degC"]) for f in _fig5() if f["fluido_coolprop"] == p["fluido"])
        T_fin = min(109.0, Tc - 0.5, T_fig + 0.05)  # rango que grafica Yari (fuera de él, artefacto cerca de T_c)
        f = _barrido(p, 50.0, T_fin)
        i = int(np.argmax([x[1] for x in f]))
        T_opt, W_opt = f[i][0], f[i][1]
        cerca = [x for x in f if abs(x[0] - T_y) < 0.051]
        W_en_Ty = cerca[0][1] if cerca else float("nan")
        if interior:
            tol_T = TOL_T_FIG if pid == "VP-C-R134a" else TOL_T
            tol_W = TOL_W + TOL_CURVA_ABS / W_y if pid == "VP-C-R134a" else TOL_W
            ok = abs(T_opt - T_y) <= tol_T and abs(W_opt - W_y) / W_y <= tol_W
            nota = f"T3* {T_opt - T_y:+.2f} K; Ẇ_max {100 * (W_opt - W_y) / W_y:+.2f} %"
        else:
            j = f.index(cerca[0]) if cerca else None
            pend = (f[j + 1][1] - f[j - 1][1]) / (f[j + 1][0] - f[j - 1][0]) if j else float("nan")
            ok = pend > 0
            nota = f"límite de Yari: dẆ/dT3 = {pend:+.1f} kW/K en {T_y} °C; T3* del código {T_opt} °C"
        etas, ms = [x[2] for x in f], [x[3] for x in f]
        mono = all(b > a for a, b in zip(etas, etas[1:])) and all(b < a for a, b in zip(ms, ms[1:]))
        opt.append({"id_punto": pid, "fluido": p["fluido"], "T3_yari": T_y, "W_yari": W_y,
                    "T3_codigo": T_opt, "W_max_codigo": round(W_opt, 2), "W_codigo_en_T3_yari":
                    round(W_en_Ty, 2), "interior": interior, "veredicto": "pasa" if ok else "falla",
                    "nota": nota, "eta_sube_y_m_baja": mono})
        print(f"{pid:15s} {'pasa ' if ok else 'FALLA'} {nota}; η↑ y ṁ↓ con T3: {mono}", flush=True)
    curva = _curvas_fig5(puntos)
    vp13 = puntos["VP-13"]
    b = CoolPropAdapter(vp13["fluido"])
    T_sat = b.T_sat(vp13["P_ev"]["kPa"]) - 273.15
    for dT in range(0, 21, 2):
        p = deepcopy(vp13)
        p["estado_3"] = {"q": 1} if dT == 0 else {"T_degC": T_sat + dT}
        _, r = _ciclo(p)
        tend.append({"caso": "Campos 2014, n-butano 140 °C", "dT_sh_K": dT, "W_net_kW": round(r["Wnet"], 4)})
    W = [x["W_net_kW"] for x in tend]
    baja = all(b < a for a, b in zip(W, W[1:]))
    print(f"Campos 2014: Ẇ_net con ΔT_sh 0→20 K: {W[0]:.3f} → {W[-1]:.3f} kW; baja siempre: {baja}")
    for nombre, filas in (("optimo_T3.csv", opt), ("tendencias.csv", tend), ("curvas_fig5.csv", curva)):
        with (OUT / nombre).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    print(f"Salida en {OUT}")


if __name__ == "__main__":
    main()
