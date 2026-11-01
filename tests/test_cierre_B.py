"""Cierre B del condensador (D-16, como el Kalina tercero), probado con AGUA.

El agua no es fluido del estudio: aquí se prueba el código (lazo en h1, balances, O2), no
se evalúa ningún caso. Los números son entradas de prueba.
"""

from __future__ import annotations

import pytest

from src.cycle_solver import CicloSinSolucionError, resolver_ciclo_R
from src.exergy import calcular_exergia
from src.restricciones import evaluar_ciclo

T_SUM = 300.0
B_KW = dict(T_fuente=800.0, T_sumidero=T_SUM, P_ev=1000.0, P_cd=75.0,
            eta_t=0.85, eta_p=0.75, eps_ev=0.95, m=1.0)
CRIT = {"tol_N2": 1e-3, "tol_exergia": 1e-3, "x4_min": 0.0, "x3_min": 1.0, "f_Pcrit": 1.0,
        "T3_max": None, "T_amb_max": None}


def _ciclo(agua, eps_cond, eps_rec=None):
    r = resolver_ciclo_R(agua, eps_cond=eps_cond, eps_rec=eps_rec, **B_KW)
    ex = calcular_exergia(r, agua, T0=T_SUM, P0=101.325)
    v = evaluar_ciclo(r, ex, agua, criterios=CRIT,
                      eps={"eps_ev": 0.95, "eps_rec": eps_rec, "eps_cond": eps_cond})
    return r, ex, {f.codigo for f in v.fallas}


@pytest.mark.parametrize("eps_rec", [None, 0.5])
def test_lazo_h1_cierra_balances(agua, eps_rec):
    r, ex, _ = _ciclo(agua, 0.95, eps_rec)
    e = r["estados"]
    assert 1 < r["iteraciones"] < 50
    assert r["N2"] < 1e-9 and ex["cierre_exergia"] < 1e-9
    assert all(v >= -1e-12 for v in ex["Sgen"].values())
    h1_min = agua.h(75.0, T=T_SUM)
    eps_real = (e["e4r"].h - e["e1"].h) / (e["e4r"].h - h1_min)
    assert eps_real == pytest.approx(0.95, abs=1e-8)          # la ε usada es la dada
    assert len({x.m for x in e.values()}) == 1


def test_eps_alta_liquido_comprimido_y_O2_pasa(agua):
    r, _, fallas = _ciclo(agua, 0.95)
    e1 = r["estados"]["e1"]
    assert e1.fase == "liquido" and e1.T < agua.T_sat(75.0)    # comprimido (subenfriado)
    assert "O2" not in fallas


def test_eps_baja_bifasico_y_O2_falla(agua):
    """El ciclo con estos datos no funciona: el condensador no alcanza a condensar todo."""
    r, _, fallas = _ciclo(agua, 0.80)
    assert r["estados"]["e1"].fase == "bifasico"
    assert "O2" in fallas


def test_entradas_fuera_de_rango(agua):
    with pytest.raises(ValueError):                  # ε_cond fuera de [0, 1]
        resolver_ciclo_R(agua, eps_cond=1.2, eps_rec=None, **B_KW)
    with pytest.raises(CicloSinSolucionError):       # P_cd >= P_ev
        resolver_ciclo_R(agua, eps_cond=0.9, eps_rec=None, **dict(B_KW, P_cd=1000.0))
