"""Resuelve UN punto del ORC en modo R con las entradas de `definiciones.yaml` e imprime todo.

Uso (desde la raíz del repo; solo cuando el usuario ordene la corrida):
    python -m scripts.punto_modo_R --fluido n-butano --P_ev <kPa> --P_cd <kPa> --eps_cond <->
(cierre B, D-16: los valores los da el caso; no hay valores por defecto).

`scripts/` llama a `src/` y nunca al revés. Con ``--guardar`` agrega el punto al Excel único
(`datos/resultados_orc.xlsx`, ver `src/exportar_excel.py`); sin él no guarda nada.
"""

from __future__ import annotations

import argparse
import sys

from src import definiciones as d
from src.cycle_solver import resolver_ciclo_R
from src.exergy import calcular_exergia
from src.exportar_excel import RUTA, agregar_corrida, filas_corrida
from src.properties.coolprop_adapter import CoolPropAdapter
from src.restricciones import evaluar_ciclo


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")       # consola cp1252 de Windows (Δ, ṁ, −)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fluido", required=True, help="clave de `fluidos` en definiciones.yaml")
    ap.add_argument("--P_ev", type=float, required=True, help="presión del evaporador [kPa]")
    ap.add_argument("--P_cd", type=float, required=True, help="presión del condensador [kPa]")
    ap.add_argument("--eps_cond", type=float, default=None,
                    help="efectividad del condensador; obligatoria si el YAML la tiene en null")
    ap.add_argument("--eps_rec", type=float, default=None,
                    help="efectividad del recuperador; sin ella queda apagado (YAML)")
    ap.add_argument("--caso", default="diseno", help="clave de `casos` (T_fuente, T_sumidero)")
    ap.add_argument("--guardar", action="store_true", help=f"agrega el punto a {RUTA.name}")
    ap.add_argument("--etiqueta", default=None, help="nombre libre de la corrida en el Excel")
    a = ap.parse_args()

    defs = d.cargar()
    backend = CoolPropAdapter(d.nombre_coolprop(defs, a.fluido))
    entradas = d.entradas_R(defs, caso=a.caso)
    if a.eps_cond is not None:
        entradas["eps_cond"] = a.eps_cond
    if a.eps_rec is not None:
        entradas["eps_rec"] = a.eps_rec
    if entradas["eps_cond"] is None:
        ap.error("eps_cond no está en definiciones.yaml: darla con --eps_cond")
    r = resolver_ciclo_R(backend, P_ev=a.P_ev, P_cd=a.P_cd, **entradas)
    ex = calcular_exergia(r, backend, T0=d.valor(defs, "estado_muerto.T0"),
                          P0=d.valor(defs, "estado_muerto.P0"))
    val = evaluar_ciclo(r, ex, backend, criterios=d.criterios(defs, fluido=a.fluido),
                        eps={k: entradas[k] for k in ("eps_ev", "eps_rec", "eps_cond")})

    print(f"{a.fluido} ({backend.fluido}), modo R, P_ev = {a.P_ev} kPa, P_cd = {r['P_cd']:.3f} kPa")
    print(f"{'estado':>6} {'T [K]':>10} {'P [kPa]':>10} {'h [kJ/kg]':>11} {'s':>9} {'q':>7} fase")
    for k, e in r["estados"].items():
        q = "-" if e.q is None else f"{e.q:.4f}"
        print(f"{e.etiqueta:>6} {e.T:10.3f} {e.P:10.3f} {e.h:11.3f} {e.s:9.5f} {q:>7} {e.fase}")
    for k in ("Qin", "Qout", "Wt", "Wp", "Wnet", "eta", "eta_carnot", "eta_sobre_carnot",
              "w_net", "eps_cond", "iteraciones", "r_p", "P_ev_sobre_Pcrit", "dh_s", "VR", "r_bw", "dT_sh3", "N2"):
        print(f"  {k:<18} {r[k]}")
    for k in ("eta_II", "Ed_total", "cierre_exergia"):
        print(f"  {k:<18} {ex[k]}")
    print("  Ed por componente [kW]:", {k: round(v, 4) for k, v in ex["Ed"].items()})
    print(val.mensaje_reporte())
    if a.guardar:
        meta = {"fluido": a.fluido, "fluido_coolprop": backend.fluido, "caso": a.caso,
                "version_definiciones": defs.get("version"), "etiqueta": a.etiqueta}
        filas = filas_corrida(r, ex, val, meta=meta,
                              entradas={**entradas, "P_ev": a.P_ev, "P_cd": a.P_cd})
        print(f"Guardado en {RUTA} como corrida {agregar_corrida(filas)}")


if __name__ == "__main__":
    main()
