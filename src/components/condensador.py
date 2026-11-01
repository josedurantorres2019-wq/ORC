"""Condensador del ORC (4r → 1). Dos cierres del modo R.

Cierre B (D-16, vigente en modo R): efectividad, igual que el condensador del Kalina tercero.
    h1,min = h(P_cd, T_sumidero)
    h1     = h4r − ε_cond (h4r − h1,min)          P_cd y ε_cond son DATOS
    Q̇_out  = ṁ (h4r − h1)
  El estado 1 es un RESULTADO: puede salir bifásico. No se corrige aquí; lo juzga O2
  (succión líquida). Un fluido puro condensa a T constante, así que con ε_cond baja el
  estado 1 sale bifásico (D-15 §2.6): eso es lo que O2 debe detectar.

Cierre A (D-15, alternativa): líquido impuesto a la salida; ε_cd,eq es un resultado.
Presión de condensación del cierre A:
    modo R:  P_cd = P_sat(T_sumidero + ΔT_cd)   (o P_cd como entrada directa, como P_baja)
    modo F:  la fija el solver con T_sat(P_cd) = T_w2 + ΔT_pp,cd (D-15 §2.3)
Salida (H7):
    h1 = h(P_cd, q=0)                     si ΔT_sc = 0 (líquido saturado)
    h1 = h(P_cd, T_sat − ΔT_sc)           si ΔT_sc > 0 (subenfriado)
    Q̇_out = ṁ (h4r − h1)                  calor que SALE (positivo)
    ε_cd,eq = (h4r − h1) / (h4r − h(P_cd, T_sumidero))      solo informativo
Modo F, agua de enfriamiento de c_p,w constante:
    T_w2 = T_w1 + Q̇_out / (ṁ_w c_p,w)

Hipótesis: H1, H2, H3 ΔP = 0 (P1 = P4r = P_cd), H4, H12 contracorriente.
Balance de masa: ṁ_1 = ṁ_4r.
"""

from __future__ import annotations

from ..errores import CicloSinSolucionError
from ..properties.adapter import PropertyBackend, PropertyRangeError
from ..state import EstadoTermo
from ._estado import estado_Ph
from ._perfil_tq import perfil_T

__all__ = ["presion_R", "estado_salida", "resolver", "resolver_eps", "eps_equivalente",
           "agua_F"]


def resolver_eps(entrada: EstadoTermo, backend: PropertyBackend, *, T_sumidero: float,
                 eps: float, m: float) -> tuple[EstadoTermo, dict]:
    """Cierre B: enfría 4r → 1 por efectividad a P_cd = ``entrada.P``.

    Devuelve ``(estado 1, {"Qout": kW, "h1_min": kJ/kg})``. No exige líquido (lo hace O2).
    """
    if not 0.0 <= eps <= 1.0:
        raise ValueError(f"eps_cond={eps} fuera de [0, 1]")
    h1_min = backend.h(entrada.P, T=T_sumidero)
    h1 = entrada.h - eps * (entrada.h - h1_min)
    estado1 = estado_Ph(backend, entrada.P, h1, m=m, etiqueta="1")
    return estado1, {"Qout": m * (entrada.h - h1), "h1_min": h1_min}


def presion_R(backend: PropertyBackend, *, T_sumidero: float, dT_cd: float) -> float:
    """P_cd [kPa] = P_sat(T_sumidero + ΔT_cd)."""
    return backend.P_sat(T_sumidero + dT_cd)


def estado_salida(backend: PropertyBackend, *, P_cd: float, dT_sc: float,
                  m: float) -> EstadoTermo:
    """Estado 1. Solo depende de P_cd y ΔT_sc: por eso el ciclo puede arrancar por aquí."""
    if dT_sc < 0.0:
        raise ValueError(f"dT_sc={dT_sc} < 0")
    if dT_sc == 0.0:
        h1 = backend.h(P_cd, q=0.0)
    else:
        h1 = backend.h(P_cd, T=backend.T_sat(P_cd) - dT_sc)
    estado1 = estado_Ph(backend, P_cd, h1, m=m, etiqueta="1")
    if estado1.fase == "bifasico":      # no debería pasar: lección §2.6 convertida en guarda
        raise CicloSinSolucionError(f"estado 1 bifásico (q={estado1.q}) a P_cd={P_cd} kPa")
    return estado1


def resolver(entrada: EstadoTermo, backend: PropertyBackend, *, dT_sc: float,
             m: float) -> tuple[EstadoTermo, dict]:
    """Enfría 4r → 1 a P_cd = ``entrada.P``. Devuelve ``(estado 1, {"Qout": kW})``."""
    estado1 = estado_salida(backend, P_cd=entrada.P, dT_sc=dT_sc, m=m)
    return estado1, {"Qout": m * (entrada.h - estado1.h)}


def eps_equivalente(entrada: EstadoTermo, salida: EstadoTermo, backend: PropertyBackend, *,
                    T_sumidero: float) -> float | None:
    """ε_cd,eq [-]; None si h(P_cd, T_sumidero) no existe o el denominador no es positivo."""
    try:
        h_min = backend.h(entrada.P, T=T_sumidero)
    except PropertyRangeError:
        return None
    den = entrada.h - h_min
    return (entrada.h - salida.h) / den if den > 0.0 else None


def agua_F(entrada: EstadoTermo, salida: EstadoTermo, backend: PropertyBackend, *,
           T_w1: float, m_w: float, cp_w: float, n_tramos: int) -> dict:
    """Lado del agua en modo F: ``{"T_w2": K, "dT_min": K, "h_pinch": kJ/kg}``.

    El agua entra (T_w1) por el extremo del estado 1 y sale (T_w2) por el del 4r.
    ``dT_min`` es la mínima diferencia real T_fluido − T_agua del perfil discreto: la
    condición de D-15 (pinch contra T_w2) la deja ≥ ΔT_pp,cd si el perfil es el esperado,
    y la restricción L3 lo comprueba.
    """
    C_w = m_w * cp_w
    m = entrada.m
    T_w2 = T_w1 + m * (entrada.h - salida.h) / C_w
    perfil = perfil_T(backend, entrada.P, salida.h, entrada.h, n_tramos=n_tramos)
    dTs = [(T - (T_w1 + m * (h - salida.h) / C_w), h) for h, T in perfil]
    dT_min, h_pinch = min(dTs)
    return {"T_w2": T_w2, "dT_min": dT_min, "h_pinch": h_pinch}
