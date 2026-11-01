"""Evaporador del ORC (2r → 3). Dos cierres, mismas ecuaciones de balance (D-15 §2.2).

Modo R — reservorio a T_fuente, efectividad con la MISMA definición que ε_HRVG del Kalina:
    h3,max = h(P_ev, T_fuente)
    h3     = h2r + ε_ev (h3,max − h2r)
    Q̇_in   = ṁ (h3 − h2r)
  El cierre por ε fija implícitamente el sobrecalentamiento: puede dejar x3 < 1, y eso lo
  juzga la restricción O5 (x3 ≥ x3_min), no este componente (§2.6, hallazgo 2).

Modo F — fuente finita de c̄_p constante, pinch ΔT_pp,ev (H8: ΔT_sh = 0 por defecto):
    h3   = h(P_ev, q=1)  si ΔT_sh = 0;  h(P_ev, T_sat + ΔT_sh)  si no
    ṁ    = mín sobre el perfil de  ṁ_f c̄_p (T_f1 − ΔT_pp − T(h)) / (h3 − h)
           (en el punto de burbuja es la ecuación de D-15: ṁ(h3 − h_l) = ṁ_f c̄_p (T_f1 − T_f,pp));
           si el mínimo cae en otro punto del perfil, ese tramo es el que limita ṁ.
    T_f2 = T_f1 − ṁ (h3 − h2r) / (ṁ_f c̄_p)
    Q̇_in = ṁ (h3 − h2r) = ṁ_f c̄_p (T_f1 − T_f2)

Hipótesis: H1, H2 (todo el calor que cede la fuente lo recibe el fluido), H3 ΔP = 0
(P3 = P2r), H4, H12 contracorriente. Balance de masa: ṁ_3 = ṁ_2r; la fuente no se mezcla.
"""

from __future__ import annotations

from ..errores import CicloSinSolucionError
from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo
from ._estado import estado_Ph
from ._perfil_tq import perfil_T

__all__ = ["resolver_R", "resolver_F"]


def resolver_R(entrada: EstadoTermo, backend: PropertyBackend, *, T_fuente: float,
               eps: float, m: float) -> tuple[EstadoTermo, dict]:
    """Calienta 2r → 3 por efectividad. Devuelve ``(estado 3, {"Qin": kW, "h3_max": kJ/kg})``."""
    P_ev = entrada.P
    h3_max = backend.h(P_ev, T=T_fuente)
    h3 = entrada.h + eps * (h3_max - entrada.h)
    estado3 = estado_Ph(backend, P_ev, h3, m=m, etiqueta="3")
    return estado3, {"Qin": m * (h3 - entrada.h), "h3_max": h3_max}


def resolver_F(entrada: EstadoTermo, backend: PropertyBackend, *, T_f1: float, m_f: float,
               cp_f: float, dT_pp: float, dT_sh: float, n_tramos: int) -> tuple[EstadoTermo, dict]:
    """Calienta 2r → 3 con pinch. ṁ es un RESULTADO (la entrada no necesita traerlo).

    ``cp_f`` en kJ/(kg·K), ``m_f`` en kg/s. Devuelve ``(estado 3, {...})`` con
    ``Qin`` [kW], ``m`` [kg/s], ``T_f2``, ``T_fpp`` [K], ``dT_min`` [K] (mínimo real del
    perfil discreto) y ``h_pinch`` [kJ/kg] (dónde está ese mínimo).
    """
    P_ev = entrada.P
    T_sat = backend.T_sat(P_ev)
    h3 = backend.h(P_ev, q=1.0) if dT_sh == 0.0 else backend.h(P_ev, T=T_sat + dT_sh)
    T3 = backend.estado_Ph(P_ev, h3)["T"]
    if T_f1 - T3 < dT_pp:
        raise CicloSinSolucionError(f"T_f1 − T3 = {T_f1 - T3:.3f} K < ΔT_pp = {dT_pp} K en el extremo "
                         "caliente: no existe ṁ > 0 que cumpla el pinch")
    C_f = m_f * cp_f                                      # kW/K
    perfil = perfil_T(backend, P_ev, entrada.h, h3, n_tramos=n_tramos)
    candidatos = [(C_f * (T_f1 - dT_pp - T) / (h3 - h), h) for h, T in perfil if h < h3]
    m, h_pinch = min(candidatos)
    if m <= 0.0:
        raise CicloSinSolucionError("el pinch deja ṁ ≤ 0: la fuente no alcanza a calentar el fluido")
    T_f2 = T_f1 - m * (h3 - entrada.h) / C_f
    dT_min = min(T_f1 - m * (h3 - h) / C_f - T for h, T in perfil)
    estado3 = estado_Ph(backend, P_ev, h3, m=m, etiqueta="3")
    # T_fpp: temperatura de la fuente en el punto que limita (burbuja o el que toque).
    return estado3, {"Qin": m * (h3 - entrada.h), "m": m, "T_f2": T_f2,
                     "T_fpp": T_f1 - m * (h3 - h_pinch) / C_f, "dT_min": dT_min,
                     "h_pinch": h_pinch}
