"""Evaporador del ORC (2r → 3), modo R (D-15 §2.2).

Reservorio a T_fuente, efectividad con la MISMA definición que ε_HRVG del Kalina:
    h3,max = h(P_ev, T_fuente)
    h3     = h2r + ε_ev (h3,max − h2r)
    Q̇_in   = ṁ (h3 − h2r)
El cierre por ε fija implícitamente el sobrecalentamiento: puede dejar x3 < 1, y eso lo
juzga la restricción O5 (x3 ≥ x3_min), no este componente (§2.6, hallazgo 2).
Hipótesis: H1, H2 (todo el calor que cede la fuente lo recibe el fluido), H3 ΔP = 0
(P3 = P2r), H4, H12 contracorriente. Balance de masa: ṁ_3 = ṁ_2r; la fuente no se mezcla.
"""

from __future__ import annotations

from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo
from ._estado import estado_Ph

__all__ = ["resolver"]


def resolver(entrada: EstadoTermo, backend: PropertyBackend, *, T_fuente: float,
             eps: float, m: float) -> tuple[EstadoTermo, dict]:
    """Calienta 2r → 3 por efectividad. Devuelve ``(estado 3, {"Qin": kW, "h3_max": kJ/kg})``."""
    P_ev = entrada.P
    h3_max = backend.h(P_ev, T=T_fuente)
    h3 = entrada.h + eps * (h3_max - entrada.h)
    estado3 = estado_Ph(backend, P_ev, h3, m=m, etiqueta="3")
    return estado3, {"Qin": m * (h3 - entrada.h), "h3_max": h3_max}
