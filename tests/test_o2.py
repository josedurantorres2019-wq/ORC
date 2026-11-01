"""O2 con la lógica del Kalina tercero, cierre por efectividades, probado con AGUA.

El agua no es fluido del estudio. Los números son entradas de prueba del código, no valores
del caso: T_amb y T_sumidero del estudio no están fijados (se definen con la corrida de
validación). Con T_sumidero = 300 K y P_cd = 75 kPa, T_sat(P_cd) ≈ 365 K.
"""

from __future__ import annotations

import pytest

from src.cycle_solver import resolver_ciclo_R
from src.restricciones import evaluar_ciclo
from src.restricciones.operativos import h1_peor_ambiente

T_SUM, P_CD = 300.0, 75.0
KW = dict(T_fuente=800.0, T_sumidero=T_SUM, P_ev=1000.0, P_cd=P_CD, eta_t=0.85, eta_p=0.75,
          eps_ev=0.95, m=1.0, eps_rec=None)
CRIT = {"tol_N2": 1e-3, "tol_exergia": 1e-3, "x4_min": 0.0, "x3_min": 1.0, "f_Pcrit": 1.0,
        "T3_max": None}


def _o2(agua, *, eps_cond, T_amb):
    r = resolver_ciclo_R(agua, eps_cond=eps_cond, **KW)
    v = evaluar_ciclo(r, None, agua, criterios=dict(CRIT, T_amb_max=T_amb),
                      eps={"eps_ev": KW["eps_ev"], "eps_cond": eps_cond})
    return r, "O2" in {f.codigo for f in v.fallas}


def test_mismo_ambiente_que_el_diseno_pasa(agua):
    """T_amb = T_sumidero: el condensador re-resuelto reproduce el estado 1 de diseño."""
    r, falla = _o2(agua, eps_cond=0.95, T_amb=T_SUM)
    h1p, _, _ = h1_peor_ambiente(r, agua, T_amb_max=T_SUM)
    assert h1p == pytest.approx(r["estados"]["e1"].h, abs=1e-9) and not falla


def test_ambiente_mas_caliente_empeora_la_succion(agua):
    r, _ = _o2(agua, eps_cond=0.95, T_amb=T_SUM)
    h1p, _, _ = h1_peor_ambiente(r, agua, T_amb_max=T_SUM + 20.0)
    assert h1p > r["estados"]["e1"].h


def test_eps_alta_da_margen(agua):
    _, falla = _o2(agua, eps_cond=0.95, T_amb=T_SUM + 20.0)
    assert not falla


def test_eps_baja_falla(agua):
    _, falla = _o2(agua, eps_cond=0.80, T_amb=None)
    assert falla


def test_sumidero_por_encima_de_T_sat_falla(agua):
    _, falla = _o2(agua, eps_cond=0.95, T_amb=agua.T_sat(P_CD) + 1.0)
    assert falla
