"""Prueba de unidad del modo R con agua (cierre A: el libro fija el estado 1): Çengel cap. 10, Ej. 10-1 y Ej. 10-7.

Es la prueba que D-15 §2.4 fija para el modo R. El libro usa tablas de vapor redondeadas:
se aceptan diferencias de décimas de % (nota de Çengel en la bóveda, §3). Datos del libro:
3 MPa / 350 °C → 75 kPa, ciclo ideal; Ej. 10-7 con T_H = 800 K, T_L = T0 = 300 K.
Valores esperados: w_b = 3,03; q_ent = 2728,6; q_sal = 2018,6 kJ/kg; x4 = 0,886;
η = 26,0 %; x_dest,2-3 = 636; x_dest,4-1 = 360 kJ/kg; η_II (convención del libro) = 41,7 %.
"""

from __future__ import annotations

import pytest

from src.components import bomba, condensador
from src.cycle_solver import resolver_ciclo_R
from src.exergy import calcular_exergia

P_EV, P_CD, T3, T_H, T_L = 3000.0, 75.0, 623.15, 800.0, 300.0


@pytest.fixture(scope="module")
def ciclo(agua):
    # ε_ev que reproduce T3 = 350 °C con la fuente a 800 K (el modo R cierra por ε).
    e1 = condensador.estado_salida(agua, P_cd=P_CD, dT_sc=0.0, m=1.0)
    e2, _ = bomba.resolver(e1, agua, P_salida=P_EV, eta_p=1.0, m=1.0)
    eps = (agua.h(P_EV, T=T3) - e2.h) / (agua.h(P_EV, T=T_H) - e2.h)
    r = resolver_ciclo_R(agua, T_fuente=T_H, T_sumidero=T_L, P_ev=P_EV, dT_cd=None, P_cd=P_CD, eps_cond=None,
                         dT_sc=0.0, eta_t=1.0, eta_p=1.0, eps_ev=eps, m=1.0, eps_rec=None)
    return r, calcular_exergia(r, agua, T0=T_L, P0=101.325)


def test_ej_10_1(ciclo):
    r, _ = ciclo
    assert r["estados"]["e3"].T == pytest.approx(T3, abs=1e-6)
    assert r["Wp"] == pytest.approx(3.03, rel=0.01)
    assert r["Qin"] == pytest.approx(2728.6, rel=0.002)
    assert r["Qout"] == pytest.approx(2018.6, rel=0.002)
    assert r["estados"]["e4"].q == pytest.approx(0.886, abs=0.002)
    assert r["eta"] == pytest.approx(0.260, abs=0.001)
    assert r["r_bw"] == pytest.approx(0.004, abs=0.0005)
    assert r["N2"] < 1e-12


def test_ej_10_7(ciclo):
    r, ex = ciclo
    assert ex["Ed"]["evaporador"] == pytest.approx(636.0, rel=0.005)
    assert ex["Ed"]["condensador"] == pytest.approx(360.0, rel=0.005)
    assert ex["Ed"]["turbina"] == pytest.approx(0.0, abs=1e-6)
    assert ex["Ed"]["bomba"] == pytest.approx(0.0, abs=1e-6)
    assert ex["Ed_total"] == pytest.approx(996.0, rel=0.005)
    assert ex["eta_II_cengel"] == pytest.approx(0.417, abs=0.002)    # variante del libro
    assert ex["cierre_exergia"] < 1e-12


def test_determinismo(agua, ciclo):
    """Mismas entradas → mismos números, bit a bit (calificación del motor, Paso 5)."""
    r, _ = ciclo
    e = r["estados"]
    eps = (e["e3"].h - e["e2r"].h) / (r["h3_max"] - e["e2r"].h)
    r2 = resolver_ciclo_R(agua, T_fuente=T_H, T_sumidero=T_L, P_ev=P_EV, dT_cd=None, P_cd=P_CD, eps_cond=None,
                          dT_sc=0.0, eta_t=1.0, eta_p=1.0, eps_ev=eps, m=1.0, eps_rec=None)
    assert r2["Wnet"] == pytest.approx(r["Wnet"], rel=1e-14)
