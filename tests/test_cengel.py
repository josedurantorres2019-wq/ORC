"""Prueba de unidad del modo R con agua: Çengel cap. 10, Ej. 10-1 y Ej. 10-7.

Es la prueba que D-15 §2.4 fija para el modo R. El libro usa tablas de vapor redondeadas:
se aceptan diferencias de décimas de % (nota de Çengel en la bóveda, §3). Datos del libro:
3 MPa / 350 °C → 75 kPa, ciclo ideal; Ej. 10-7 con T_H = 800 K, T_L = T0 = 300 K.
Valores esperados: w_b = 3,03; q_ent = 2728,6; q_sal = 2018,6 kJ/kg; x4 = 0,886;
η = 26,0 %; x_dest,2-3 = 636; x_dest,4-1 = 360 kJ/kg; η_II (convención del libro) = 41,7 %.

El ciclo cierra por efectividades (como el Kalina): ε_ev y ε_cond se eligen para que salgan
los estados del libro (T3 = 350 °C, estado 1 líquido saturado). Las efectividades se sacan
de la cadena ideal del libro 1 → 2 → 3 → 4; el lazo en h1 debe converger a ese mismo ciclo.
"""

from __future__ import annotations

import pytest

from src.components import bomba, turbina
from src.components._estado import estado_Ph
from src.cycle_solver import resolver_ciclo_R
from src.exergy import calcular_exergia

P_EV, P_CD, T3, T_H, T_L = 3000.0, 75.0, 623.15, 800.0, 300.0


def _eps_del_libro(agua) -> tuple[float, float]:
    e1 = estado_Ph(agua, P_CD, agua.h(P_CD, q=0.0), m=1.0, etiqueta="1")
    e2, _ = bomba.resolver(e1, agua, P_salida=P_EV, eta_p=1.0, m=1.0)
    h3 = agua.h(P_EV, T=T3)
    eps_ev = (h3 - e2.h) / (agua.h(P_EV, T=T_H) - e2.h)
    e4, _ = turbina.resolver(estado_Ph(agua, P_EV, h3, m=1.0, etiqueta="3"), agua,
                             P_salida=P_CD, eta_t=1.0)
    eps_cond = (e4.h - e1.h) / (e4.h - agua.h(P_CD, T=T_L))
    return eps_ev, eps_cond


def _resolver(agua, eps_ev, eps_cond):
    return resolver_ciclo_R(agua, T_fuente=T_H, T_sumidero=T_L, P_ev=P_EV, P_cd=P_CD,
                            eps_cond=eps_cond, eta_t=1.0, eta_p=1.0, eps_ev=eps_ev, m=1.0,
                            eps_rec=None)


@pytest.fixture(scope="module")
def ciclo(agua):
    r = _resolver(agua, *_eps_del_libro(agua))
    return r, calcular_exergia(r, agua, T0=T_L, P0=101.325)


def test_ej_10_1(agua, ciclo):
    r, _ = ciclo
    assert r["estados"]["e1"].h == pytest.approx(agua.h(P_CD, q=0.0), abs=1e-5)
    assert r["estados"]["e3"].T == pytest.approx(T3, abs=1e-4)
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
    r2 = _resolver(agua, *_eps_del_libro(agua))
    assert r2["Wnet"] == r["Wnet"]
