"""Análisis exergético del ORC: exergía FÍSICA, Ė_d por componente y η_II (D-15 §2.4).

Igual que en el Kalina (H14):
    ex   = (h − h0) − T0 (s − s0),  h0, s0 = h, s(P0, T0) del MISMO fluido y motor
    Ė_d,k = T0 Ṡ_gen,k
El estado muerto se evalúa en la fase real del fluido a (T0, P0): gas para n-butano y
R1234yf, líquido para MM (revisión D, H17 pendiente); no afecta a Ė_d ni a η_II.

Ṡ_gen por componente [kW/K]:
    evaporador   R: ṁ(s3 − s2r) − Q̇_in/T_fuente        F: ṁ(s3 − s2r) + ṁ_f c̄_p ln(T_f2/T_f1)
    turbina         ṁ(s4 − s3)
    recuperador     ṁ[(s4r − s4) + (s2r − s2)]
    condensador  R: ṁ(s1 − s4r) + Q̇_out/T_sumidero     F: ṁ(s1 − s4r) + ṁ_w c_p,w ln(T_w2/T_w1)
    bomba           ṁ(s2 − s1)
Modo R:  Ė_Qin = Q̇_in(1 − T0/T_fuente), Ė_Qout = Q̇_out(1 − T0/T_sumidero), η_II = Ẇ_net/Ė_Qin,
         cierre Ė_Qin − Ẇ_net − Ė_Qout = ΣĖ_d.
Modo F:  fuente y agua como líquidos ideales de c̄_p constante (sin término de presión):
         ex(T) = c̄_p[(T − T0) − T0 ln(T/T0)];  η_II = Ẇ_net/Ė_f1;
         cierre Ė_f1 − Ė_f2 − Ẇ_net − (Ė_w2 − Ė_w1) = ΣĖ_d.
El cierre es una identidad si el balance de energía cierra (revisión C): sirve para atrapar
errores de código, no para validar la física.
"""

from __future__ import annotations

from dataclasses import replace
from math import log

from .properties.adapter import PropertyBackend
from .state import EstadoTermo

__all__ = ["exergia_fisica", "calcular_exergia"]

_COMPONENTES = ("evaporador", "turbina", "recuperador", "condensador", "bomba")


def exergia_fisica(estado: EstadoTermo, backend: PropertyBackend, *, T0: float,
                   P0: float) -> float:
    """Exergía física específica [kJ/kg] de ``estado``."""
    h0, s0 = backend.h(P0, T=T0), backend.s(P0, T=T0)
    return (estado.h - h0) - T0 * (estado.s - s0)


def _ex_liquido(cp: float, T: float, T0: float) -> float:
    """Exergía específica [kJ/kg] de un líquido ideal de c_p constante."""
    return cp * ((T - T0) - T0 * log(T / T0))


def calcular_exergia(resultado: dict, backend: PropertyBackend, *, T0: float,
                     P0: float) -> dict:
    """Exergía de los 6 estados, Ṡ_gen y Ė_d por componente, η_II y cierre relativo."""
    e, m, modo = resultado["estados"], resultado["m"], resultado["modo"]
    h0, s0 = backend.h(P0, T=T0), backend.s(P0, T=T0)
    estados = {k: replace(v, exergia_fisica=(v.h - h0) - T0 * (v.s - s0)) for k, v in e.items()}
    s = {k: v.s for k, v in e.items()}
    Wnet, Qin, Qout = resultado["Wnet"], resultado["Qin"], resultado["Qout"]

    sgen = {"turbina": m * (s["e4"] - s["e3"]),
            "recuperador": m * ((s["e4r"] - s["e4"]) + (s["e2r"] - s["e2"])),
            "bomba": m * (s["e2"] - s["e1"])}
    out = {"estados": estados, "T0": T0, "P0": P0}
    if modo == "R":
        Tf, Ts = resultado["T_fuente"], resultado["T_sumidero"]
        sgen["evaporador"] = m * (s["e3"] - s["e2r"]) - Qin / Tf
        sgen["condensador"] = m * (s["e1"] - s["e4r"]) + Qout / Ts
        Ex_in, Ex_out = Qin * (1.0 - T0 / Tf), Qout * (1.0 - T0 / Ts)
        out.update(Ex_Qin=Ex_in, Ex_Qout=Ex_out, eta_II=Wnet / Ex_in,
                   eta_II_cengel=resultado["Wt"] / (Ex_in + resultado["Wp"]))  # no adoptada
        balance = Ex_in - Wnet - Ex_out
        referencia = Ex_in
    elif modo == "F":
        mf, cpf, mw, cpw = (resultado[k] for k in ("m_f", "cp_f", "m_w", "cp_w"))
        Tf1, Tf2, Tw1, Tw2 = (resultado[k] for k in ("T_f1", "T_f2", "T_w1", "T_w2"))
        sgen["evaporador"] = m * (s["e3"] - s["e2r"]) + mf * cpf * log(Tf2 / Tf1)
        Ex_f1, Ex_f2 = mf * _ex_liquido(cpf, Tf1, T0), mf * _ex_liquido(cpf, Tf2, T0)
        if mw is None:      # T_cd dada: sumidero = reservorio a T_w1 (cierre del benchmark)
            sgen["condensador"] = m * (s["e1"] - s["e4r"]) + Qout / Tw1
            Ex_w1, Ex_w2 = 0.0, Qout * (1.0 - T0 / Tw1)
        else:
            sgen["condensador"] = m * (s["e1"] - s["e4r"]) + mw * cpw * log(Tw2 / Tw1)
            Ex_w1, Ex_w2 = mw * _ex_liquido(cpw, Tw1, T0), mw * _ex_liquido(cpw, Tw2, T0)
        out.update(Ex_f1=Ex_f1, Ex_f2=Ex_f2, Ex_w1=Ex_w1, Ex_w2=Ex_w2, eta_II=Wnet / Ex_f1,
                   eta_II_ced=Wnet / (Ex_f1 - Ex_f2),                      # informativo
                   phi=Qin / (mf * cpf * (Tf1 - T0)))
        balance = Ex_f1 - Ex_f2 - Wnet - (Ex_w2 - Ex_w1)
        referencia = Ex_f1
    else:
        raise ValueError(f"modo desconocido: {modo!r}")

    Ed = {k: T0 * sgen[k] for k in _COMPONENTES}
    Ed_total = sum(Ed.values())
    out.update(Sgen=sgen, Ed=Ed, Ed_total=Ed_total,
               cierre_exergia=abs(balance - Ed_total) / abs(referencia))
    return out
