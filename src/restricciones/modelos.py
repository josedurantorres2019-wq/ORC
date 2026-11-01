"""Tipos de las restricciones del ORC: `Severidad`, `Clasificacion`, `Falla`, `ResultadoValidacion`.

Mismo esquema que el Kalina (ficha `Falla`, la más severa manda), con la correspondencia
de D-15 §4.1: N2 y N2x numéricos; S1, S2, S4-S8 de segunda ley (S3 no aplica: no hay
válvula); O1, O2, O3, O5 operativos; L1-L3 nuevos (límites del fluido y pinch del modo F).
La etiqueta «KALINA» del Kalina se llama aquí ADMISIBLE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = ["Severidad", "Clasificacion", "Falla", "ResultadoValidacion", "ORDEN"]


class Severidad(str, Enum):
    """TIPO de causa de una falla."""
    NUMERICO = "numerico"
    CRITICO = "critico"
    TECNOLOGICO = "tecnologico"


class Clasificacion(str, Enum):
    """RESULTADO del punto, de más a menos severo."""
    NO_CONVERGIO = "NO_CONVERGIO"
    INVIABLE = "INVIABLE"
    CORREGIBLE = "CORREGIBLE"
    ADMISIBLE = "ADMISIBLE"


ORDEN = {Clasificacion.NO_CONVERGIO: 0, Clasificacion.INVIABLE: 1,
         Clasificacion.CORREGIBLE: 2, Clasificacion.ADMISIBLE: 3}


@dataclass
class Falla:
    codigo: str
    severidad: Severidad
    clasificacion: Clasificacion
    mensaje: str
    variable: str
    valor_medido: float
    valor_esperado: str
    sugerencia: str


@dataclass
class ResultadoValidacion:
    clasificacion: Clasificacion
    fallas: list[Falla] = field(default_factory=list)
    no_aplica: tuple[str, ...] = ()

    @property
    def principal(self) -> Falla | None:
        """La falla más severa (None si el punto es ADMISIBLE)."""
        return min(self.fallas, key=lambda f: ORDEN[f.clasificacion]) if self.fallas else None

    def mensaje_reporte(self) -> str:
        if not self.fallas:
            return "ADMISIBLE: pasa todos los criterios aplicables."
        lineas = []
        for f in sorted(self.fallas, key=lambda f: ORDEN[f.clasificacion]):
            lineas.append(f"[{f.clasificacion.value}] {f.codigo}: {f.mensaje} (medido="
                          f"{f.valor_medido!r}, esperado {f.valor_esperado}). {f.sugerencia}")
        return "\n".join(lineas)
