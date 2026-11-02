"""Corrida principal SIN recuperador y, si puede funcionar, la misma CON recuperador.

Flujo (pedido del usuario, 2026-11-02):
  1. corrida principal con el recuperador apagado (eps_rec = None);
  2. se verifica que el recuperador pueda funcionar: T4 > T2 en esa corrida (el escape de la
     turbina sale más caliente que el líquido que sale de la bomba);
  3. si puede, se repite el punto con ``eps_rec`` y se comparan las dos corridas. Se guardan
     como corridas SEPARADAS del Excel único (otro `id_corrida`, etiqueta ``… | sin_rec`` y
     ``… | con_rec``; la columna eps_rec queda vacía en la primera).

Las presiones P_ev y P_cd se fijan (vienen de los papers): aquí no se varían. ε_rec no tiene
valor aprobado: se da en la línea de comandos, no se inventa. Solo corre cuando el usuario lo
ordene. `scripts/` llama a `src/` y nunca al revés.

Uso:
    python -m scripts.comparar_recuperador --fluido MM --P_ev <kPa> --P_cd <kPa> \
        --eps_cond <-> --eps_rec <-> [--caso diseno] [--guardar] [--etiqueta texto]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import definiciones as d
from src.cycle_solver import CicloNoConvergeError, CicloSinSolucionError, resolver_ciclo_R
from src.exergy import calcular_exergia
from src.exportar_excel import RUTA, agregar_corrida, filas_corrida
from src.properties.coolprop_adapter import CoolPropAdapter
from src.restricciones import evaluar_ciclo

__all__ = ["resolver_punto", "recuperador_puede_funcionar", "comparar", "guardar_par"]


def resolver_punto(backend, entradas: dict, *, P_ev: float, P_cd: float, criterios: dict,
                   T0: float, P0: float):
    """Un punto: ciclo, exergía y restricciones. ``entradas`` incluye ``eps_rec`` (None = apagado)."""
    r = resolver_ciclo_R(backend, P_ev=P_ev, P_cd=P_cd, **entradas)
    ex = calcular_exergia(r, backend, T0=T0, P0=P0)
    val = evaluar_ciclo(r, ex, backend, criterios=criterios,
                        eps={k: entradas[k] for k in ("eps_ev", "eps_rec", "eps_cond")})
    return r, ex, val


def recuperador_puede_funcionar(r: dict) -> tuple[bool, float]:
    """``(T4 > T2, T4 − T2)`` en la corrida sin recuperador (ahí 4r = 4 y 2r = 2)."""
    e = r["estados"]
    dT = e["e4"].T - e["e2"].T
    return dT > 0.0, dT


def _valores(punto) -> dict:
    r, ex, _ = punto
    return {"Wnet": r["Wnet"], "Qin": r["Qin"], "Qrec": r["Qrec"], "eta": r["eta"],
            "eta_II": ex["eta_II"]}


def comparar(backend, entradas: dict, *, P_ev: float, P_cd: float, eps_rec: float,
             criterios: dict, T0: float, P0: float) -> dict:
    """Pasos 1 a 3. Devuelve ``sin``, ``con`` (None si no corre), ``puede``, ``dT_4_2``,
    ``motivo`` (por qué no se corrió o no se resolvió) y ``delta`` (con − sin)."""
    if eps_rec is None:
        raise ValueError("eps_rec es obligatoria para la corrida con recuperador")
    kw = dict(P_ev=P_ev, P_cd=P_cd, criterios=criterios, T0=T0, P0=P0)
    sin = resolver_punto(backend, {**entradas, "eps_rec": None}, **kw)
    puede, dT = recuperador_puede_funcionar(sin[0])
    out = {"sin": sin, "con": None, "puede": puede, "dT_4_2": dT, "motivo": None, "delta": None}
    if not puede:
        out["motivo"] = f"T4 − T2 = {dT:.3f} K ≤ 0: el escape no puede precalentar el líquido"
        return out
    try:
        con = resolver_punto(backend, {**entradas, "eps_rec": eps_rec}, **kw)
    except (CicloSinSolucionError, CicloNoConvergeError) as err:
        out.update(puede=False, motivo=f"el ciclo con recuperador no se resuelve: {err}")
        return out
    v_sin, v_con = _valores(sin), _valores(con)
    out["con"] = con
    out["delta"] = {k: v_con[k] - v_sin[k] for k in v_sin}
    out["delta"]["mejora_eta"] = v_con["eta"] > v_sin["eta"]
    return out


def guardar_par(c: dict, *, meta: dict, entradas: dict, P_ev: float, P_cd: float,
                eps_rec: float, ruta: Path | str = RUTA) -> dict:
    """Agrega al Excel único la corrida sin recuperador y, si existe, la con recuperador.

    Devuelve ``{"sin": id, "con": id | None}``. Son filas distintas (nunca se mezclan).
    """
    base = meta.get("etiqueta") or "comparar_recuperador"
    ids = {"con": None}
    for clave, eps in (("sin", None), ("con", eps_rec)):
        if c[clave] is None:
            continue
        r, ex, val = c[clave]
        filas = filas_corrida(r, ex, val, meta={**meta, "etiqueta": f"{base} | {clave}_rec"},
                              entradas={**entradas, "eps_rec": eps, "P_ev": P_ev, "P_cd": P_cd})
        ids[clave] = agregar_corrida(filas, ruta)
    return ids


def reporte(c: dict, eps_rec: float) -> str:
    """Texto para la consola: las dos corridas lado a lado y el veredicto."""
    v_sin = _valores(c["sin"])
    L = [f"T4 − T2 (sin recuperador) = {c['dT_4_2']:.3f} K "
         f"-> {'puede funcionar' if c['dT_4_2'] > 0 else 'NO puede funcionar'}"]
    if c["con"] is None:
        L += [f"Recuperador no evaluado: {c['motivo']}",
              f"Solo corrida principal: η_I = {v_sin['eta']:.5f}, Ẇ_net = {v_sin['Wnet']:.4f} kW"]
        return "\n".join(L)
    v_con, dl = _valores(c["con"]), c["delta"]
    L.append(f"{'':<8}{'sin rec.':>14}{'con rec.':>14}{'con − sin':>14}   (ε_rec = {eps_rec})")
    for k, nombre in (("Wnet", "Ẇ_net kW"), ("Qin", "Q̇_in kW"), ("Qrec", "Q̇_rec kW"),
                      ("eta", "η_I"), ("eta_II", "η_II")):
        L.append(f"{nombre:<10}{v_sin[k]:>12.5f}{v_con[k]:>14.5f}{dl[k]:>14.5f}")
    L.append("clasificación: " + c["sin"][2].clasificacion.value + " (sin) / "
             + c["con"][2].clasificacion.value + " (con)")
    L.append("VEREDICTO: " + ("el recuperador SÍ mejora η_I" if dl["mejora_eta"]
                              else "el recuperador NO mejora η_I"))
    return "\n".join(L)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fluido", required=True, help="clave de `fluidos` en definiciones.yaml")
    ap.add_argument("--P_ev", type=float, required=True, help="presión del evaporador [kPa]")
    ap.add_argument("--P_cd", type=float, required=True, help="presión del condensador [kPa]")
    ap.add_argument("--eps_rec", type=float, required=True, help="ε_rec de la corrida con recuperador")
    ap.add_argument("--eps_cond", type=float, default=None, help="obligatoria si el YAML la tiene en null")
    ap.add_argument("--caso", default="diseno", help="clave de `casos` (T_fuente, T_sumidero)")
    ap.add_argument("--guardar", action="store_true", help=f"agrega las corridas a {RUTA.name}")
    ap.add_argument("--etiqueta", default=None, help="nombre libre del estudio en el Excel")
    a = ap.parse_args()

    defs = d.cargar()
    backend = CoolPropAdapter(d.nombre_coolprop(defs, a.fluido))
    entradas = d.entradas_R(defs, caso=a.caso)
    if a.eps_cond is not None:
        entradas["eps_cond"] = a.eps_cond
    if entradas["eps_cond"] is None:
        ap.error("eps_cond no está en definiciones.yaml: darla con --eps_cond")
    c = comparar(backend, entradas, P_ev=a.P_ev, P_cd=a.P_cd, eps_rec=a.eps_rec,
                 criterios=d.criterios(defs, fluido=a.fluido), T0=d.valor(defs, "estado_muerto.T0"),
                 P0=d.valor(defs, "estado_muerto.P0"))
    print(f"{a.fluido} ({backend.fluido}), caso {a.caso}, P_ev = {a.P_ev} kPa, P_cd = {a.P_cd} kPa")
    print(reporte(c, a.eps_rec))
    if a.guardar:
        meta = {"fluido": a.fluido, "fluido_coolprop": backend.fluido, "caso": a.caso,
                "version_definiciones": defs.get("version"), "etiqueta": a.etiqueta}
        ids = guardar_par(c, meta=meta, entradas=entradas, P_ev=a.P_ev, P_cd=a.P_cd,
                          eps_rec=a.eps_rec)
        print(f"Guardado en {RUTA}: sin recuperador = corrida {ids['sin']}, "
              f"con recuperador = corrida {ids['con'] or 'no corrió'}")


if __name__ == "__main__":
    main()
