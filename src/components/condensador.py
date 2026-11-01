"""Condensador del ORC (4r → 1), cierre B (D-16): efectividad, igual que el Kalina tercero.

    h1,min = h(P_cd, T_sumidero)
    h1     = h4r − ε_cond (h4r − h1,min)          P_cd y ε_cond son DATOS
    Q̇_out  = ṁ (h4r − h1)
El estado 1 es un RESULTADO: puede salir bifásico. No se corrige aquí; lo juzga O2
(succión líquida). Un fluido puro condensa a T constante, así que con ε_cond baja el
estado 1 sale bifásico (D-15 §2.6): eso es lo que O2 debe detectar.

Hipótesis: H1, H2, H3 ΔP = 0 (P1 = P4r = P_cd), H4, H12 contracorriente.
Balance de masa: ṁ_1 = ṁ_4r.
"""

from __future__ import annotations

from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo
from ._estado import estado_Ph

__all__ = ["resolver"]


def resolver(entrada: EstadoTermo, backend: PropertyBackend, *, T_sumidero: float,
             eps: float, m: float) -> tuple[EstadoTermo, dict]:
    """Enfría 4r → 1 por efectividad a P_cd = ``entrada.P``.

    Devuelve ``(estado 1, {"Qout": kW, "h1_min": kJ/kg})``. No exige líquido (lo hace O2).
    """
    if not 0.0 <= eps <= 1.0:
        raise ValueError(f"eps_cond={eps} fuera de [0, 1]")
    h1_min = backend.h(entrada.P, T=T_sumidero)
    h1 = entrada.h - eps * (entrada.h - h1_min)
    estado1 = estado_Ph(backend, entrada.P, h1, m=m, etiqueta="1")
    return estado1, {"Qout": m * (entrada.h - h1), "h1_min": h1_min}
