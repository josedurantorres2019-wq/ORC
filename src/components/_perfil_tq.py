"""Ayuda privada: perfil T(h) del fluido a P constante, para revisar el pinch (modo F).

H12: intercambiadores en contracorriente. El perfil se discretiza en ``n_tramos`` tramos
iguales de entalpía y se le añaden los puntos de saturación que caigan dentro del intervalo
(burbuja y rocío), que es donde suele estar el pinch de un fluido puro.
"""

from __future__ import annotations

from ..properties.adapter import PropertyBackend, PropertyRangeError

__all__ = ["perfil_T"]


def perfil_T(backend: PropertyBackend, P: float, h_ini: float, h_fin: float, *,
             n_tramos: int) -> list[tuple[float, float]]:
    """Lista ordenada de (h [kJ/kg], T [K]) entre ``h_ini`` y ``h_fin`` a ``P`` [kPa]."""
    if n_tramos < 1:
        raise ValueError(f"n_tramos={n_tramos} < 1")
    lo, hi = min(h_ini, h_fin), max(h_ini, h_fin)
    hs = {lo + (hi - lo) * i / n_tramos for i in range(n_tramos + 1)}
    if P < backend.P_crit:
        try:
            hs.update(hq for hq in (backend.h(P, q=0.0), backend.h(P, q=1.0)) if lo < hq < hi)
        except PropertyRangeError:
            pass
    return [(h, backend.estado_Ph(P, h)["T"]) for h in sorted(hs)]
