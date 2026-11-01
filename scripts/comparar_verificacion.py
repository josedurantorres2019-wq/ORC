"""Corre los casos publicados con el código del ORC y los compara con sus datos (nivel V1 y V3).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.comparar_verificacion            # imprime la comparación
    python -m scripts.comparar_verificacion --guardar  # además la agrega al Excel único
    python -m scripts.comparar_verificacion --entradas 03_verificacion/entradas_puntos.csv
        # además escribe las entradas en modo R de cada punto, para correr lo mismo en EES y DWSIM

Lee el bloque `verificacion` de cada `01_referencias/casos/*.yaml`, lo lleva al modo R con
`_mapeo_papers` (V-A, V-B), resuelve con `resolver_ciclo_R` y arma una fila por variable con
`src.verificacion.comparar` (tolerancias del YAML, aprobadas en V-D). Con ``--guardar`` cada
punto queda como corrida (hojas `corridas`, `estados`, ...) y sus comparaciones en `verificacion`.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

from src import definiciones as d
from src.cycle_solver import resolver_ciclo_R
from src.exergy import calcular_exergia
from src.exportar_excel import RUTA, agregar_corrida, agregar_verificacion, filas_corrida
from src.properties.coolprop_adapter import CoolPropAdapter
from src.restricciones import evaluar_ciclo
from src.verificacion import comparar

from ._mapeo_papers import componentes, entradas_modo_R, salidas

CASOS = Path(__file__).resolve().parents[1] / "01_referencias" / "casos"


def _puntos():
    for ruta in sorted(CASOS.glob("*.yaml")):
        caso = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        for punto in caso.get("verificacion", []):
            yield ruta.stem, punto


def _filas(punto: dict, valores: dict, nivel: str, id_corrida) -> list[dict]:
    return [comparar(id_punto=punto["id_punto"], nivel=nivel, herramienta="paper",
                     referencia=c["referencia"], variable=c["variable"], unidad=c["unidad"],
                     valor_ref=c["valor_ref"], valor_python=valores[c["variable"]],
                     tolerancia=c["tolerancia"], tipo_tolerancia=c["tipo"], causa=c.get("causa"),
                     id_corrida=id_corrida)
            for c in punto["comparar"]]


def _corrida(caso: str, punto: dict, b, defs: dict, guardar: bool):
    """Resuelve el punto en modo R. Devuelve (valores, id_corrida, mensaje, entradas)."""
    ent = entradas_modo_R(punto, b)
    r = resolver_ciclo_R(b, **ent)
    ex = calcular_exergia(r, b, T0=d.valor(defs, "estado_muerto.T0"),
                          P0=d.valor(defs, "estado_muerto.P0"))
    val = evaluar_ciclo(r, ex, b, criterios=d.criterios(defs, fluido=punto["fluido"]),
                        eps={k: ent[k] for k in ("eps_ev", "eps_rec", "eps_cond")})
    msg = (f"ε_ev={ent['eps_ev']:.4f} ε_cond={ent['eps_cond']:.4f} ε_rec={ent['eps_rec']} "
           f"η_t={ent['eta_t']:.4f} ṁ={ent['m']:.3f} kg/s  iter={r['iteraciones']}  "
           f"clase={val.clasificacion.value}")
    id_corrida = None
    if guardar:
        meta = {"fluido": punto["fluido"], "fluido_coolprop": b.fluido, "caso": caso,
                "version_definiciones": defs.get("version"), "etiqueta": punto["id_punto"]}
        id_corrida = agregar_corrida(filas_corrida(r, ex, val, meta=meta, entradas=ent))
    return salidas(r, punto), id_corrida, msg, ent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--guardar", action="store_true", help=f"agrega todo a {RUTA.name}")
    ap.add_argument("--entradas", type=Path, default=None, help="CSV con las entradas en modo R")
    a = ap.parse_args()
    defs = d.cargar()
    todas, entradas = [], []
    for caso, punto in _puntos():
        b = CoolPropAdapter(punto["fluido"])
        if punto.get("tipo") == "componentes":
            valores, id_corrida, nivel, msg = componentes(punto, b), None, "V1", "bomba y turbina"
        else:
            valores, id_corrida, msg, ent = _corrida(caso, punto, b, defs, a.guardar)
            nivel = "V3"
            entradas.append({"id_punto": punto["id_punto"], "fluido_coolprop": b.fluido, **ent})
        filas = _filas(punto, valores, nivel, id_corrida)
        todas += filas
        print(f"\n{punto['id_punto']} ({caso}, {punto['fluido']}): {msg}")
        for f in filas:
            err = f"{100 * f['error_rel']:+.3f} %" if f["error_rel"] is not None else "-"
            print(f"  {f['variable']:<10} ref={f['valor_ref']:<10g} python={f['valor_python']:<12.5g}"
                  f" error={err:>10}  tol={f['tolerancia']:g} ({f['tipo_tolerancia']})  "
                  f"{f['veredicto'].upper()}" + (f"  [{f['causa']}]" if f["causa"] else ""))
    resumen = {v: sum(f["veredicto"] == v for f in todas) for v in ("pasa", "explicado", "falla")}
    print(f"\nResumen: {resumen} de {len(todas)} comparaciones")
    if a.entradas:
        a.entradas.parent.mkdir(parents=True, exist_ok=True)
        with open(a.entradas, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(entradas[0]))
            w.writeheader()
            w.writerows(entradas)
        print(f"Entradas en modo R: {a.entradas}")
    if a.guardar:
        agregar_verificacion(todas)
        print(f"Guardado en {RUTA}")


if __name__ == "__main__":
    main()
