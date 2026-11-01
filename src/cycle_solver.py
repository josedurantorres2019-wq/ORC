"""Solver del ciclo ORC subcrítico simple (D-14): cierre por efectividades, como el Kalina.

Modo R con cierre B del condensador (D-16): fuente y sumidero son reservorios, evaporador
por ε_ev, condensador por ε_cond, base ṁ (H13). Lazo en h1 (como el lazo del condensador
del Kalina) y, con recuperador, lazo interior en h2r. Es la única formulación del código:
la de pinch (modo F) y el cierre A se retiraron el 2026-10-31 (quedan en el commit 5100776).

Hipótesis del ciclo (D-15 §3): H1 estacionario; H2 adiabático; H3 ΔP = 0 (dos niveles de
presión, P_ev y P_cd); H4 sin Δe_c/Δe_p; H5 η_t, η_p constantes; H6 CoolProp HEOS; H8 lo
que dé ε_ev; H11 Ẇ_net = Ẇ_t − Ẇ_p en el eje; H12 contracorriente; H13 ṁ = 1 kg/s.
Convención de signos: Q̇_in, Q̇_out, Ẇ_t, Ẇ_p, Q̇_rec positivos en el sentido físico.

Ninguna función tiene valores físicos por defecto: todos salen de `definiciones.yaml`
(los pasa quien llama). Solo los controles numéricos tienen valor por defecto.
"""

from __future__ import annotations

from . import _lazos
from .errores import CicloNoConvergeError, CicloSinSolucionError
from .properties.adapter import PropertyBackend

__all__ = ["resolver_ciclo_R", "CicloNoConvergeError", "CicloSinSolucionError"]

TOL_H = 1e-7          # kJ/kg, lazos en h1 y h2r
MAX_ITER = 200


def _globales(r: dict, backend: PropertyBackend, *, T_alta: float, T_baja: float) -> dict:
    """Ẇ_net, η_I, η_Carnot, w_net y las salidas adicionales aprobadas (2026-10-31)."""
    e = r["estados"]
    m = r["m"]
    r["Wnet"] = r["Wt"] - r["Wp"]
    r["eta"] = r["Wnet"] / r["Qin"]
    r["eta_carnot"] = 1.0 - T_baja / T_alta
    r["eta_sobre_carnot"] = r["eta"] / r["eta_carnot"]
    r["w_net"] = r["Wnet"] / m                                  # kJ/kg de fluido
    r["N2"] = abs(r["Qin"] - r["Qout"] - r["Wnet"]) / abs(r["Qin"])
    r["r_p"] = r["P_ev"] / r["P_cd"]
    r["P_ev_sobre_Pcrit"] = r["P_ev"] / backend.P_crit
    r["dh_s"] = e["e3"].h - r["h4s"]
    r["VR"] = e["e4"].v / e["e3"].v
    r["r_bw"] = r["Wp"] / r["Wt"]
    r["dT_sh3"] = e["e3"].T - backend.T_sat(r["P_ev"])          # revisión B (pendiente)
    r["T_sat_cd"] = backend.T_sat(r["P_cd"])
    return r


def resolver_ciclo_R(backend: PropertyBackend, *, T_fuente: float, T_sumidero: float,
                     P_ev: float, P_cd: float, eps_cond: float, eta_t: float, eta_p: float,
                     eps_ev: float, m: float, eps_rec: float | None, tol_h: float = TOL_H,
                     max_iter: int = MAX_ITER) -> dict:
    """Modo R, cierre B. ``eps_rec=None`` = sin recuperador.

    ``P_cd`` y ``eps_cond`` son datos (como el Kalina tercero). El estado 1 sale del lazo en
    h1 y puede ser bifásico: no se corrige aquí, lo juzga O2.
    """
    if not P_cd < P_ev < backend.P_crit:
        raise CicloSinSolucionError(f"se exige P_cd < P_ev < P_crit: {P_cd=}, {P_ev=}, "
                                    f"P_crit={backend.P_crit}")
    c = _lazos.lazo_condensador_R(backend, P_ev=P_ev, P_cd=P_cd, T_fuente=T_fuente,
                                  T_sumidero=T_sumidero, eps_ev=eps_ev, eps_cond=eps_cond,
                                  eps_rec=eps_rec, eta_t=eta_t, eta_p=eta_p, m=m, tol_h=tol_h,
                                  max_iter=max_iter)
    r = {"modo": "R", "fluido": backend.fluido, "m": m, "P_ev": P_ev, "P_cd": P_cd,
         "estados": {k: c[k] for k in ("e1", "e2", "e2r", "e3", "e4", "e4r")},
         **{k: c[k] for k in ("Qin", "Qout", "Wt", "Wp", "Qrec", "h2s", "h4s", "h3_max",
                              "iter_rec", "residuo_h2r", "iteraciones", "residuo_h1")},
         "eps_cond": eps_cond, "T_fuente": T_fuente, "T_sumidero": T_sumidero}
    return _globales(r, backend, T_alta=T_fuente, T_baja=T_sumidero)
