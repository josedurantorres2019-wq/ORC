"""Cada componente por separado: masa, energía, definiciones de η/ε, 2.ª ley y estados.

Los estados de entrada son genéricos (fracciones de P_crit), no puntos del estudio: aquí se
prueba el código del componente, no se evalúa el ciclo.
"""

from __future__ import annotations

import pytest

from src.components import bomba, condensador, evaporador, recuperador, turbina
from src.components._estado import estado_Ph

M = 2.0      # kg/s, distinto de 1 para que un ṁ olvidado se note


def _liq(b, P):
    return estado_Ph(b, P, b.h(P, q=0.0), m=M, etiqueta="1")


def _vap(b, P):
    return estado_Ph(b, P, b.h(P, q=1.0), m=M, etiqueta="3")


def test_bomba(fluido):
    _, b = fluido
    P1, P2 = 0.05 * b.P_crit, 0.6 * b.P_crit
    e1 = _liq(b, P1)
    e2, r = bomba.resolver(e1, b, P_salida=P2, eta_p=0.75, m=M)
    assert e2.P == P2 and e2.m == M                                     # masa, presión
    assert r["Wp"] == pytest.approx(M * (e2.h - e1.h), rel=1e-12)      # energía
    assert (r["h2s"] - e1.h) / (e2.h - e1.h) == pytest.approx(0.75, rel=1e-12)
    assert b.s(P2, h=r["h2s"]) == pytest.approx(e1.s, abs=1e-8)        # h2s isentrópico
    assert e2.s > e1.s and r["Wp"] > 0.0                               # 2.ª ley, signo
    assert e2.s == pytest.approx(b.s(P2, h=e2.h), abs=1e-10)           # estado vs CoolProp
    ideal, _ = bomba.resolver(e1, b, P_salida=P2, eta_p=1.0, m=M)
    assert ideal.s == pytest.approx(e1.s, abs=1e-8)
    with pytest.raises(ValueError):
        bomba.resolver(e1, b, P_salida=0.5 * P1, eta_p=0.75, m=M)


def test_turbina(fluido):
    _, b = fluido
    P3, P4 = 0.6 * b.P_crit, 0.05 * b.P_crit
    e3 = _vap(b, P3)
    e4, r = turbina.resolver(e3, b, P_salida=P4, eta_t=0.85)
    assert e4.P == P4 and e4.m == M
    assert r["Wt"] == pytest.approx(M * (e3.h - e4.h), rel=1e-12)
    assert (e3.h - e4.h) / (e3.h - r["h4s"]) == pytest.approx(0.85, rel=1e-12)
    assert b.s(P4, h=r["h4s"]) == pytest.approx(e3.s, abs=1e-8)
    assert e4.s > e3.s and r["Wt"] > 0.0
    assert e4.T == pytest.approx(b.estado_Ph(P4, e4.h)["T"], abs=1e-9)


def test_evaporador(fluido):
    _, b = fluido
    P = 0.4 * b.P_crit
    e2 = estado_Ph(b, P, b.h(P, T=b.T_sat(P) - 40.0), m=M, etiqueta="2")
    T_f = b.T_sat(P) + 15.0
    e3, r = evaporador.resolver(e2, b, T_fuente=T_f, eps=0.85, m=M)
    assert e3.P == P                                                    # H3: ΔP = 0
    assert r["h3_max"] == pytest.approx(b.h(P, T=T_f), rel=1e-12)
    assert (e3.h - e2.h) / (r["h3_max"] - e2.h) == pytest.approx(0.85, rel=1e-12)
    assert r["Qin"] == pytest.approx(M * (e3.h - e2.h), rel=1e-12) and r["Qin"] > 0.0
    assert e3.T <= T_f                                                  # S5


def test_condensador(fluido):
    _, b = fluido
    T_sum = 300.0
    P_cd = b.P_sat(T_sum + 10.0)
    e4 = estado_Ph(b, P_cd, b.h(P_cd, T=T_sum + 40.0), m=M, etiqueta="4r")
    e1, r = condensador.resolver(e4, b, T_sumidero=T_sum, eps=0.95, m=M)
    assert e1.P == P_cd and e1.m == M                                   # H3, masa
    assert r["h1_min"] == pytest.approx(b.h(P_cd, T=T_sum), rel=1e-12)
    assert (e4.h - e1.h) / (e4.h - r["h1_min"]) == pytest.approx(0.95, rel=1e-12)
    assert r["Qout"] == pytest.approx(M * (e4.h - e1.h), rel=1e-12) and r["Qout"] > 0.0
    assert e1.T >= T_sum                                                # S6
    with pytest.raises(ValueError):
        condensador.resolver(e4, b, T_sumidero=T_sum, eps=1.2, m=M)


def test_recuperador(fluido):
    _, b = fluido
    P_cd, P_ev = 0.05 * b.P_crit, 0.6 * b.P_crit
    e4 = estado_Ph(b, P_cd, b.h(P_cd, T=b.T_sat(P_cd) + 40.0), m=M, etiqueta="4")
    e2 = estado_Ph(b, P_ev, b.h(P_ev, T=b.T_sat(P_cd) + 1.0), m=M, etiqueta="2")
    e4r, e2r, r = recuperador.resolver(e4, e2, b, eps=0.7)
    assert (e4r.P, e2r.P) == (P_cd, P_ev) and e4r.m == e2r.m == M
    assert M * (e4.h - e4r.h) == pytest.approx(M * (e2r.h - e2.h), rel=1e-12)   # energía
    assert r["Qrec"] == pytest.approx(M * (e4.h - e4r.h), rel=1e-12)
    q_max = min(e4.h - b.h(P_cd, T=e2.T), b.h(P_ev, T=e4.T) - e2.h)
    assert r["q_max"] == pytest.approx(q_max, rel=1e-12)
    assert (e4.h - e4r.h) / q_max == pytest.approx(0.7, rel=1e-12)
    assert (e4r.s - e4.s) + (e2r.s - e2.s) > 0.0                                  # Ṡ_gen > 0
    assert e4r.T > e2.T and e4.T > e2r.T                                           # sin cruce
    cero4, cero2, r0 = recuperador.resolver(e4, e2, b, eps=0.0)
    assert r0["Qrec"] == 0.0 and cero4.h == e4.h and cero2.h == e2.h


@pytest.mark.parametrize("eps", [0.9, 1.0])
def test_recuperador_con_subenfriamiento_no_cruza(fluido, eps):
    """Revisión D1: con T2 < T_sat(P_cd) la fórmula de un solo lado cruzaba temperaturas."""
    _, b = fluido
    P_cd, P_ev = 0.05 * b.P_crit, 0.6 * b.P_crit
    Ts = b.T_sat(P_cd)
    e4 = estado_Ph(b, P_cd, b.h(P_cd, T=Ts + 5.0), m=M, etiqueta="4")
    e2 = estado_Ph(b, P_ev, b.h(P_ev, T=Ts - 5.0), m=M, etiqueta="2")
    e4r, e2r, _ = recuperador.resolver(e4, e2, b, eps=eps)
    assert e2r.T <= e4.T + 1e-6 and e4r.T >= e2.T - 1e-6
    assert (e4r.s - e4.s) + (e2r.s - e2.s) >= -1e-12


def test_recuperador_sin_gradiente_falla(fluido):
    """Revisión D2: T4 ≤ T2 → el punto no existe con recuperador."""
    from src.errores import CicloSinSolucionError
    _, b = fluido
    P_cd, P_ev = 0.05 * b.P_crit, 0.6 * b.P_crit
    e4 = _liq(b, P_cd)
    e2 = estado_Ph(b, P_ev, b.h(P_ev, T=e4.T + 1.0), m=M, etiqueta="2")
    with pytest.raises(CicloSinSolucionError):
        recuperador.resolver(e4, e2, b, eps=0.5)
