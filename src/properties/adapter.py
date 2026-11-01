"""Interfaz abstracta `PropertyBackend` (fluido puro) y excepción `PropertyRangeError`.

Único contrato entre la capa de propiedades y el resto del proyecto. No importa ningún
backend concreto: si F2 obliga a cambiar CoolProp por REFPROP, solo cambia el adapter
(contexto del proyecto, 2026-10-31: «detrás de un adaptador»).

Unidades canónicas de la interfaz, independientes del backend:
P [kPa], T [K], h [kJ/kg], s [kJ/(kg·K)], v [m³/kg].
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

__all__ = ["PropertyBackend", "PropertyRangeError"]


class PropertyRangeError(Exception):
    """El backend no puede cubrir el estado pedido (fuera de rango o sin convergencia).

    Solo la lanzan los adapters; la excepción cruda del motor nunca llega sin envolver al
    solver (lección del Kalina: distinguir «el motor falló» de «el estado no existe»).
    """


class PropertyBackend(ABC):
    """Contrato de propiedades de un fluido puro, en unidades canónicas."""

    fluido: str

    @property
    @abstractmethod
    def P_crit(self) -> float:
        """Presión crítica [kPa]."""

    @property
    @abstractmethod
    def T_crit(self) -> float:
        """Temperatura crítica [K]."""

    @abstractmethod
    def h(self, P: float, *, T: Optional[float] = None, s: Optional[float] = None,
          q: Optional[float] = None) -> float:
        """Entalpía [kJ/kg] con P y exactamente uno de T, s o q (título 0-1)."""

    @abstractmethod
    def s(self, P: float, *, T: Optional[float] = None, h: Optional[float] = None,
          q: Optional[float] = None) -> float:
        """Entropía [kJ/(kg·K)] con P y exactamente uno de T, h o q."""

    @abstractmethod
    def T_sat(self, P: float) -> float:
        """Temperatura de saturación [K] a P [kPa] (P < P_crit)."""

    @abstractmethod
    def P_sat(self, T: float) -> float:
        """Presión de saturación [kPa] a T [K] (T < T_crit)."""

    @abstractmethod
    def estado_Ph(self, P: float, h: float) -> dict:
        """Flash (P, h) → {'T', 's', 'v', 'q', 'fase'} con la convención de `EstadoTermo`."""
