"""Compara código, EES y DWSIM entre sí y contra los papers, punto por punto (niveles V2-V3).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.comparar_herramientas            # imprime y escribe la tabla CSV
    python -m scripts.comparar_herramientas --guardar  # además agrega Python ↔ herramienta al Excel

Entradas: `03_verificacion/entradas_puntos.csv` (las del código, sacadas de los papers), los CSV de
resultados de cada herramienta (`ees/resultados_ees.csv`, `dwsim/resultados_dwsim_<paq>.csv`) y
los valores de los papers (bloque `verificacion` de `01_referencias/casos/*.yaml`).
Salida: `03_verificacion/comparacion_herramientas.csv`, una fila por (punto, variable) con el valor
del paper, del código y de cada herramienta. Ninguna cifra se copia a mano.
Tolerancias: Python ↔ herramienta las de `03_verificacion/tolerancias.yaml` (§7 del plan);
herramienta ↔ paper las mismas del YAML de cada caso que usa el código.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

from src.cycle_solver import resolver_ciclo_R
from src.exportar_excel import agregar_verificacion
from src.properties.coolprop_adapter import CoolPropAdapter
from src.verificacion import comparar

from ._mapeo_papers import salidas
from ._tablas_reporte import escribir_tablas
from .comparar_verificacion import _puntos

V = Path(__file__).resolve().parents[1] / "03_verificacion"
HERRAMIENTAS = {"EES": V / "ees" / "resultados_ees.csv",
                "DWSIM-CoolProp": V / "dwsim" / "resultados_dwsim_coolprop.csv",
                "DWSIM-PR": V / "dwsim" / "resultados_dwsim_pr.csv"}
# variable de los CSV → (clase de tolerancia, unidad, nombre en el resultado de Python)
VARIABLES = {"W_net": ("energia", "kW", "Wnet"), "W_t": ("energia", "kW", "Wt"),
             "W_p": ("energia", "kW", "Wp"), "Q_in": ("energia", "kW", "Qin"),
             "Q_out": ("energia", "kW", "Qout"), "Q_rec": ("energia", "kW", "Qrec"),
             "eta": ("eta", "-", "eta"), "dh_s": ("energia", "kJ/kg", "dh_s"),
             "T1": ("T", "K", "e1"), "T2": ("T", "K", "e2"), "T3": ("T", "K", "e3"),
             "T4": ("T", "K", "e4"), "x4": ("x", "-", "e4")}


def _python(fila: dict) -> dict:
    b = CoolPropAdapter(fila["fluido_coolprop"])
    ent = {k: float(v) if v else None for k, v in fila.items()
           if k not in ("id_punto", "fluido_coolprop")}
    r = resolver_ciclo_R(b, **ent)
    out = {k: r[n] for k, (_, _, n) in VARIABLES.items() if not k.startswith(("T", "x"))}
    out.update({f"T{i}": r["estados"][f"e{i}"].T for i in (1, 2, 3, 4)})
    out["x4"] = r["estados"]["e4"].q
    return out, r


def _leer(ruta: Path) -> dict[str, dict]:
    if not ruta.exists():
        return {}
    return {f["id_punto"]: {k: float(v) for k, v in f.items() if k in VARIABLES}
            for f in csv.DictReader(ruta.open(encoding="utf-8"))}


def _x(v: float) -> float:
    """Título acotado a [0, 1]: EES da 100 (vapor sobrecalentado) y -100 (líquido)."""
    return min(max(v, 0.0), 1.0) if v == v else v


def _paper(punto: dict, val: dict, m: float) -> dict:
    """Valores de la herramienta con los nombres del paper (misma función que usa el código)."""
    r = {"eta": val["eta"], "Wnet": val["W_net"], "Wt": val["W_t"], "Wp": val["W_p"],
         "Qin": val["Q_in"], "Qout": val["Q_out"], "Qrec": val["Q_rec"], "dh_s": val["dh_s"], "m": m}
    return salidas(r, punto)


def _causa_paper(c: dict, v_herr: float, v_py: float, tol_h: dict, causa_h: str | None,
                 codigo_pasa: bool):
    """La causa del caso (dato del paper, EoS de EES 2015, ...) explica a la herramienta si ella
    coincide con el código dentro de su tolerancia de energía; si no, hace falta además la causa
    documentada de su propia diferencia con el código (causas.yaml)."""
    if v_py == 0:
        return None
    if abs(v_herr - v_py) / abs(v_py) <= tol_h["energia"]["tol"]:
        return c.get("causa") or (f"el código pasa frente al paper y la herramienta coincide con el "
                                  f"código dentro de su tolerancia (±{100 * tol_h['energia']['tol']:g} %)"
                                  if codigo_pasa else None)
    if not causa_h or not (c.get("causa") or codigo_pasa):
        return None
    return f"{c['causa']} | además, frente al código: {causa_h}" if c.get("causa") else (
        f"el código pasa frente al paper; la diferencia es de la herramienta: {causa_h}")


def _causa_herr(causas: dict, h: str, pid: str) -> str | None:
    ca = causas.get(h, {})
    return None if pid in ca.get("sin_causa", []) else ca.get(pid, ca.get("todos"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--guardar", action="store_true")
    ap.add_argument("--punto", action="append", help="con --guardar: solo estos puntos al Excel")
    a = ap.parse_args()
    tol = yaml.safe_load((V / "tolerancias.yaml").read_text(encoding="utf-8"))
    causas = yaml.safe_load((V / "causas.yaml").read_text(encoding="utf-8"))
    res = {h: _leer(r) for h, r in HERRAMIENTAS.items()}
    casos = {p["id_punto"]: p for _, p in _puntos()}
    tabla, excel = [], []
    for fila in csv.DictReader((V / "entradas_puntos.csv").open(encoding="utf-8")):
        pid, m = fila["id_punto"], float(fila["m"])
        py, r = _python(fila)
        # 1) contra el paper: código y cada herramienta, con las tolerancias del caso
        sal_py = salidas(r, casos[pid])
        for c in casos[pid]["comparar"]:
            v = c["variable"]
            py_pasa = comparar(id_punto=pid, nivel="V3", herramienta="paper", referencia="",
                               variable=v, unidad="", valor_ref=c["valor_ref"], valor_python=sal_py[v],
                               tolerancia=c["tolerancia"], tipo_tolerancia=c["tipo"])["veredicto"] == "pasa"
            fila_t = {"id_punto": pid, "comparacion": "paper", "variable": v,
                      "unidad": c["unidad"], "paper": c["valor_ref"], "Python": sal_py[v]}
            for h in HERRAMIENTAS:
                if pid in res[h] and v in (sal := _paper(casos[pid], res[h][pid], m)):
                    k = comparar(id_punto=pid, nivel="V3", herramienta=h,
                                 referencia=c["referencia"], variable=v, unidad=c["unidad"],
                                 valor_ref=c["valor_ref"], valor_python=sal[v],
                                 tolerancia=c["tolerancia"], tipo_tolerancia=c["tipo"],
                                 causa=_causa_paper(c, sal[v], sal_py[v], tol[h],
                                                    _causa_herr(causas, h, pid), py_pasa))
                    fila_t[h], fila_t[f"err_{h}"], fila_t[f"ver_{h}"] = sal[v], k["error_rel"], k["veredicto"]
            tabla.append(fila_t)
        # 2) Python ↔ herramienta, todas las variables, tolerancias del §7
        for v, (clase, unidad, _) in VARIABLES.items():
            fila_t = {"id_punto": pid, "comparacion": "Python", "variable": v, "unidad": unidad,
                      "Python": py[v]}
            for h in HERRAMIENTAS:
                if pid not in res[h]:
                    continue
                ref = res[h][pid][v]
                if v == "x4":
                    ref, py[v] = _x(ref), _x(py[v])
                if v == "Q_rec" and ref == 0 and py[v] == 0:
                    continue
                t = tol[h][clase]
                causa = _causa_herr(causas, h, pid)
                k = comparar(id_punto=pid, nivel="V2", herramienta=h,
                             referencia=f"{h}, {HERRAMIENTAS[h].name}", variable=v, unidad=unidad,
                             valor_ref=ref, valor_python=py[v], tolerancia=t["tol"],
                             tipo_tolerancia=t["tipo"], causa=causa)
                fila_t[h], fila_t[f"err_{h}"], fila_t[f"ver_{h}"] = ref, (
                    k["error_abs"] if t["tipo"] == "abs" else k["error_rel"]), k["veredicto"]
                if not a.punto or pid in a.punto:
                    excel.append(k)
            tabla.append(fila_t)
    cols = ["id_punto", "comparacion", "variable", "unidad", "paper", "Python"]
    for h in HERRAMIENTAS:
        cols += [h, f"err_{h}", f"ver_{h}"]
    with (V / "comparacion_herramientas.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(tabla)
    for h in HERRAMIENTAS:
        vs = [t[f"ver_{h}"] for t in tabla if f"ver_{h}" in t]
        print(h, {c: vs.count(c) for c in ("pasa", "explicado", "falla")},
              f"({len({t['id_punto'] for t in tabla if f'ver_{h}' in t})} puntos)")
    print(f"Tabla: {V / 'comparacion_herramientas.csv'}")
    escribir_tablas(tabla, list(HERRAMIENTAS), VARIABLES, V / "reporte_tablas.md")
    if a.guardar and excel:
        agregar_verificacion(excel)
        print(f"{len(excel)} filas Python ↔ herramienta en la hoja verificacion")


if __name__ == "__main__":
    main()
