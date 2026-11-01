"""Análisis exergético del ORC: exergía FÍSICA, Ė_d por componente y η_II (D-15 §2.4).

Igual que en el Kalina (H14):
    ex   = (h − h0) − T0 (s − s0),  h0, s0 = h, s(P0, T0) del MISMO fluido y motor
    Ė_d,k = T0 Ṡ_gen,k
El estado muerto se evalúa en la fase real del fluido a (T0, P0): gas para n-butano y
R1234yf, líquido para MM (revisión D, H17 pendiente); no afecta a Ė_d ni a η_II.

Ṡ_gen por componente [kW/K]:
    evaporador   ṁ(s3 − s2r) − Q̇_in/T_fuente
    turbina      ṁ(s4 − s3)
    recuperador  ṁ[(s4r − s4) + (s2r − s2)]
    condensador  ṁ(s1 − s4r) + Q̇_out/T_sumidero
    bomba        ṁ(s2 − s1)
Ė_Qin = Q̇_in(1 − T0/T_fuente), Ė_Qout = Q̇_out(1 − T0/T_sumidero), η_II = Ẇ_net/Ė_Qin,
cierre Ė_Qin − Ẇ_net − Ė_Qout = ΣĖ_d. El cierre es una identidad si el balance de energía
cierra (revisión C): sirve para atrapar errores de código, no para validar la física.
"""

from __future__ import annotations

from dataclasses import replace

from .properties.adapter import PropertyBackend
from .state import EstadoTermo

__all__ = ["exergia_fisica", "calcular_exergia"]

_COMPONENTES = ("evaporador", "turbina", "recuperador", "condensador", "bomba")


def exergia_fisica(estado: EstadoTermo, backend: PropertyBackend, *, T0: float,
                   P0: float) -> float:
    """Exergía física específica [kJ/kg] de ``estado``."""
    h0, s0 = backend.h(P0, T=T0), backend.s(P0, T=T0)
    return (estado.h - h0) - T0 * (estado.s - s0)


def calcular_exergia(resultado: dict, backend: PropertyBackend, *, T0: float,
                     P0: float) -> dict:
    """Exergía de los 6 estados, Ṡ_gen y Ė_d por componente, η_II y cierre relativo."""
    e, m = resultado["estados"], resultado["m"]
    h0, s0 = backend.h(P0, T=T0), backend.s(P0, T=T0)
    estados = {k: replace(v, exergia_fisica=(v.h - h0) - T0 * (v.s - s0)) for k, v in e.items()}
    s = {k: v.s for k, v in e.items()}
    Wnet, Qin, Qout = resultado["Wnet"], resultado["Qin"], resultado["Qout"]
    Tf, Ts = resultado["T_fuente"], resultado["T_sumidero"]

    sgen = {"evaporador": m * (s["e3"] - s["e2r"]) - Qin / Tf,
            "turbina": m * (s["e4"] - s["e3"]),
            "recuperador": m * ((s["e4r"] - s["e4"]) + (s["e2r"] - s["e2"])),
            "condensador": m * (s["e1"] - s["e4r"]) + Qout / Ts,
            "bomba": m * (s["e2"] - s["e1"])}
    Ex_in, Ex_out = Qin * (1.0 - T0 / Tf), Qout * (1.0 - T0 / Ts)
    Ed = {k: T0 * sgen[k] for k in _COMPONENTES}
    Ed_total = sum(Ed.values())
    return {"estados": estados, "T0": T0, "P0": P0, "Ex_Qin": Ex_in, "Ex_Qout": Ex_out,
            "eta_II": Wnet / Ex_in,
            "eta_II_cengel": resultado["Wt"] / (Ex_in + resultado["Wp"]),   # no adoptada
            "Sgen": sgen, "Ed": Ed, "Ed_total": Ed_total,
            "cierre_exergia": abs(Ex_in - Wnet - Ex_out - Ed_total) / abs(Ex_in)}
