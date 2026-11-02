"""Flujo «sin recuperador → ¿puede funcionar? → con recuperador», probado con AGUA.

El agua no es fluido del estudio: se prueba la lógica del script, no se evalúa ningún caso.
Los números son entradas de prueba (las mismas de `test_cierre_B.py`).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from scripts import comparar_recuperador as cr
from src.cycle_solver import resolver_ciclo_R

T_SUM = 300.0
ENTRADAS = dict(T_fuente=800.0, T_sumidero=T_SUM, eps_cond=0.95, eta_t=0.85, eta_p=0.75,
                eps_ev=0.95, m=1.0, eps_rec=None)
P = dict(P_ev=1000.0, P_cd=75.0)
CRIT = {"tol_N2": 1e-3, "tol_exergia": 1e-3, "x4_min": 0.0, "x3_min": 1.0, "f_Pcrit": 1.0,
        "T3_max": None, "T_amb_max": None}


def _comparar(agua, eps_rec=0.5):
    return cr.comparar(agua, ENTRADAS, eps_rec=eps_rec, criterios=CRIT, T0=T_SUM, P0=101.325, **P)


def test_puede_funcionar_es_T4_mayor_que_T2():
    caliente = SimpleNamespace(estados={"e4": SimpleNamespace(T=400.0), "e2": SimpleNamespace(T=310.0)})
    frio = SimpleNamespace(estados={"e4": SimpleNamespace(T=300.0), "e2": SimpleNamespace(T=310.0)})
    assert cr.recuperador_puede_funcionar({"estados": caliente.estados}) == (True, 90.0)
    ok, dT = cr.recuperador_puede_funcionar({"estados": frio.estados})
    assert ok is False and dT == -10.0


def test_la_corrida_principal_es_sin_recuperador(agua):
    c = _comparar(agua)
    r_directa = resolver_ciclo_R(agua, **P, **ENTRADAS)
    r = c["sin"][0]
    assert r["Qrec"] == 0.0 and r["Wnet"] == r_directa["Wnet"] and r["eta"] == r_directa["eta"]


def test_con_recuperador_cambia_lo_esperado(agua):
    c = _comparar(agua, 0.5)
    assert c["puede"] and c["dT_4_2"] > 0 and c["motivo"] is None
    (r_sin, _, _), (r_con, ex_con, _), dl = c["sin"], c["con"], c["delta"]
    assert r_con["Qrec"] > 0.0 and dl["Qrec"] == pytest.approx(r_con["Qrec"])
    assert r_con["Qin"] < r_sin["Qin"]                       # el recuperador aporta calor al líquido
    assert r_con["N2"] < 1e-9 and ex_con["cierre_exergia"] < 1e-9
    assert dl["mejora_eta"] == (r_con["eta"] > r_sin["eta"])
    assert "VEREDICTO" in cr.reporte(c, 0.5)


def test_si_T4_no_supera_T2_no_se_corre_con_recuperador(agua, monkeypatch):
    monkeypatch.setattr(cr, "recuperador_puede_funcionar", lambda r: (False, -3.0))
    c = _comparar(agua)
    assert c["puede"] is False and c["con"] is None and c["delta"] is None
    assert "≤ 0" in c["motivo"] and c["sin"][0]["Qrec"] == 0.0
    assert "no evaluado" in cr.reporte(c, 0.5)


def test_si_el_ciclo_con_recuperador_no_existe_se_reporta(agua, monkeypatch):
    original = cr.resolver_punto

    def falla_con(backend, entradas, **kw):
        if entradas["eps_rec"] is not None:
            raise cr.CicloSinSolucionError("T4 <= T2 dentro del lazo")
        return original(backend, entradas, **kw)

    monkeypatch.setattr(cr, "resolver_punto", falla_con)
    c = _comparar(agua)
    assert c["puede"] is False and c["con"] is None and "no se resuelve" in c["motivo"]


def test_eps_rec_obligatoria_y_en_rango(agua):
    with pytest.raises(ValueError):
        _comparar(agua, None)
    with pytest.raises(ValueError):
        _comparar(agua, 1.5)


def test_las_dos_corridas_se_guardan_por_separado(agua, tmp_path):
    ruta = tmp_path / "resultados_orc.xlsx"
    c = _comparar(agua, 0.5)
    meta = {"fluido": "agua", "fluido_coolprop": "Water", "caso": "prueba",
            "version_definiciones": 0, "etiqueta": "estudio"}
    ids = cr.guardar_par(c, meta=meta, entradas=ENTRADAS, eps_rec=0.5, ruta=ruta, **P)
    assert ids["sin"] != ids["con"] and {ids["sin"], ids["con"]} == {1, 2}
    ws = load_workbook(ruta)["corridas"]
    cab = [x.value for x in ws[1]]
    filas = {f[cab.index("id_corrida")]: f for f in ([x.value for x in row] for row in ws.iter_rows(min_row=3))}
    assert filas[ids["sin"]][cab.index("eps_rec")] is None
    assert filas[ids["con"]][cab.index("eps_rec")] == 0.5
    assert filas[ids["sin"]][cab.index("etiqueta")] == "estudio | sin_rec"
    assert filas[ids["con"]][cab.index("etiqueta")] == "estudio | con_rec"


def test_si_no_puede_solo_se_guarda_la_principal(agua, tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "recuperador_puede_funcionar", lambda r: (False, -1.0))
    c = _comparar(agua)
    ids = cr.guardar_par(c, meta={"etiqueta": None}, entradas=ENTRADAS, eps_rec=0.5,
                         ruta=tmp_path / "x.xlsx", **P)
    assert ids == {"sin": 1, "con": None}
