"""Cierres del ciclo completo con los fluidos del estudio. MARCADAS `corrida`: NO se corren
por defecto (memoria «no correr sin orden»). Con orden del usuario:  pytest -m corrida

Solo comprueban balances, 2.ª ley y convergencia; no fijan ni imprimen η ni Ẇ (eso es P1).
"""

from __future__ import annotations

import pytest

from src import definiciones as d
from src.cycle_solver import resolver_ciclo_F, resolver_ciclo_R
from src.exergy import calcular_exergia

pytestmark = pytest.mark.corrida


def _comprobar(r, ex, defs):
    assert r["N2"] <= d.valor(defs, "tolerancias.balance_energia_rel")
    assert ex["cierre_exergia"] <= d.valor(defs, "tolerancias.cierre_exergia_rel")
    assert all(v >= -1e-9 for v in ex["Sgen"].values()), ex["Sgen"]
    assert len({e.m for e in r["estados"].values()}) == 1                 # un solo ṁ


@pytest.mark.parametrize("eps_rec", [None, 0.6])
def test_modo_R_cierra(fluido, defs, eps_rec):
    clave, b = fluido
    caso = "enunciado" if clave == "MM" else "diseno"
    kw = d.entradas_R(defs, caso=caso)
    kw["eps_rec"] = eps_rec
    kw["eps_cond"] = 1.0           # límite de la efectividad: solo para probar cierres
    P_cd = b.P_sat(kw["T_sumidero"] + d.valor(defs, "umbrales.dT_cd"))
    P_ev = 0.5 * d.valor(defs, "umbrales.f_Pcrit") * b.P_crit
    r = resolver_ciclo_R(b, P_ev=P_ev, P_cd=P_cd, **kw)
    ex = calcular_exergia(r, b, T0=d.valor(defs, "estado_muerto.T0"),
                          P0=d.valor(defs, "estado_muerto.P0"))
    _comprobar(r, ex, defs)


def test_modo_F_con_agua_cierra(fluido, defs):
    clave, b = fluido
    T_f1 = d.valor(defs, "casos.enunciado.T_fuente" if clave == "MM" else "casos.diseno.T_fuente")
    T0 = d.valor(defs, "estado_muerto.T0")
    P_ev = 0.3 * b.P_crit
    r = resolver_ciclo_F(b, P_ev=P_ev, T_f1=T_f1, m_f=10.0, cp_f=4.2, T_w1=T0, m_w=200.0,
                         cp_w=4.18, dT_pp_ev=d.valor(defs, "umbrales.dT_pp_ev"),
                         dT_pp_cd=d.valor(defs, "umbrales.dT_pp_cd"), dT_sh=0.0, dT_sc=0.0,
                         eta_t=0.85, eta_p=0.75, eps_rec=None)
    ex = calcular_exergia(r, b, T0=T0, P0=d.valor(defs, "estado_muerto.P0"))
    _comprobar(r, ex, defs)
    assert r["dT_min_ev"] >= d.valor(defs, "umbrales.dT_pp_ev") - 1e-6
    assert r["dT_min_cd"] >= d.valor(defs, "umbrales.dT_pp_cd") - 1e-6
