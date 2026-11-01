"""O2 con la lógica del Kalina tercero, cierre A, probado con AGUA (no es fluido del estudio).

El cierre B (vigente) se prueba en test_cierre_B.py.

Los números son entradas de prueba del código, no valores del caso: T_amb y T_sumidero
del estudio no están fijados (se definen con la corrida de validación).
"""

from __future__ import annotations

import pytest

from src.cycle_solver import resolver_ciclo_R
from src.restricciones import evaluar_ciclo
from src.restricciones.operativos import h1_peor_ambiente

T_SUM = 300.0
KW = dict(T_fuente=800.0, T_sumidero=T_SUM, P_ev=1000.0, dT_cd=10.0, P_cd=None, eps_cond=None,
          eta_t=0.85, eta_p=0.75, eps_ev=0.95, m=1.0, eps_rec=None)
CRIT = {"tol_N2": 1e-3, "tol_exergia": 1e-3, "x4_min": 0.0, "x3_min": 1.0, "f_Pcrit": 1.0,
        "T3_max": None, "dT_pp_ev": None, "dT_pp_cd": None}


def _o2(agua, *, dT_sc, T_amb):
    r = resolver_ciclo_R(agua, dT_sc=dT_sc, **KW)
    v = evaluar_ciclo(r, None, agua, criterios=dict(CRIT, T_amb_max=T_amb),
                      eps={"eps_ev": KW["eps_ev"]})
    return r, "O2" in {f.codigo for f in v.fallas}


def test_mismo_ambiente_que_el_diseno_pasa(agua):
    """T_amb = T_sumidero: el condensador re-resuelto reproduce el estado 1 de diseño."""
    r, falla = _o2(agua, dT_sc=0.0, T_amb=T_SUM)
    h1p, _, _ = h1_peor_ambiente(r, agua, T_amb_max=T_SUM)
    assert h1p == pytest.approx(r["estados"]["e1"].h, abs=1e-9) and not falla


def test_sin_subenfriamiento_falla_con_ambiente_mas_caliente(agua):
    """Cierre A deja líquido saturado sin margen: cualquier T_amb > T_sumidero da bifásico."""
    _, falla = _o2(agua, dT_sc=0.0, T_amb=T_SUM + 0.5)
    assert falla


def test_subenfriamiento_da_margen(agua):
    _, falla = _o2(agua, dT_sc=5.0, T_amb=T_SUM + 0.5)
    assert not falla


def test_sumidero_por_encima_de_T_sat_falla(agua):
    _, falla = _o2(agua, dT_sc=5.0, T_amb=T_SUM + 20.0)       # T_sat(P_cd) = T_SUM + 10
    assert falla


def test_sin_T_amb_usa_el_sumidero(agua):
    """T_amb_max = None: ambiente = sumidero; con el cierre A, O2 pasa por construcción."""
    r = resolver_ciclo_R(agua, dT_sc=0.0, **KW)
    v = evaluar_ciclo(r, None, agua, criterios=dict(CRIT, T_amb_max=None), eps={})
    assert "O2" not in {f.codigo for f in v.fallas}
