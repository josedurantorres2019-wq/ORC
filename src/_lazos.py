"""Lazos privados del solver ORC, modo R (D-15 §2.5).

Los lazos aparecen cuando hay recirculación y cierre por efectividad (corrección del
2026-10-31 en el modelo, §2.5). Todos son de UNA variable:

- `lazo_condensador_R`: cierre B. ε_cond hace que h1 dependa de h4r, y h4r de h1:
  sustitución sucesiva en h1 (el lazo del condensador del Kalina tercero).
- `lazo_recuperador_R`: con recuperador. ε_ev hace que h3 dependa de h2r, y h2r depende
  de h4 (recuperador): sustitución sucesiva en h2r, el análogo del lazo exterior del Kalina
  (ahí ε_HRVG hace que h2 dependa de h1).
- `lado_caliente_R`: una pasada 1 → 4r con h1 dado (el cuerpo del lazo en h1).
"""

from __future__ import annotations

from dataclasses import replace

from .components import bomba, condensador, evaporador, recuperador, turbina
from .components._estado import estado_Ph
from .errores import CicloNoConvergeError
from .properties.adapter import PropertyBackend
from .state import EstadoTermo

__all__ = ["lado_caliente_R", "lazo_condensador_R", "lazo_recuperador_R"]


def lado_caliente_R(e1: EstadoTermo, backend: PropertyBackend, *, P_ev: float, P_cd: float,
                    T_fuente: float, eps_ev: float, eps_rec: float | None, eta_t: float,
                    eta_p: float, m: float, tol_h: float, max_iter: int) -> dict:
    """Modo R desde el estado 1 hasta 4r: bomba → [recuperador] → evaporador → turbina."""
    e2, bo = bomba.resolver(e1, backend, P_salida=P_ev, eta_p=eta_p, m=m)
    if eps_rec is None:
        e2r = replace(e2, etiqueta="2r")
        e3, ev = evaporador.resolver(e2r, backend, T_fuente=T_fuente, eps=eps_ev, m=m)
        e4, tu = turbina.resolver(e3, backend, P_salida=P_cd, eta_t=eta_t)
        e4r = replace(e4, etiqueta="4r")
        lazo = {"Qrec": 0.0, "iteraciones": 0, "residuo_h2r": 0.0}
    else:
        lazo = lazo_recuperador_R(e2, backend, P_cd=P_cd, T_fuente=T_fuente, eps_ev=eps_ev,
                                  eps_rec=eps_rec, eta_t=eta_t, m=m, tol_h=tol_h,
                                  max_iter=max_iter)
        e2r, e3, e4, e4r = lazo["e2r"], lazo["e3"], lazo["e4"], lazo["e4r"]
        ev = tu = lazo
    return {"e2": e2, "e2r": e2r, "e3": e3, "e4": e4, "e4r": e4r, "Qin": ev["Qin"],
            "Wt": tu["Wt"], "Wp": bo["Wp"], "Qrec": lazo["Qrec"], "h2s": bo["h2s"],
            "h4s": tu["h4s"], "h3_max": ev["h3_max"], "iter_rec": lazo["iteraciones"],
            "residuo_h2r": lazo["residuo_h2r"]}


def lazo_condensador_R(backend: PropertyBackend, *, P_cd: float, T_sumidero: float,
                       eps_cond: float, m: float, tol_h: float, max_iter: int,
                       **kw_caliente) -> dict:
    """Cierre B: sustitución sucesiva en h1, el análogo del lazo del condensador del Kalina.

    ε_cond hace que h1 dependa de h4r, y h4r depende de h1 (bomba → ε_ev → turbina).
    Arranque: líquido saturado a P_cd. Se devuelve la pasada cuyo h1 de ENTRADA produjo los
    estados, así Q̇_out = ṁ(h4r − h1) cierra N2 exacto; ε efectiva difiere de ε_cond ≤ tol_h.
    """
    h1 = backend.h(P_cd, q=0.0)
    for it in range(1, max_iter + 1):
        e1 = estado_Ph(backend, P_cd, h1, m=m, etiqueta="1")
        c = lado_caliente_R(e1, backend, P_cd=P_cd, m=m, tol_h=tol_h, max_iter=max_iter,
                            **kw_caliente)
        e1_nuevo, _ = condensador.resolver(c["e4r"], backend, T_sumidero=T_sumidero,
                                           eps=eps_cond, m=m)
        delta = abs(e1_nuevo.h - h1)
        if delta <= tol_h:
            return {**c, "e1": e1, "iteraciones": it, "residuo_h1": delta,
                    "Qout": m * (c["e4r"].h - e1.h)}
        h1 = e1_nuevo.h
    raise CicloNoConvergeError(f"lazo del condensador sin converger en {max_iter} iteraciones "
                               f"(último Δh1 = {delta:.3e} kJ/kg)")


def lazo_recuperador_R(e2: EstadoTermo, backend: PropertyBackend, *, P_cd: float,
                       T_fuente: float, eps_ev: float, eps_rec: float, eta_t: float,
                       m: float, tol_h: float, max_iter: int) -> dict:
    """Sustitución sucesiva en h2r. Devuelve estados 2r, 3, 4, 4r, energías e iteraciones."""
    h2r = e2.h                                   # arranque: recuperador sin carga
    for it in range(1, max_iter + 1):
        e2r = estado_Ph(backend, e2.P, h2r, m=m, etiqueta="2r")
        e3, ev = evaporador.resolver(e2r, backend, T_fuente=T_fuente, eps=eps_ev, m=m)
        e4, tu = turbina.resolver(e3, backend, P_salida=P_cd, eta_t=eta_t)
        e4r, e2r_nuevo, re = recuperador.resolver(e4, e2, backend, eps=eps_rec)
        delta = abs(e2r_nuevo.h - h2r)
        if delta <= tol_h:
            # Se cierra con el h2r de ESTA pasada (el que produjo e3), para que Q̇_in, Q̇_rec y
            # los estados sean consistentes entre sí; el error es ≤ tol_h.
            return {"e2r": e2r, "e3": e3, "e4": e4, "e4r": e4r, "iteraciones": it,
                    **ev, **tu, **re, "residuo_h2r": delta}
        h2r = e2r_nuevo.h
    raise CicloNoConvergeError(f"lazo del recuperador sin converger en {max_iter} iteraciones "
                               f"(último Δh2r = {delta:.3e} kJ/kg)")
