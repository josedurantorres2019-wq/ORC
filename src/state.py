"""Tipo compartido `EstadoTermo`: un punto del ciclo ORC.

Contenedor de datos puro, sin lógica de propiedades: los componentes consultan el
`PropertyBackend` y construyen estos estados. Es un fluido puro, así que no lleva
composición (a diferencia del Kalina). Unidades canónicas: T [K], P [kPa], h [kJ/kg],
s [kJ/(kg·K)], v [m³/kg], m [kg/s].

Convención de `q` (la misma del Kalina): 0 = líquido (saturado o comprimido),
1 = vapor (saturado o sobrecalentado), entre 0 y 1 = título en la campana.
Por encima de P_crit la fase es 'supercritico' y `q` queda en None.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["EstadoTermo"]


@dataclass
class EstadoTermo:
    T: float
    P: float
    h: float
    s: float
    v: float | None = None            # m³/kg, para VR = v4/v3
    m: float | None = None            # kg/s, caudal de esta corriente
    q: float | None = None            # título (ver docstring del módulo)
    fase: str | None = None           # 'liquido' | 'bifasico' | 'vapor' | 'supercritico'
    exergia_fisica: float | None = None  # kJ/kg (la llena exergy.py, no los componentes)
    etiqueta: str | None = None       # "1", "2", "2r", "3", "4", "4r"
