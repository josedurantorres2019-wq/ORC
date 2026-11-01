"""Criterios operativos O1, O2, O3, O5 y límites L1-L2 del ORC (D-07, D-15 §4.1).

O1  x4 ≥ x4_min, solo si x4 < 1 (fluidos húmedos)            CORREGIBLE (como el Kalina)
O2  cavitación: succión de la bomba líquida en el peor ambiente  CORREGIBLE (O2 del Kalina tercero)
O3  Ẇ_net > 0                                                   INVIABLE
O5  x3 ≥ x3_min: vapor a la turbina (sentido opuesto al O5 del Kalina)   INVIABLE
L1  P_ev ≤ f_Pcrit·P_crit (H16)                                 CORREGIBLE  [propuesta]
L2  T3 ≤ T3_max, estabilidad térmica (H15; solo si hay valor)   CORREGIBLE  [propuesta]

O2, misma lógica que `ciclo_kalina_tercero/src/restricciones/operativos.py` (solo lógica: los
valores de T_amb y T_sumidero los da el caso, aquí no hay números):
    T_amb'  = máx(T_sumidero, T_amb_max)                       peor ambiente
    h1'     = h4r − ε_cd,eq · [h4r − h(P_cd, T_amb')]           condensador re-resuelto con su
                                                                 efectividad de diseño congelada,
                                                                 P_cd y estado 4r fijos
    falla si h1' > h(P_cd, q=0)                                  la bomba recibiría bifásico
Si T_amb' ≥ T_sat(P_cd), el sumidero no puede condensar el fluido: falla directa.
Por H3 (ΔP = 0) la succión está a P_cd: NPSH queda fuera del modelo (limitación declarada).
T_amb_max = None (por defecto) significa ambiente = sumidero, como en la campaña final del
Kalina tercero: T_amb' = T_sumidero y O2 revisa directamente que el estado 1 calculado sea
líquido. Se da aparte solo si el caso tiene un enfriador cuyo sumidero difiere del ambiente.
La ε usada es ``resultado["eps_cond"]``, el dato del cierre B.
"""

from __future__ import annotations

from ..properties.adapter import PropertyBackend
from .modelos import Clasificacion, Falla, Severidad

__all__ = ["verificar_operativos", "h1_peor_ambiente"]

_TOL_Q = 1e-6      # título: la PQ de CoolProp devuelve 1 − O(1e-12) en vapor saturado
_TOL_H = 1e-6      # kJ/kg


def h1_peor_ambiente(resultado: dict, backend: PropertyBackend, *,
                     T_amb_max: float | None) -> tuple[float, float, float]:
    """(h1', h_l(P_cd), T_amb') de O2. h1' = inf si el sumidero no puede condensar."""
    e4r, P_cd = resultado["estados"]["e4r"], resultado["P_cd"]
    T_sum = resultado["T_sumidero"]
    T_amb = T_sum if T_amb_max is None else max(T_sum, T_amb_max)
    h_l = backend.h(P_cd, q=0.0)
    if T_amb == T_sum:                    # mismo sumidero: el estado 1 ya es el de O2
        return resultado["estados"]["e1"].h, h_l, T_amb
    eps = resultado["eps_cond"]
    if eps is None or T_amb >= resultado["T_sat_cd"]:
        return float("inf"), h_l, T_amb
    return e4r.h - eps * (e4r.h - backend.h(P_cd, T=T_amb)), h_l, T_amb


def verificar_operativos(resultado: dict, backend: PropertyBackend, *, x4_min: float,
                         x3_min: float, T_amb_max: float | None, f_Pcrit: float,
                         T3_max: float | None) -> list[Falla]:
    e, f = resultado["estados"], []
    q3, q4 = e["e3"].q, e["e4"].q
    if q4 is not None and q4 < 1.0 - _TOL_Q and q4 < x4_min:
        f.append(Falla("O1", Severidad.TECNOLOGICO, Clasificacion.CORREGIBLE,
                       "título bajo a la salida de la turbina", "x4", q4, f">= {x4_min}",
                       "subir T3 (sobrecalentar) o bajar P_ev"))
    h1p, h_l, T_amb = h1_peor_ambiente(resultado, backend, T_amb_max=T_amb_max)
    if h1p > h_l + _TOL_H:
        f.append(Falla("O2", Severidad.CRITICO, Clasificacion.CORREGIBLE,
                       "succión de la bomba bifásica en el peor ambiente (cavitación)",
                       f"h1' (a T_amb={T_amb:.3f} K)", h1p, f"<= h_l(P_cd) = {h_l:.6g}",
                       "subir eps_cond o P_cd"))
    if resultado["Wnet"] <= 0.0:
        f.append(Falla("O3", Severidad.CRITICO, Clasificacion.INVIABLE,
                       "potencia neta no positiva", "Wnet", resultado["Wnet"], "> 0",
                       "revisar P_ev y las eficiencias"))
    if q3 is None or q3 < x3_min - _TOL_Q:
        f.append(Falla("O5", Severidad.CRITICO, Clasificacion.INVIABLE,
                       "la turbina recibe vapor húmedo", "x3", q3, f">= {x3_min}",
                       "bajar P_ev o subir eps_ev"))
    if resultado["P_ev_sobre_Pcrit"] > f_Pcrit:
        f.append(Falla("L1", Severidad.TECNOLOGICO, Clasificacion.CORREGIBLE,
                       "P_ev demasiado cerca de P_crit", "P_ev/P_crit",
                       resultado["P_ev_sobre_Pcrit"], f"<= {f_Pcrit}", "bajar P_ev"))
    if T3_max is not None and e["e3"].T > T3_max:
        f.append(Falla("L2", Severidad.TECNOLOGICO, Clasificacion.CORREGIBLE,
                       "T3 supera el límite de estabilidad térmica", "T3", e["e3"].T,
                       f"<= {T3_max} K", "bajar P_ev o T3"))
    return f
