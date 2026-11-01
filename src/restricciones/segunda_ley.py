"""Criterios de segunda ley S1, S2, S4-S8 (críticos: INVIABLE). D-15 §4.1.

S3 no aplica (no hay válvula). S4 solo con recuperador. En modo F, S5/S6 se miden contra
la entrada de la fuente (T_f1) y del agua (T_w1), y S8 contra 1 − T_w1/T_f1.
"""

from __future__ import annotations

from .modelos import Clasificacion, Falla, Severidad

__all__ = ["verificar_segunda_ley"]

_TOL_S = 1e-9     # kJ/(kg·K): ruido del flash en procesos isentrópicos (η = 1)


def _crit(codigo, mensaje, variable, medido, esperado, sugerencia) -> Falla:
    return Falla(codigo, Severidad.CRITICO, Clasificacion.INVIABLE, mensaje, variable,
                 medido, esperado, sugerencia)


def verificar_segunda_ley(resultado: dict, *, eps: dict, sgen: dict | None) -> list[Falla]:
    """``eps``: efectividades usadas, p.ej. {"eps_ev": 0.85, "eps_rec": None}.

    ``sgen``: Ṡ_gen por componente de `exergy.calcular_exergia` (o None). Añade «Sg»
    (propuesta): ningún componente puede generar entropía negativa.
    """
    e, f = resultado["estados"], []
    for comp, valor in (sgen or {}).items():
        if valor < -_TOL_S * resultado["m"]:
            f.append(_crit("Sg", f"Ṡ_gen < 0 en {comp}", f"Sgen[{comp}]", valor, ">= 0",
                           "revisar el balance de entropía de ese componente"))
    R = resultado["modo"] == "R"
    T_alta = resultado["T_fuente"] if R else resultado["T_f1"]
    T_baja = resultado["T_sumidero"] if R else resultado["T_w1"]

    if e["e4"].s < e["e3"].s - _TOL_S:
        f.append(_crit("S1", "la entropía cae en la turbina", "s4 − s3",
                       e["e4"].s - e["e3"].s, ">= 0", "revisar eta_t y h4s"))
    if e["e2"].s < e["e1"].s - _TOL_S:
        f.append(_crit("S2", "la entropía cae en la bomba", "s2 − s1",
                       e["e2"].s - e["e1"].s, ">= 0", "revisar eta_p y h2s"))
    if resultado["Qrec"] < 0.0:
        f.append(_crit("S4", "el recuperador pasa calor del lado frío al caliente", "Qrec",
                       resultado["Qrec"], ">= 0", "apagar el recuperador en este punto"))
    if resultado["Qrec"] != 0.0:
        cruce = min(e["e4"].T - e["e2r"].T, e["e4r"].T - e["e2"].T)
        if cruce < 0.0:
            f.append(_crit("S4", "cruce de temperaturas en el recuperador",
                           "mín(T4 − T2r, T4r − T2)", cruce, "> 0", "reducir eps_rec"))
    if e["e3"].T > T_alta:
        f.append(_crit("S5", "la salida del evaporador supera la T de la fuente", "T3",
                       e["e3"].T, f"<= {T_alta:.3f} K", "reducir eps_ev o P_ev"))
    if e["e1"].T < T_baja:
        f.append(_crit("S6", "la salida del condensador queda bajo la T del sumidero", "T1",
                       e["e1"].T, f">= {T_baja:.3f} K", "subir dT_cd o P_cd"))
    for nombre, v in eps.items():
        if v is not None and not 0.0 <= v <= 1.0:
            f.append(_crit("S7", f"{nombre} fuera de [0, 1]", nombre, v, "[0, 1]",
                           f"corregir {nombre}"))
    carnot = 1.0 - T_baja / T_alta
    if resultado["eta"] >= carnot:
        f.append(_crit("S8", "η_I supera la cota de Carnot", "eta", resultado["eta"],
                       f"< {carnot:.6g}", "revisar N2 y las temperaturas de reservorio"))
    return f
