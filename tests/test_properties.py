"""El adapter devuelve lo mismo que CoolProp PropsSI, con las unidades convertidas bien."""

from __future__ import annotations

import CoolProp.CoolProp as CP
import pytest

from src.properties.adapter import PropertyRangeError
from src.properties.coolprop_adapter import CoolPropAdapter


def _punto(b):
    """Un estado subcrítico líquido y uno de vapor de prueba, en función de P_crit/T_crit."""
    P = 0.3 * b.P_crit
    return P, b.T_sat(P)


def test_saturacion_contra_propssi(fluido):
    _, b = fluido
    P, Ts = _punto(b)
    assert Ts == pytest.approx(CP.PropsSI("T", "P", P * 1e3, "Q", 0, b.fluido), rel=1e-10)
    assert b.P_sat(Ts) == pytest.approx(P, rel=1e-8)
    for q in (0.0, 1.0):
        assert b.h(P, q=q) == pytest.approx(CP.PropsSI("H", "P", P * 1e3, "Q", q, b.fluido) / 1e3,
                                            rel=1e-10)
        assert b.s(P, q=q) == pytest.approx(CP.PropsSI("S", "P", P * 1e3, "Q", q, b.fluido) / 1e3,
                                            rel=1e-10)


def test_monofasico_y_flash_Ph(fluido):
    _, b = fluido
    P, Ts = _punto(b)
    for T, fase, q in ((Ts - 20.0, "liquido", 0.0), (Ts + 20.0, "vapor", 1.0)):
        h = b.h(P, T=T)
        assert h == pytest.approx(CP.PropsSI("H", "P", P * 1e3, "T", T, b.fluido) / 1e3, rel=1e-10)
        p = b.estado_Ph(P, h)
        assert p["T"] == pytest.approx(T, abs=1e-6)
        assert p["s"] == pytest.approx(b.s(P, T=T), rel=1e-9)
        assert p["v"] == pytest.approx(1.0 / CP.PropsSI("D", "P", P * 1e3, "T", T, b.fluido),
                                       rel=1e-9)
        assert (p["fase"], p["q"]) == (fase, q)


def test_bifasico_titulo(fluido):
    _, b = fluido
    P, _ = _punto(b)
    h = b.h(P, q=0.4)
    p = b.estado_Ph(P, h)
    assert p["fase"] == "bifasico" and p["q"] == pytest.approx(0.4, abs=1e-9)


def test_isentropico_inverso(fluido):
    _, b = fluido
    P, Ts = _punto(b)
    s = b.s(P, T=Ts + 30.0)
    h = b.h(0.5 * P, s=s)
    assert b.s(0.5 * P, h=h) == pytest.approx(s, abs=1e-9)


def test_errores_envueltos(fluido):
    _, b = fluido
    with pytest.raises(PropertyRangeError):
        b.T_sat(1.1 * b.P_crit)
    with pytest.raises(PropertyRangeError):
        b.h(-5.0, T=300.0)
    with pytest.raises(ValueError):
        b.h(100.0, T=300.0, q=0.0)
    with pytest.raises(PropertyRangeError):
        CoolPropAdapter("NoEsUnFluido")
