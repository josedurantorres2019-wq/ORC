"""Pruebas metamórficas sobre los puntos de los papers (ampliación v1.0.0, familia F4).

Cada punto de verificación ya contrastado con su paper sirve de semilla. Se le aplica un cambio
cuyo efecto el modelo DEBE cumplir y se comprueba ese efecto. No hacen falta datos nuevos y no se
toca el código. El estado muerto de la exergía es el T_sumidero de cada punto (no el del Kalina).
"""

from __future__ import annotations

import pytest

from src.cycle_solver import resolver_ciclo_R
from src.exergy import calcular_exergia
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts._mapeo_papers import entradas_modo_R
from scripts.comparar_verificacion import _puntos

SEMILLAS = [p for _, p in _puntos() if p.get("tipo") != "componentes"]
IDS = [p["id_punto"] for p in SEMILLAS]


def _ciclo(punto, **cambios):
    b = CoolPropAdapter(punto["fluido"])
    ent = {**entradas_modo_R(punto, b), **cambios}
    return b, ent, resolver_ciclo_R(b, **ent)


@pytest.mark.parametrize("punto", SEMILLAS, ids=IDS)
def test_escala_con_el_caudal(punto):
    """ṁ × 2 duplica potencias y calores; η, T y títulos no cambian."""
    b, ent, r = _ciclo(punto)
    _, _, r2 = _ciclo(punto, m=2 * ent["m"])
    for k in ("Wnet", "Wt", "Wp", "Qin", "Qout", "Qrec"):
        assert r2[k] == pytest.approx(2 * r[k], rel=1e-9, abs=1e-9)
    assert r2["eta"] == pytest.approx(r["eta"], rel=1e-12)
    for e in ("e1", "e2", "e3", "e4"):
        assert r2["estados"][e].T == pytest.approx(r["estados"][e].T, abs=1e-9)


@pytest.mark.parametrize("punto", SEMILLAS, ids=IDS)
def test_mejor_turbina_mas_potencia(punto):
    """η_t mayor → más Ẇ_net y salida de turbina más fría (con el resto de las entradas fijas)."""
    b, ent, r = _ciclo(punto)
    if ent["eta_t"] >= 1.0:
        pytest.skip("turbina ideal en el paper")
    _, _, r2 = _ciclo(punto, eta_t=min(1.0, ent["eta_t"] + 0.05))
    assert r2["Wnet"] > r["Wnet"]
    assert r2["estados"]["e4"].h < r["estados"]["e4"].h


@pytest.mark.parametrize("punto", SEMILLAS, ids=IDS)
def test_recuperador_en_cero_es_no_tenerlo(punto):
    """ε_rec = 0 da el mismo ciclo que «sin recuperador».

    Hallazgo H-1 (2026-11-02), corregido en la v1.0.1: antes, si T4 ≤ T2, `recuperador.resolver`
    rechazaba ε_rec = 0 con CicloSinSolucionError aunque no hubiera calor que transferir.
    """
    _, ent, r = _ciclo(punto)
    if ent["eps_rec"] is not None:
        pytest.skip("el punto tiene recuperador")
    _, _, r0 = _ciclo(punto, eps_rec=0.0)
    assert r0["Wnet"] == pytest.approx(r["Wnet"], rel=1e-9)
    assert r0["Qrec"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("punto", SEMILLAS, ids=IDS)
def test_maquinas_ideales_no_generan_entropia(punto):
    """η_t = η_p = 1 → S_gen de la turbina y de la bomba nulas."""
    b, ent, _ = _ciclo(punto)
    _, _, r = _ciclo(punto, eta_t=1.0, eta_p=1.0)
    ex = calcular_exergia(r, b, T0=ent["T_sumidero"], P0=101.325)
    assert ex["Sgen"]["turbina"] == pytest.approx(0.0, abs=1e-6 * ent["m"])
    assert ex["Sgen"]["bomba"] == pytest.approx(0.0, abs=1e-6 * ent["m"])


@pytest.mark.parametrize("punto", SEMILLAS, ids=IDS)
def test_cierres_de_energia_y_exergia(punto):
    """Primera ley (N2) y balance de exergía cierran en todos los puntos de los papers."""
    b, ent, r = _ciclo(punto)
    ex = calcular_exergia(r, b, T0=ent["T_sumidero"], P0=101.325)
    assert r["N2"] < 1e-8
    assert abs(ex["cierre_exergia"]) < 1e-6
    assert all(v >= -1e-6 * ent["m"] for v in ex["Sgen"].values())   # ruido numérico (VP-15: −3e-8)
