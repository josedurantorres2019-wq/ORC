"""Turbina del ORC (3 → 4), igual que la turbina del Kalina.

Ecuaciones (D-15 §2.3; Çengel Ec. 10-11):
    h4s = h(P_cd, s3)                    expansión isentrópica
    h4  = h3 − η_t (h3 − h4s)            H5: η_t constante
    Ẇ_t = ṁ (h3 − h4)                    trabajo que SALE (positivo)

Hipótesis: H1 estacionario, H2 adiabática, H4 sin Δe_c ni Δe_p, H5 η_t isentrópica
constante. Balance de masa: ṁ_4 = ṁ_3 = ṁ.
"""

from __future__ import annotations

from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo
from ._estado import estado_Ph

__all__ = ["resolver"]


def resolver(entrada: EstadoTermo, backend: PropertyBackend, *, P_salida: float,
             eta_t: float) -> tuple[EstadoTermo, dict]:
    """Expande la corriente 3 hasta la 4 a ``P_salida`` [kPa]. ṁ = ``entrada.m``.

    Devuelve ``(estado 4, {"Wt": kW, "h4s": kJ/kg})``; ``h4s`` alimenta Δh_s = h3 − h4s.
    """
    if entrada.m is None:
        raise ValueError("la corriente 3 debe traer su caudal m")
    if not 0.0 < eta_t <= 1.0:
        raise ValueError(f"eta_t={eta_t} fuera de (0, 1]")
    if P_salida > entrada.P:
        raise ValueError(f"la turbina no comprime: P_salida={P_salida} > P3={entrada.P} kPa")
    h3 = entrada.h
    h4s = backend.h(P_salida, s=entrada.s)
    h4 = h3 - eta_t * (h3 - h4s)
    estado4 = estado_Ph(backend, P_salida, h4, m=entrada.m, etiqueta="4")
    return estado4, {"Wt": entrada.m * (h3 - h4), "h4s": h4s}
