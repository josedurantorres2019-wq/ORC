"""Bomba del ORC (1 → 2), igual que la bomba del Kalina.

Ecuaciones (D-15 §2.3; Çengel Ec. 10-2 y 10-10):
    h2s = h(P_ev, s1)                    compresión isentrópica
    h2  = h1 + (h2s − h1) / η_p          H5: η_p constante
    Ẇ_p = ṁ (h2 − h1)                    trabajo que ENTRA (positivo)

Hipótesis: H1 estacionario, H2 adiabática, H4 sin Δe_c ni Δe_p, H5 η_p isentrópica
constante. No se usa w = v·ΔP (Çengel Ec. 10-3): solo vale para líquido incompresible y un
orgánico cerca de T_c no lo es; se usa h(P2, s1) del motor.
Balance de masa: ṁ_2 = ṁ_1 = ṁ.
"""

from __future__ import annotations

from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo
from ._estado import estado_Ph

__all__ = ["resolver"]


def resolver(entrada: EstadoTermo, backend: PropertyBackend, *, P_salida: float,
             eta_p: float, m: float) -> tuple[EstadoTermo, dict]:
    """Comprime la corriente 1 hasta la 2 a ``P_salida`` [kPa].

    Devuelve ``(estado 2, {"Wp": kW, "h2s": kJ/kg})``.
    """
    if not 0.0 < eta_p <= 1.0:
        raise ValueError(f"eta_p={eta_p} fuera de (0, 1]")
    if P_salida < entrada.P:
        raise ValueError(f"la bomba no expande: P_salida={P_salida} < P1={entrada.P} kPa")
    h1 = entrada.h
    h2s = backend.h(P_salida, s=entrada.s)
    h2 = h1 + (h2s - h1) / eta_p
    estado2 = estado_Ph(backend, P_salida, h2, m=m, etiqueta="2")
    return estado2, {"Wp": m * (h2 - h1), "h2s": h2s}
