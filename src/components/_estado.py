"""Ayuda privada: construir un `EstadoTermo` completo a partir de (P, h)."""

from __future__ import annotations

from ..properties.adapter import PropertyBackend
from ..state import EstadoTermo

__all__ = ["estado_Ph"]


def estado_Ph(backend: PropertyBackend, P: float, h: float, *, m: float | None,
              etiqueta: str) -> EstadoTermo:
    """Flash (P, h) del backend → `EstadoTermo` con T, s, v, q y fase llenos."""
    p = backend.estado_Ph(P, h)
    return EstadoTermo(T=p["T"], P=P, h=h, s=p["s"], v=p["v"], m=m, q=p["q"],
                       fase=p["fase"], etiqueta=etiqueta)
