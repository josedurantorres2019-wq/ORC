"""Robustez de los lazos del solver sobre puntos de los papers (ampliación v1.0.0, familia F5).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.v1.robustez_lazo

1. Lazo en h1: ε_cond barrida de 0,50 a 0,999 sobre VP-03 (Yari, n-butano) y VP-14 (Çengel 10-23,
   agua subenfriada). El estado 1 pasa de bifásico a saturado y a subenfriado.
2. Lazo del recuperador: ε_rec barrida de 0 a 0,99 sobre VP-06 (Bombarda, MM).
Criterios (fijados antes de correr): todos los puntos convergen; residuo en h1 < 1e-7 kJ/kg;
Ẇ_net continua (sin saltos: |Δ²Ẇ| < 1 % de Ẇ entre pasos vecinos); Q_rec creciente con ε_rec.
Lo que no cumpla es un hallazgo para v1.0.1: aquí no se corrige nada.
Salida: `03_verificacion/v1/robustez_lazo.csv`.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

from src.cycle_solver import resolver_ciclo_R
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts._mapeo_papers import entradas_modo_R
from scripts.comparar_verificacion import _puntos

OUT = Path(__file__).resolve().parents[2] / "03_verificacion" / "v1"


def _barrer(punto: dict, clave: str, valores) -> list[dict]:
    b = CoolPropAdapter(punto["fluido"])
    ent = entradas_modo_R(punto, b)
    filas = []
    for v in valores:
        fila = {"id_punto": punto["id_punto"], "variable": clave, "valor": round(float(v), 4)}
        try:
            r = resolver_ciclo_R(b, **{**ent, clave: float(v)})
            e1 = r["estados"]["e1"]
            fila.update(converge=True, iteraciones=r["iteraciones"], iter_rec=r.get("iter_rec"),
                        residuo_h1=r["residuo_h1"], W_net=r["Wnet"], Q_rec=r["Qrec"],
                        x1=e1.q, T1_menos_Tsat=e1.T - b.T_sat(ent["P_cd"]))
        except Exception as ex:                       # se registra: es un hallazgo, no se corrige
            fila.update(converge=False, error=f"{type(ex).__name__}: {str(ex)[:120]}")
        filas.append(fila)
    return filas


def _criterios(filas: list[dict], creciente: str | None = None) -> list[str]:
    malos = []
    if not all(f["converge"] for f in filas):
        malos.append(f"{sum(not f['converge'] for f in filas)} sin converger")
    ok = [f for f in filas if f["converge"]]
    if any(abs(f["residuo_h1"]) >= 1e-7 for f in ok):
        malos.append("residuo en h1 ≥ 1e-7")
    W = np.array([f["W_net"] for f in ok])
    if len(W) > 2 and np.max(np.abs(np.diff(W, 2))) >= 0.01 * np.max(np.abs(W)):
        malos.append(f"salto en Ẇ_net (máx |Δ²Ẇ| = {np.max(np.abs(np.diff(W, 2))):.2f} kW)")
    if creciente and any(b < a - 1e-9 for a, b in zip([f[creciente] for f in ok], [f[creciente] for f in ok][1:])):
        malos.append(f"{creciente} no crece")
    return malos


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    pts = {p["id_punto"]: p for _, p in _puntos()}
    todas = []
    for pid in ("VP-03", "VP-14"):
        f = _barrer(pts[pid], "eps_cond", np.linspace(0.50, 0.999, 41))
        it = [x["iteraciones"] for x in f if x["converge"]]
        malos = _criterios(f)
        print(f"{pid} ε_cond 0,50→0,999: {'pasa' if not malos else 'FALLA: ' + '; '.join(malos)}; "
              f"iteraciones {min(it)}–{max(it)}; x1 de {f[0].get('x1', float('nan')):.3f} a "
              f"T1−Tsat {f[-1].get('T1_menos_Tsat', float('nan')):+.2f} K", flush=True)
        todas += f
    f = _barrer(pts["VP-06"], "eps_rec", np.linspace(0.0, 0.99, 34))
    malos = _criterios(f, creciente="Q_rec")
    it = [x["iter_rec"] for x in f if x["converge"] and x["iter_rec"] is not None]
    print(f"VP-06 ε_rec 0→0,99: {'pasa' if not malos else 'FALLA: ' + '; '.join(malos)}; "
          f"iteraciones del recuperador {min(it) if it else '-'}–{max(it) if it else '-'}", flush=True)
    todas += f
    claves = list(dict.fromkeys(k for x in todas for k in x))
    with (OUT / "robustez_lazo.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=claves)
        w.writeheader()
        w.writerows(todas)
    print(f"Salida en {OUT / 'robustez_lazo.csv'}")


if __name__ == "__main__":
    main()
