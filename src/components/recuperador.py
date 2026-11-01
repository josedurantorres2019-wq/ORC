"""Recuperador opcional del ORC (lado caliente 4 → 4r, lado frío 2 → 2r).

Forma de efectividad del ε_reg del Kalina, con el calor máximo del lado que LIMITA:
    q_max = mín[ h4 − h(P_cd, T2) ,  h(P_ev, T4) − h2 ]
    h4r   = h4 − ε_rec · q_max
    h2r   = h2 + (h4 − h4r)              balance de energía con el mismo ṁ en los dos lados
    Q̇_rec = ṁ (h4 − h4r)                 carga interna (no cruza la frontera del ciclo)

Desviación de D-15 §2.3 (revisión termodinámica 2026-10-31, D1; PENDIENTE de aprobación):
§2.3 usa solo el lado caliente, h4 − h(P_cd, T2). Si T2 < T_sat(P_cd) (ΔT_sc > 0) ese
término incluye el calor latente y el lado frío no puede absorberlo: cruce de temperaturas
(2.ª ley). Cuando el lado caliente limita, las dos fórmulas coinciden.

Si T4 ≤ T2 no hay recuperación posible (el calor iría del frío al caliente): el punto no
existe con recuperador (revisión D2).

Hipótesis: H1, H2 (sin pérdidas al ambiente: todo lo que cede 4 lo recibe 2),
H3 ΔP = 0 en ambos lados, H4, H12 contracorriente. ε_rec = 0 equivale a apagarlo.
Balance de masa: ṁ_4r = ṁ_4 = ṁ_2r = ṁ_2.
"""

from __future__ import annotations

from ..errores import CicloSinSolucionError
from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo
from ._estado import estado_Ph

__all__ = ["resolver"]


def resolver(caliente: EstadoTermo, fria: EstadoTermo, backend: PropertyBackend, *,
             eps: float) -> tuple[EstadoTermo, EstadoTermo, dict]:
    """Devuelve ``(estado 4r, estado 2r, {"Qrec": kW, "q_max": kJ/kg})``. ``caliente`` = 4, ``fria`` = 2."""
    if caliente.m is None or fria.m is None or abs(caliente.m - fria.m) > 1e-12 * caliente.m:
        raise ValueError("el recuperador exige el mismo caudal ṁ en los dos lados")
    if not 0.0 <= eps <= 1.0:
        raise ValueError(f"eps_rec={eps} fuera de [0, 1]")
    if caliente.T <= fria.T:
        raise CicloSinSolucionError(f"T4={caliente.T:.3f} K <= T2={fria.T:.3f} K: el "
                                    "recuperador no puede transferir calor")
    q_max = min(caliente.h - backend.h(caliente.P, T=fria.T),
                backend.h(fria.P, T=caliente.T) - fria.h)
    h4r = caliente.h - eps * q_max
    h2r = fria.h + (caliente.h - h4r)
    estado4r = estado_Ph(backend, caliente.P, h4r, m=caliente.m, etiqueta="4r")
    estado2r = estado_Ph(backend, fria.P, h2r, m=fria.m, etiqueta="2r")
    return estado4r, estado2r, {"Qrec": caliente.m * (caliente.h - h4r), "q_max": q_max}
