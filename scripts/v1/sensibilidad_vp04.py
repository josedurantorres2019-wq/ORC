"""Sensibilidad de VP-04 (Yari, R1234yf): ¿qué supuesto explica −3,5 %? (ampliación v1.0.0, familia F8).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.v1.sensibilidad_vp04

1. Para cada supuesto del caso (pinch, η_p, η_t, T de condensación) se busca, por bisección, el valor
   ÚNICO que da los 1816 kW de Yari a T3 = 84 °C con el resto igual.
2. Con ese valor se recalcula toda la curva del R1234yf de la Fig. 5 (digitalizada) y se mide el
   error en cada punto. Si un supuesto fuera la causa, debería reproducir también la FORMA de la
   curva: con los supuestos de Yari el error del código crece de −0,7 % (65 °C) a −3,5 % (84 °C).
Salida: `03_verificacion/v1/sensibilidad_vp04.csv`.
"""

from __future__ import annotations

import csv
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np

from scripts.comparar_verificacion import _puntos
from scripts.v1.barrido_optimo_T3 import _ciclo, _con_T3, _fig5

OUT = Path(__file__).resolve().parents[2] / "03_verificacion" / "v1" / "sensibilidad_vp04.csv"
W_YARI = 1816.0


def _con(punto: dict, param: str, v: float) -> dict:
    p = deepcopy(punto)
    if param == "dT_pinch":
        p["m"]["pinch"]["dT_pinch"] = v
    elif param == "T_cond":
        p["P_cd"] = {"T_sat_degC": v}
    else:
        p[param] = v
    return p


def _W(punto: dict, T3: float) -> float:
    return _ciclo(_con_T3(punto, T3))[1]["Wnet"]


def _bisecar(punto: dict, param: str, a: float, b: float) -> float | None:
    fa = _W(_con(punto, param, a), 84.0) - W_YARI
    fb = _W(_con(punto, param, b), 84.0) - W_YARI
    if fa * fb > 0:
        return None
    for _ in range(60):
        c = 0.5 * (a + b)
        fc = _W(_con(punto, param, c), 84.0) - W_YARI
        if fa * fc <= 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return 0.5 * (a + b)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    base = {p["id_punto"]: p for _, p in _puntos()}["VP-04"]
    fig = [(float(f["T3_degC"]), float(f["W_net_kW"])) for f in _fig5() if f["fluido_coolprop"] == "R1234yf"]
    casos = {"dT_pinch": (5.0, 10.0, 10.0), "eta_p": (0.85, 1.0, 0.85), "eta_t": (0.85, 0.95, 0.85),
             "T_cond": (35.0, 40.0, 40.0)}
    filas = []
    err0 = [100 * (_W(base, T) - W) / W for T, W in fig]
    print(f"Supuestos de Yari: error a lo largo de la curva {err0[0]:+.2f} … {err0[-1]:+.2f} %")
    for param, (a, b, actual) in casos.items():
        v = _bisecar(base, param, a, b)
        if v is None:
            print(f"{param:9s}: ningún valor en [{a}, {b}] da 1816 kW")
            filas.append({"supuesto": param, "valor_yari": actual, "valor_que_da_1816": None})
            continue
        p = _con(base, param, v)
        err = [100 * (_W(p, T) - W) / W for T, W in fig]
        rms = float(np.sqrt(np.mean(np.square(err))))
        print(f"{param:9s}: {actual} → {v:.4g} da 1816 kW a 84 °C; error en la curva "
              f"{err[0]:+.2f} (65 °C) … {err[-1]:+.2f} % (84 °C); RMS {rms:.2f} %", flush=True)
        filas.append({"supuesto": param, "valor_yari": actual, "valor_que_da_1816": v,
                      "error_65C_pct": err[0], "error_84C_pct": err[-1], "rms_curva_pct": rms})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for x in filas for k in x)))
        w.writeheader()
        w.writerows(filas)
    print(f"Salida en {OUT}")


if __name__ == "__main__":
    main()
