"""Ciclo completo con AGUA (no es un fluido del estudio): cubre el lazo del recuperador,
el modo F con Brent, la exergía del modo F y las rutas de error (revisión, huecos 1-4).

Las entradas son genéricas: aquí se prueba el código, no se evalúa ningún caso del estudio.
"""

from __future__ import annotations

from math import log

import pytest

from src.cycle_solver import CicloSinSolucionError, resolver_ciclo_F, resolver_ciclo_R
from src.exergy import calcular_exergia

T0, P0 = 300.0, 101.325
R_KW = dict(T_fuente=800.0, T_sumidero=300.0, P_ev=1000.0, dT_cd=None, P_cd=75.0, eps_cond=None, dT_sc=0.0,
            eta_t=0.85, eta_p=0.75, eps_ev=0.95, m=1.0)
F_KW = dict(P_ev=1000.0, T_f1=550.0, m_f=10.0, cp_f=4.2, T_w1=300.0, dT_pp_ev=10.0,
            dT_sh=0.0, dT_sc=0.0, eta_t=0.85, eta_p=0.75, eps_rec=None)


def _cierres(r, ex):
    assert r["N2"] < 1e-9 and ex["cierre_exergia"] < 1e-9
    assert all(v >= -1e-12 for v in ex["Sgen"].values()), ex["Sgen"]
    assert len({e.m for e in r["estados"].values()}) == 1


@pytest.mark.parametrize("eps_rec", [0.0, 0.5, 0.9])
def test_lazo_recuperador_R(agua, eps_rec):
    r = resolver_ciclo_R(agua, eps_rec=eps_rec, **R_KW)
    ex = calcular_exergia(r, agua, T0=T0, P0=P0)
    _cierres(r, ex)
    assert r["iteraciones"] < 50
    assert r["estados"]["e4"].fase == "vapor"            # escape sobrecalentado: hay recuperación
    if eps_rec == 0.0:
        sin = resolver_ciclo_R(agua, eps_rec=None, **R_KW)
        assert r["Wnet"] == pytest.approx(sin["Wnet"], rel=1e-12)
    else:
        assert r["Qrec"] > 0.0


def test_modo_F_agua_finita(agua):
    r = resolver_ciclo_F(agua, m_w=100.0, cp_w=4.18, dT_pp_cd=10.0, **F_KW)
    ex = calcular_exergia(r, agua, T0=T0, P0=P0)
    _cierres(r, ex)
    assert abs(r["residuo_cd"]) < 1e-5
    assert r["Qin"] == pytest.approx(10.0 * 4.2 * (550.0 - r["T_f2"]), rel=1e-10)
    assert r["Qout"] == pytest.approx(100.0 * 4.18 * (r["T_w2"] - 300.0), rel=1e-10)
    assert r["dT_min_ev"] == pytest.approx(10.0, abs=1e-6)
    assert r["dT_min_cd"] >= 10.0 - 1e-6
    Ex_f1 = 10.0 * 4.2 * ((550.0 - T0) - T0 * log(550.0 / T0))
    assert ex["Ex_f1"] == pytest.approx(Ex_f1, rel=1e-12)
    assert ex["eta_II"] == pytest.approx(r["Wnet"] / Ex_f1, rel=1e-12)


def test_modo_F_T_cd_dada(agua):
    r = resolver_ciclo_F(agua, m_w=None, cp_w=None, dT_pp_cd=None, T_cd=320.0, **F_KW)
    ex = calcular_exergia(r, agua, T0=T0, P0=P0)
    _cierres(r, ex)
    assert r["T_sat_cd"] == pytest.approx(320.0, abs=1e-6) and r["iteraciones"] == 0


def test_rutas_de_error(agua):
    with pytest.raises(CicloSinSolucionError):           # agua de enfriamiento insuficiente
        resolver_ciclo_F(agua, m_w=0.5, cp_w=4.18, dT_pp_cd=10.0, **F_KW)
    with pytest.raises(CicloSinSolucionError):           # fuente sin margen para el pinch
        resolver_ciclo_F(agua, m_w=None, cp_w=None, dT_pp_cd=None, T_cd=320.0,
                         **dict(F_KW, T_f1=agua.T_sat(1000.0) + 5.0))
    with pytest.raises(ValueError):                      # T_cd y agua finita a la vez (D4)
        resolver_ciclo_F(agua, m_w=100.0, cp_w=4.18, dT_pp_cd=10.0, T_cd=320.0, **F_KW)
    with pytest.raises(CicloSinSolucionError):           # supercrítico en R
        resolver_ciclo_R(agua, eps_rec=None, **dict(R_KW, P_ev=1.01 * agua.P_crit))
    with pytest.raises(CicloSinSolucionError):           # escape húmedo: T4 <= T2 (D2)
        resolver_ciclo_R(agua, eps_rec=0.5, **dict(R_KW, P_ev=3000.0, eps_ev=0.5, eta_t=1.0))
