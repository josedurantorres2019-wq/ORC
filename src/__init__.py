"""Núcleo de cálculo del ciclo ORC subcrítico simple (D-14, D-15).

Organización por capas, la misma del Kalina tercero:

    properties/  contrato `PropertyBackend` + `CoolPropAdapter` (el único que importa CoolProp)
    components/  un archivo por equipo, funciones puras `resolver(...)`
    cycle_solver resuelve el ciclo cerrando por efectividades (modo R, cierre B, D-16)
    exergy       exergía física, Ė_d por componente y η_II
    restricciones/  criterios N/S/O/L con ficha `Falla`; la más severa manda

`EstadoTermo` (state.py) es lo único que viaja entre componentes. Unidades canónicas:
T [K], P [kPa], h [kJ/kg], s [kJ/(kg·K)], v [m³/kg], m [kg/s], potencias [kW].
Valores y criterios: solo `02_modelo/definiciones.yaml` (lector en `definiciones.py`).
"""
