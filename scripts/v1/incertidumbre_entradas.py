"""Incertidumbre por el redondeo de los datos publicados (ampliación v1.0.0, familia F6).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.v1.incertidumbre_entradas

Los papers publican sus entradas redondeadas (Yari T3 = 76,32 °C; Bombarda 0,12 bar; Vera 0,052 MPa).
Cada entrada numérica se perturba de forma uniforme en ± media unidad de su última cifra y se
propaga con el código (Monte Carlo, 400 muestras, semilla fija). Resultado por comparación: la
semiamplitud del 95 % (U95) de la salida, frente a la tolerancia aprobada y al error observado.
- U95 > tolerancia: la tolerancia es más estrecha que lo que el propio dato permite.
- |error| ≤ tolerancia + U95: la diferencia cabe en el redondeo del dato.
Los enunciados de Çengel son datos exactos de un problema: no se perturban.
Salida: `03_verificacion/v1/incertidumbre_entradas.csv`.
"""

from __future__ import annotations

import csv
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np

from src.cycle_solver import resolver_ciclo_R
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts._mapeo_papers import entradas_modo_R, salidas
from scripts.comparar_verificacion import _puntos

OUT = Path(__file__).resolve().parents[2] / "03_verificacion" / "v1" / "incertidumbre_entradas.csv"
N, SEMILLA = 400, 20261102
# Solo valores que el paper REPORTA (resultados redondeados). La T de condensación de Yari (40 °C) y
# de Campos (37 °C) son supuestos de diseño exactos: no se perturban (corregido tras la 1.ª corrida).
CAMPOS = [("P_ev", "kPa"), ("P_ev", "T_sat_degC"), ("P_cd", "kPa"), ("estado_3", "T_degC"),
          ("m", "kg_s")]


def _media_unidad(v: float) -> float:
    s = repr(float(v)).rstrip("0").rstrip(".")
    return 0.5 * 10.0 ** (-(len(s.split(".")[1]) if "." in s else 0))


def _salidas(punto: dict) -> dict:
    b = CoolPropAdapter(punto["fluido"])
    return salidas(resolver_ciclo_R(b, **entradas_modo_R(punto, b)), punto)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rng = np.random.default_rng(SEMILLA)
    filas = []
    for caso, punto in _puntos():
        if caso.startswith("cengel") or punto.get("tipo") == "componentes":
            continue
        campos = [(a, b) for a, b in CAMPOS if b in punto.get(a, {})]
        extra = [("Q_rec_kW", None)] if "Q_rec_kW" in punto else []
        base = _salidas(punto)
        muestras = {c["variable"]: [] for c in punto["comparar"]}
        for _ in range(N):
            p = deepcopy(punto)
            for a, b in campos:
                v = punto[a][b]
                p[a][b] = v + rng.uniform(-1, 1) * _media_unidad(v)
            for a, _b in extra:
                p[a] = punto[a] + rng.uniform(-1, 1) * _media_unidad(punto[a])
            s = _salidas(p)
            for k in muestras:
                muestras[k].append(s[k])
        for c in punto["comparar"]:
            x = np.array(muestras[c["variable"]])
            u95 = float(np.percentile(np.abs(x - base[c["variable"]]), 95))
            rel = c["tipo"] == "rel"
            u = u95 / abs(c["valor_ref"]) if rel else u95
            err = (base[c["variable"]] - c["valor_ref"]) / (abs(c["valor_ref"]) if rel else 1.0)
            fila = {"id_punto": punto["id_punto"], "variable": c["variable"], "tipo": c["tipo"],
                    "tolerancia": c["tolerancia"], "U95_redondeo": u, "error": err,
                    "U95_mayor_que_tol": u > c["tolerancia"],
                    "error_cabe_en_tol_mas_U95": abs(err) <= c["tolerancia"] + u,
                    "entradas_perturbadas": ";".join(f"{a}.{b}" for a, b in campos) + (";Q_rec_kW" if extra else "")}
            filas.append(fila)
            print(f"{punto['id_punto']:16s} {c['variable']:6s} U95={u:.4f} tol={c['tolerancia']:.4f} "
                  f"error={err:+.4f}  {'U95>tol ' if fila['U95_mayor_que_tol'] else ''}"
                  f"{'cabe' if fila['error_cabe_en_tol_mas_U95'] else 'NO cabe'}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"Salida en {OUT}")


if __name__ == "__main__":
    main()
