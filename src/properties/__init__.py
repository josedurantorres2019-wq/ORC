"""Capa de propiedades termodinámicas (patrón adapter).

Exporta SOLO la interfaz y la excepción controlada, nunca el backend concreto, para que
`import src.properties` funcione sin CoolProp instalado. El adapter se importa explícito:

    from src.properties.coolprop_adapter import CoolPropAdapter
"""

from .adapter import PropertyBackend, PropertyRangeError

__all__ = ["PropertyBackend", "PropertyRangeError"]
