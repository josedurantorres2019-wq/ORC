"""Pruebas que PUEDEN fallar (revisión C): cada criterio se dispara con un punto sintético.

Los puntos se arman a mano (no salen del solver), así que esto prueba la lógica de
clasificación sin resolver el ciclo.
"""

from __future__ import annotations

import pytest

from src.restricciones import Clasificacion, evaluar_ciclo
from src.state import EstadoTermo

CRIT = {"tol_N2": 1e-3, "tol_exergia": 1e-3, "x4_min": 0.90, "x3_min": 1.0,
        "T_amb_max": None,  # ambiente = sumidero; O2 se prueba con agua en test_o2.py
        "f_Pcrit": 0.90, "T3_max": None, "dT_pp_ev": 10.0, "dT_pp_cd": 10.0}
EPS = {"eps_ev": 0.85, "eps_rec": None}


class _Fake:
    """Backend mínimo: O2 solo pide h_l(P_cd); se elige para que O2 pase (O2: test_o2.py)."""
    def h(self, P, q=None, T=None, s=None):
        return 1e9


FAKE = _Fake()


def _e(T, s, q, et):
    return EstadoTermo(T=T, P=1.0, h=0.0, s=s, m=1.0, q=q, etiqueta=et)


def _base(**cambios):
    e = {"e1": _e(310.0, 1.00, 0.0, "1"), "e2": _e(311.0, 1.01, 0.0, "2"),
         "e3": _e(400.0, 2.00, 1.0, "3"), "e4": _e(330.0, 2.01, 1.0, "4")}
    e["e2r"], e["e4r"] = e["e2"], e["e4"]
    r = {"modo": "R", "m": 1.0, "estados": e, "Qin": 100.0, "Qout": 90.0, "Wnet": 10.0,
         "eta": 0.10, "N2": 0.0, "Qrec": 0.0, "T_fuente": 420.0, "T_sumidero": 300.0,
         "T_sat_cd": 310.0, "P_ev": 2000.0, "P_cd": 100.0, "P_ev_sobre_Pcrit": 0.5}
    for k, v in cambios.items():
        if k in e:
            e[k] = v
        else:
            r[k] = v
    return r


def _codigos(r, ex=None, eps=EPS):
    return {f.codigo for f in evaluar_ciclo(r, ex, FAKE, criterios=CRIT, eps=eps).fallas}


def test_punto_limpio_es_admisible():
    v = evaluar_ciclo(_base(), None, FAKE, criterios=CRIT, eps=EPS)
    assert v.clasificacion == Clasificacion.ADMISIBLE and not v.fallas


@pytest.mark.parametrize("cambio, codigo, clase", [
    ({"N2": 2e-3}, "N2", Clasificacion.NO_CONVERGIO),
    ({"e4": _e(330.0, 1.99, 1.0, "4")}, "S1", Clasificacion.INVIABLE),
    ({"e2": _e(311.0, 0.99, 0.0, "2")}, "S2", Clasificacion.INVIABLE),
    ({"e3": _e(430.0, 2.0, 1.0, "3")}, "S5", Clasificacion.INVIABLE),
    ({"e1": _e(299.0, 1.0, 0.0, "1")}, "S6", Clasificacion.INVIABLE),
    ({"eta": 0.30}, "S8", Clasificacion.INVIABLE),
    ({"e4": _e(330.0, 2.01, 0.85, "4")}, "O1", Clasificacion.CORREGIBLE),
    ({"Wnet": -1.0, "eta": -0.01}, "O3", Clasificacion.INVIABLE),
    ({"e3": _e(400.0, 2.0, 0.97, "3")}, "O5", Clasificacion.INVIABLE),
    ({"P_ev_sobre_Pcrit": 0.95}, "L1", Clasificacion.CORREGIBLE),
])
def test_cada_criterio_se_dispara(cambio, codigo, clase):
    r = _base(**cambio)
    v = evaluar_ciclo(r, None, FAKE, criterios=CRIT, eps=EPS)
    assert any(f.codigo == codigo and f.clasificacion == clase for f in v.fallas)


def test_x4_humedo_solo_si_x4_menor_que_1():
    assert "O1" not in _codigos(_base(e4=_e(330.0, 2.01, 1.0, "4")))


def test_S7_S4_Sg_L2_L3():
    assert "S7" in _codigos(_base(), eps={"eps_ev": 1.2, "eps_rec": None})
    r = _base(Qrec=5.0, e2r=_e(335.0, 1.2, 0.0, "2r"))
    assert "S4" in _codigos(r)
    ex = {"cierre_exergia": 0.0, "Sgen": {"turbina": -1e-3}}
    assert {"Sg"} <= _codigos(_base(), ex)
    assert "N2x" in _codigos(_base(), {"cierre_exergia": 1e-2, "Sgen": {}})
    crit = dict(CRIT, T3_max=390.0)
    assert "L2" in {f.codigo for f in evaluar_ciclo(_base(), None, FAKE, criterios=crit, eps=EPS).fallas}
    rF = _base(modo="F", T_f1=420.0, T_w1=300.0, dT_min_ev=9.0, dT_min_cd=10.0)
    assert "L3" in _codigos(rF)


def test_la_mas_severa_manda():
    v = evaluar_ciclo(_base(N2=1.0, eta=0.5), None, FAKE, criterios=CRIT, eps=EPS)
    assert v.clasificacion == Clasificacion.NO_CONVERGIO and v.principal.codigo == "N2"
