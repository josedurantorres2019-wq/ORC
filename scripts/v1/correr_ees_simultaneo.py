"""EES resolviendo el ORC como sistema simultáneo (ampliación v1.0.0, familia F7).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.v1.correr_ees_simultaneo

Prueba el MÉTODO NUMÉRICO: el código cierra los lazos por sustitución sucesiva; aquí EES los
resuelve con Newton, todo a la vez (`03_verificacion/ees/orc_modo_R_simultaneo.txt`).
Valores iniciales: los estados del código (CoolProp) corridos por el desfase de entalpía de EES
(otro estado de referencia), que se mide en una primera pasada corta. Como las EoS difieren, el
arranque no es la solución de EES: Newton tiene que converger por su cuenta.
Comparación: contra la corrida con PROCEDURE (`ees/resultados_ees.csv`, mismas propiedades de EES).
Si los dos métodos dan lo mismo, el resultado no depende del método. Criterio (fijado antes):
|ΔẆ_net| y |ΔQ_in| < 1e-4 relativo y |ΔT| < 0,01 K.
Salida: `03_verificacion/v1/ees_simultaneo.csv` y los programas en `ees/simultaneo/`.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from src.cycle_solver import resolver_ciclo_R
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts.correr_ees import (ENTRADAS, FLUIDO_EES, SALIDA, _leer_csv_ees, correr, programa)

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "03_verificacion" / "ees" / "simultaneo"
PLANTILLA = RAIZ / "03_verificacion" / "ees" / "orc_modo_R_simultaneo.txt"
OUT = RAIZ / "03_verificacion" / "v1" / "ees_simultaneo.csv"
EXPORTA = ["W_net", "Q_in", "T[1]", "T[2]", "T[3]", "T[4]", "eta"]


def _desfase_h(fila: dict) -> float | None:
    """h_EES − h_CoolProp del estado 1, con el programa de PROCEDURE de una sola pasada."""
    DIR.mkdir(parents=True, exist_ok=True)
    out = DIR / f"{fila['id_punto']}_h1.csv"
    texto = programa(fila, out).rsplit("$Export", 1)[0] + f"$Export /A '{out}' h[1]\n"
    prog = DIR / f"{fila['id_punto']}_h1.txt"
    prog.write_text(texto, encoding="latin-1")
    ok, _ = correr(prog, out)
    return _leer_csv_ees(out)[0] if ok else None


def _programa_simultaneo(fila: dict, r: dict, dh: float, out: Path) -> str:
    v = {k: fila[k] for k in ("P_ev", "P_cd", "T_fuente", "T_sumidero", "eps_ev", "eps_cond",
                              "eta_t", "eta_p", "m")}
    v["eps_rec"] = fila["eps_rec"] or "0"
    entradas = [f"F$ = '{FLUIDO_EES[fila['fluido_coolprop']]}'"] + [f"{k} = {x}" for k, x in v.items()]
    e = r["estados"]
    g = {"h[1]": e["e1"].h + dh, "h[2]": e["e2"].h + dh, "h[3]": e["e3"].h + dh,
         "h[4]": e["e4"].h + dh, "h_2r": e["e2r"].h + dh, "h_4r": e["e4r"].h + dh,
         "T[1]": e["e1"].T, "T[2]": e["e2"].T, "T[3]": e["e3"].T, "T[4]": e["e4"].T,
         "q_rec_kg": e["e2r"].h - e["e2"].h, "q_max": max(e["e4"].h - e["e1"].h, 1.0)}
    guesses = [f"$VarInfo {k} Guess={x:.6f}" for k, x in g.items()]
    texto = PLANTILLA.read_text(encoding="utf-8").split("}", 1)[1]
    texto = texto.replace("@ENTRADAS@", "\n".join(entradas)).replace("@GUESSES@", "\n".join(guesses))
    return texto + f"\n$Export /A '{out}' {', '.join(EXPORTA)}\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    proc = {f["id_punto"]: f for f in csv.DictReader(SALIDA.open(encoding="utf-8"))}
    filas = []
    for fila in csv.DictReader(ENTRADAS.open(encoding="utf-8")):
        pid = fila["id_punto"]
        b = CoolPropAdapter(fila["fluido_coolprop"])
        ent = {k: float(x) if x else None for k, x in fila.items() if k not in ("id_punto", "fluido_coolprop")}
        r = resolver_ciclo_R(b, **ent)
        h1_ees = _desfase_h(fila)
        if h1_ees is None:
            print(f"{pid}: no se pudo medir el desfase de h", flush=True)
            continue
        dh = h1_ees - r["estados"]["e1"].h
        out, prog = DIR / f"{pid}_sim.csv", DIR / f"{pid}.txt"
        prog.write_text(_programa_simultaneo(fila, r, dh, out), encoding="latin-1")
        ok, nota = correr(prog, out)
        if not ok:
            print(f"{pid}: EES simultáneo NO convergió ({nota or 'sin ventanas'})", flush=True)
            filas.append({"id_punto": pid, "converge": False, "nota": nota})
            continue
        s = dict(zip(EXPORTA, _leer_csv_ees(out)))
        p = proc[pid]
        dW = (s["W_net"] - float(p["W_net"])) / float(p["W_net"])
        dQ = (s["Q_in"] - float(p["Q_in"])) / float(p["Q_in"])
        dT = max(abs(s[f"T[{i}]"] - float(p[f"T{i}"])) for i in (1, 2, 3, 4))
        ok = abs(dW) < 1e-4 and abs(dQ) < 1e-4 and dT < 0.01
        filas.append({"id_punto": pid, "converge": True, "W_net_simultaneo": s["W_net"],
                      "W_net_procedure": float(p["W_net"]), "dW_rel": dW, "dQin_rel": dQ,
                      "dT_max_K": dT, "veredicto": "pasa" if ok else "falla", "nota": nota.strip()})
        print(f"{pid}: {'pasa ' if ok else 'FALLA'} ΔẆ {dW:+.1e}  ΔQ_in {dQ:+.1e}  ΔT {dT:.1e} K  "
              f"(desfase h {dh:+.2f} kJ/kg) {nota}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    claves = list(dict.fromkeys(k for x in filas for k in x))
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=claves)
        w.writeheader()
        w.writerows(filas)
    print(f"{sum(f.get('veredicto') == 'pasa' for f in filas)}/{len(filas)} pasan. Salida en {OUT}")


if __name__ == "__main__":
    main()
