"""Ciclo completo con AGUA (no es un fluido del estudio): cubre el lazo del recuperador y
las rutas de error (revisión, huecos 1-4).

Las entradas son genéricas: aquí se prueba el código, no se evalúa ningún caso del estudio.
"""

from __future__ import annotations

import pytest

from src.cycle_solver import CicloSinSolucionError, resolver_ciclo_R
from src.exergy import calcular_exergia
from src.restricciones import Clasificacion, evaluar_ciclo

T0, P0 = 300.0, 101.325
R_KW = dict(T_fuente=800.0, T_sumidero=300.0, P_ev=1000.0, P_cd=75.0, eps_cond=0.95,
            eta_t=0.85, eta_p=0.75, eps_ev=0.95, m=1.0)


def _cierres(r, ex):
    assert r["N2"] < 1e-9 and ex["cierre_exergia"] < 1e-9
    assert all(v >= -1e-12 for v in ex["Sgen"].values()), ex["Sgen"]
    assert len({e.m for e in r["estados"].values()}) == 1


@pytest.mark.parametrize("eps_rec", [0.0, 0.5])
def test_lazo_recuperador_R(agua, eps_rec):
    r = resolver_ciclo_R(agua, eps_rec=eps_rec, **R_KW)
    ex = calcular_exergia(r, agua, T0=T0, P0=P0)
    _cierres(r, ex)
    assert r["iter_rec"] < 50
    assert r["estados"]["e4"].fase == "vapor"            # escape sobrecalentado: hay recuperación
    if eps_rec == 0.0:
        sin = resolver_ciclo_R(agua, eps_rec=None, **R_KW)
        assert r["Wnet"] == pytest.approx(sin["Wnet"], rel=1e-9)
    else:
        assert r["Qrec"] > 0.0


def test_recuperador_alto_con_liquido_comprimido_lo_marca_Sg(agua):
    """Hallazgo 2026-10-31 (ya estaba en el commit 5100776): con el cierre B el estado 2
    sale muy subenfriado y con ε_rec = 0,9 el recuperador da Ṡ_gen < 0 (cruce interno de
    temperaturas, que la revisión D1 solo mira en los extremos). El punto no es físico:
    el criterio Sg tiene que marcarlo INVIABLE."""
    r = resolver_ciclo_R(agua, eps_rec=0.9, **R_KW)
    ex = calcular_exergia(r, agua, T0=T0, P0=P0)
    assert ex["Sgen"]["recuperador"] < 0.0
    crit = {"tol_N2": 1e-3, "tol_exergia": 1e-3, "x4_min": 0.0, "x3_min": 1.0, "f_Pcrit": 1.0,
            "T3_max": None, "T_amb_max": None}
    v = evaluar_ciclo(r, ex, agua, criterios=crit,
                      eps={"eps_ev": 0.95, "eps_rec": 0.9, "eps_cond": 0.95})
    assert any(f.codigo == "Sg" and f.clasificacion == Clasificacion.INVIABLE for f in v.fallas)


def test_rutas_de_error(agua):
    with pytest.raises(CicloSinSolucionError):           # supercrítico
        resolver_ciclo_R(agua, eps_rec=None, **dict(R_KW, P_ev=1.01 * agua.P_crit))
    with pytest.raises(CicloSinSolucionError):           # P_cd >= P_ev
        resolver_ciclo_R(agua, eps_rec=None, **dict(R_KW, P_cd=1000.0))
