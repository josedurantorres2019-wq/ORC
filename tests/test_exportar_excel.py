"""El Excel único acumula corridas y comparaciones (hoja `verificacion`, V-E).

El punto es sintético (no sale del solver): prueba solo la exportación.
"""

from __future__ import annotations

import pytest
from openpyxl import load_workbook

from src.exportar_excel import HOJAS, agregar_corrida, agregar_verificacion, filas_corrida
from src.restricciones import Clasificacion, Falla, ResultadoValidacion, Severidad
from src.state import EstadoTermo
from src.verificacion import comparar


def _punto():
    e = {k: EstadoTermo(T=300.0 + i, P=100.0, h=10.0 * i, s=1.0, v=0.01, q=0.0, fase="liquido",
                        etiqueta=k[1:], exergia_fisica=float(i))
         for i, k in enumerate(("e1", "e2", "e2r", "e3", "e4", "e4r"))}
    r = {"modo": "R", "estados": e, "Qin": 100.0, "Qout": 90.0, "Wt": 11.0, "Wp": 1.0,
         "Wnet": 10.0, "eta": 0.10}
    ex = {"estados": e, "T0": 300.0, "eta_II": 0.4, "Ed_total": 4.0,
          "Sgen": {"turbina": 0.01, "bomba": 0.0}, "Ed": {"turbina": 3.0, "bomba": 1.0}}
    falla = Falla("O1", Severidad.TECNOLOGICO, Clasificacion.CORREGIBLE, "x4 baja", "x4", 0.8,
                  ">= 0.90", "subir T3")
    val = ResultadoValidacion(Clasificacion.CORREGIBLE, [falla])
    meta = {"fluido": "n-butano", "fluido_coolprop": "n-Butane", "caso": "diseno",
            "version_definiciones": 1, "etiqueta": "prueba"}
    return filas_corrida(r, ex, val, meta=meta, entradas={"P_ev": 2000.0, "P_cd": 300.0})


def test_acumula_corridas_en_un_solo_excel(tmp_path):
    ruta = tmp_path / "resultados_orc.xlsx"
    assert agregar_corrida(_punto(), ruta) == 1
    assert agregar_corrida(_punto(), ruta) == 2

    wb = load_workbook(ruta)
    assert set(HOJAS) | {"diccionario"} == set(wb.sheetnames)
    corridas = list(wb["corridas"].values)
    cab = corridas[0]
    assert corridas[1][cab.index("Wnet")] == "kW"                  # fila 2: unidades
    assert [f[cab.index("id_corrida")] for f in corridas[2:]] == [1, 2]
    assert corridas[3][cab.index("falla_principal")] == "O1"
    assert corridas[3][cab.index("P_ev")] == 2000.0
    assert len(list(wb["estados"].values)) == 2 + 2 * 6
    assert len(list(wb["componentes"].values)) == 2 + 2 * 2
    assert len(list(wb["fallas"].values)) == 2 + 2


def _fila(valor_python, causa=None):
    return comparar(id_punto="VP-03", nivel="V3", herramienta="paper", referencia="Yari Tabla 6",
                    variable="Wnet", unidad="kW", valor_ref=1450.0, valor_python=valor_python,
                    tolerancia=0.005, tipo_tolerancia="rel", causa=causa, id_corrida=1)


def test_veredictos_de_la_regla_del_plan():
    assert _fila(1452.0)["veredicto"] == "pasa"                  # +0,14 %
    assert _fila(1400.0)["veredicto"] == "falla"                 # −3,4 % sin causa
    assert _fila(1400.0, causa="EoS de EES 2015")["veredicto"] == "explicado"
    with pytest.raises(ValueError):
        comparar(id_punto="x", nivel="V0", herramienta="EES", referencia="-", variable="h",
                 unidad="kJ/kg", valor_ref=0.0, valor_python=1.0, tolerancia=0.1,
                 tipo_tolerancia="rel")


def test_hoja_verificacion_se_agrega_y_acumula(tmp_path):
    ruta = tmp_path / "resultados_orc.xlsx"
    agregar_corrida(_punto(), ruta)
    wb = load_workbook(ruta)                          # simula un archivo viejo sin la hoja
    del wb["verificacion"]
    wb.save(ruta)

    assert agregar_verificacion([_fila(1452.0), _fila(1400.0)], ruta) == 2
    assert agregar_verificacion([_fila(1450.0)], ruta) == 1
    filas = list(load_workbook(ruta)["verificacion"].values)
    cab = filas[0]
    assert [f[cab.index("veredicto")] for f in filas[2:]] == ["pasa", "falla", "pasa"]
    assert list(load_workbook(ruta)["corridas"].values)[2][0] == 1   # la corrida sigue intacta
