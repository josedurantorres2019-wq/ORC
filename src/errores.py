"""Excepciones del ciclo: distinguir «no convergió» (N1) de «el punto no existe».

Lección del Kalina (calificación del motor, Paso 5): las dos se cuentan por separado.
"""

from __future__ import annotations

__all__ = ["CicloNoConvergeError", "CicloSinSolucionError"]


class CicloNoConvergeError(RuntimeError):
    """El lazo no llegó a la tolerancia (N1). Distinto de «el punto no existe»."""


class CicloSinSolucionError(ValueError):
    """El punto pedido no existe físicamente (no es un fallo numérico)."""
