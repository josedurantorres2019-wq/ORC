"""Solver del ciclo ORC subcrítico simple (D-14), modos R y F (D-15 §2.2-§2.5).

Modo R — convalidación con el Kalina: fuente y sumidero son reservorios, evaporador por
ε_ev, condensador por ε_cond (cierre B, D-16), base ṁ (H13). Lazo en h1 (como el lazo del
condensador del Kalina) y, con recuperador, lazo interior en h2r. Con el cierre A
(alternativa, D-15) es explícito: 1 → 2 → 3 → 4 → 1.
Modo F — benchmark: fuente y agua finitas de c̄_p constante, evaporador por pinch y ṁ
calculado; Brent en T_cd para cumplir T_sat(P_cd) = T_w2 + ΔT_pp,cd.

Hipótesis del ciclo (D-15 §3): H1 estacionario; H2 adiabático; H3 ΔP = 0 (dos niveles de
presión, P_ev y P_cd); H4 sin Δe_c/Δe_p; H5 η_t, η_p constantes; H6 CoolProp HEOS; H7 estado
1 líquido; H8 vapor saturado en F (ΔT_sh = 0 por defecto), lo que dé ε_ev en R; H11
Ẇ_net = Ẇ_t − Ẇ_p en el eje; H12 contracorriente; H13 ṁ = 1 kg/s en R.
Convención de signos: Q̇_in, Q̇_out, Ẇ_t, Ẇ_p, Q̇_rec positivos en el sentido físico.

Ninguna función tiene valores físicos por defecto: todos salen de `definiciones.yaml`
(los pasa quien llama). Solo los controles numéricos tienen valor por defecto.
"""

from __future__ import annotations

from scipy.optimize import brentq

from . import _lazos
from .components import condensador
from .errores import CicloNoConvergeError, CicloSinSolucionError
from .properties.adapter import PropertyBackend

__all__ = ["resolver_ciclo_R", "resolver_ciclo_F", "CicloNoConvergeError", "CicloSinSolucionError"]

TOL_H = 1e-7          # kJ/kg, lazo del recuperador (modo R)
MAX_ITER = 200
TOL_T_CD = 1e-6       # K, Brent del condensador (modo F)
N_TRAMOS = 40         # tramos del perfil T-Q (modo F)


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
                     P_ev: float, P_cd: float | None, eps_cond: float | None,
                     dT_cd: float | None, dT_sc: float | None, eta_t: float, eta_p: float,
                     eps_ev: float, m: float, eps_rec: float | None, tol_h: float = TOL_H,
                     max_iter: int = MAX_ITER) -> dict:
    """Modo R. ``eps_rec=None`` = sin recuperador.

    Cierre B (D-16, como el Kalina tercero): ``P_cd`` y ``eps_cond`` dados; ``dT_cd`` y
    ``dT_sc`` en None. El estado 1 sale del lazo en h1 y puede ser bifásico (lo juzga O2).
    Cierre A (D-15, alternativa): ``eps_cond=None``, ``dT_sc`` y uno de ``dT_cd`` o ``P_cd``.
    """
    cierre_B = eps_cond is not None
    if cierre_B and (P_cd is None or dT_cd is not None or dT_sc is not None):
        raise ValueError("cierre B: dar P_cd y eps_cond, con dT_cd = dT_sc = None")
    if not cierre_B and ((dT_cd is None) == (P_cd is None) or dT_sc is None):
        raise ValueError("cierre A: dar dT_sc y exactamente uno de dT_cd o P_cd")
    if P_cd is None:
        P_cd = condensador.presion_R(backend, T_sumidero=T_sumidero, dT_cd=dT_cd)
    if not P_cd < P_ev < backend.P_crit:
        raise CicloSinSolucionError(f"se exige P_cd < P_ev < P_crit: {P_cd=}, {P_ev=}, "
                                    f"P_crit={backend.P_crit}")
    kw = dict(P_ev=P_ev, T_fuente=T_fuente, eps_ev=eps_ev, eps_rec=eps_rec, eta_t=eta_t,
              eta_p=eta_p)
    if cierre_B:
        c = _lazos.lazo_condensador_R(backend, P_cd=P_cd, T_sumidero=T_sumidero,
                                      eps_cond=eps_cond, m=m, tol_h=tol_h,
                                      max_iter=max_iter, **kw)
        e1, Qout, iteraciones = c["e1"], c["Qout"], c["iteraciones"]
    else:
        e1 = condensador.estado_salida(backend, P_cd=P_cd, dT_sc=dT_sc, m=m)
        c = _lazos.lado_caliente_R(e1, backend, P_cd=P_cd, m=m, tol_h=tol_h,
                                   max_iter=max_iter, **kw)
        Qout, iteraciones = m * (c["e4r"].h - e1.h), 0
    est = {"e1": e1, **{k: c[k] for k in ("e2", "e2r", "e3", "e4", "e4r")}}
    r = {"modo": "R", "cierre_cd": "B" if cierre_B else "A", "fluido": backend.fluido,
         "m": m, "P_ev": P_ev, "P_cd": P_cd, "estados": est, "Qout": Qout,
         **{k: c[k] for k in ("Qin", "Wt", "Wp", "Qrec", "h2s", "h4s", "h3_max",
                              "iter_rec", "residuo_h2r")},
         "iteraciones": iteraciones, "residuo_h1": c.get("residuo_h1", 0.0),
         "eps_cond": eps_cond,
         "eps_cd_eq": condensador.eps_equivalente(est["e4r"], e1, backend,
                                                  T_sumidero=T_sumidero),
         "T_fuente": T_fuente, "T_sumidero": T_sumidero}
    return _globales(r, backend, T_alta=T_fuente, T_baja=T_sumidero)


def resolver_ciclo_F(backend: PropertyBackend, *, P_ev: float, T_f1: float, m_f: float,
                     cp_f: float, T_w1: float, m_w: float | None, cp_w: float | None,
                     dT_pp_ev: float, dT_pp_cd: float | None, dT_sh: float, dT_sc: float,
                     eta_t: float, eta_p: float, eps_rec: float | None,
                     T_cd: float | None = None, n_tramos: int = N_TRAMOS,
                     tol_T: float = TOL_T_CD) -> dict:
    """Modo F. ``cp_f``, ``cp_w`` en kJ/(kg·K); ṁ del fluido es resultado del pinch.

    Dos cierres del condensador: con agua finita (``m_w``, ``cp_w``, ``dT_pp_cd``; Brent en
    T_cd) o con ``T_cd`` [K] dada, como Yari 2015 (40 °C). Con ``T_cd`` dada y ``m_w=None``
    el sumidero es un reservorio a ``T_w1`` [propuesta, para el benchmark].
    """
    if P_ev >= backend.P_crit:
        raise CicloSinSolucionError(f"P_ev={P_ev} >= P_crit={backend.P_crit}: no es subcrítico")
    if (T_cd is None) == (m_w is None):
        raise ValueError("dar T_cd o el agua finita (m_w, cp_w, dT_pp_cd), no ambos ni ninguno")
    kw = dict(P_ev=P_ev, dT_sc=dT_sc, eta_p=eta_p, eta_t=eta_t, eps_rec=eps_rec, T_f1=T_f1,
              m_f=m_f, cp_f=cp_f, dT_pp_ev=dT_pp_ev, dT_sh=dT_sh, T_w1=T_w1, m_w=m_w,
              cp_w=cp_w, dT_pp_cd=dT_pp_cd, n_tramos=n_tramos)
    T_hi = backend.T_sat(P_ev) - 1e-3      # P_cd < P_ev
    if T_cd is not None:
        if T_cd >= T_hi:
            raise CicloSinSolucionError(f"T_cd={T_cd} K no queda por debajo de T_sat(P_ev)")
        iteraciones = 0
    else:
        T_lo = T_w1 + dT_pp_cd + 1e-6      # con Q̇_out > 0, aquí el residuo es negativo
        if T_lo >= T_hi:
            raise CicloSinSolucionError("T_w1 + ΔT_pp,cd no queda por debajo de T_sat(P_ev)")
        g = lambda T: _lazos.pasada_F(T, backend, **kw)["residuo_cd"]
        g_lo, g_hi = g(T_lo), g(T_hi)
        if g_lo > 0.0 or g_hi < 0.0:
            raise CicloSinSolucionError(f"el condensador no cierra en [{T_lo:.3f}, {T_hi:.3f}]"
                                        f" K (residuos {g_lo:.4g}, {g_hi:.4g} K)")
        T_cd, info = brentq(g, T_lo, T_hi, xtol=tol_T, full_output=True, disp=False)
        if not info.converged:
            raise CicloNoConvergeError(f"Brent en T_cd no convergió: {info.flag}")
        iteraciones = info.iterations
    p = _lazos.pasada_F(T_cd, backend, **kw)
    e, m = p["estados"], p["m"]
    r = {"modo": "F", "fluido": backend.fluido, "m": m, "P_ev": P_ev, "P_cd": p["P_cd"],
         "estados": e, "Qin": m * (e["e3"].h - e["e2r"].h), "Qout": m * (e["e4r"].h - e["e1"].h),
         "Wt": m * (e["e3"].h - e["e4"].h), "Wp": m * (e["e2"].h - e["e1"].h),
         "Qrec": m * (e["e4"].h - e["e4r"].h), "h2s": p["h2s"], "h4s": p["h4s"],
         "iteraciones": iteraciones, "residuo_cd": p["residuo_cd"],
         "T_f1": T_f1, "T_f2": p["evap"]["T_f2"], "T_fpp": p["evap"]["T_fpp"],
         "dT_min_ev": p["evap"]["dT_min"], "h_pinch_ev": p["evap"]["h_pinch"],
         "T_w1": T_w1, "T_w2": p["agua"]["T_w2"], "dT_min_cd": p["agua"]["dT_min"],
         "m_f": m_f, "cp_f": cp_f, "m_w": m_w, "cp_w": cp_w}
    return _globales(r, backend, T_alta=T_f1, T_baja=T_w1)
