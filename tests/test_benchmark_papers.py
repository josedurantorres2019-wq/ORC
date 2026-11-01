"""Benchmark contra los casos publicados (plan de verificación, nivel V1 y V3).

Corre cada punto del bloque `verificacion` de `01_referencias/casos/*.yaml` con el código y
exige que ninguna comparación quede en «falla» (pasa, o explicada con causa documentada).
Marcada `corrida`: solo con orden del usuario (`pytest -m corrida`).

VP-05 (Çengel 10-29, isobutano) queda como xfail estricto: Ẇ_net sale +0,67 % (tolerancia
0,5 %) y la causa probable, la EoS del isobutano en el EES del libro, falta confirmarla en EES.
Si un día pasa, la prueba avisa (strict) para quitar la marca.
"""

from __future__ import annotations

import pytest

from src import definiciones as d
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts._mapeo_papers import componentes
from scripts.comparar_verificacion import _corrida, _filas, _puntos

pytestmark = pytest.mark.corrida

PENDIENTES = {"VP-05": "Ẇ_net +0,67 %: causa probable la EoS de EES del libro; confirmar en EES"}
PUNTOS = list(_puntos())


@pytest.mark.parametrize("caso, punto", [
    pytest.param(c, p, id=p["id_punto"],
                 marks=pytest.mark.xfail(strict=True, reason=PENDIENTES[p["id_punto"]])
                 if p["id_punto"] in PENDIENTES else ())
    for c, p in PUNTOS])
def test_punto_publicado(caso, punto, defs):
    b = CoolPropAdapter(punto["fluido"])
    if punto.get("tipo") == "componentes":
        valores, nivel = componentes(punto, b), "V1"
    else:
        valores, _, _, _ = _corrida(caso, punto, b, defs, guardar=False)
        nivel = "V3"
    fallas = [f"{f['variable']}: {100 * (f['error_rel'] or 0):+.3f} %"
              for f in _filas(punto, valores, nivel, None) if f["veredicto"] == "falla"]
    assert not fallas, fallas


def test_hay_puntos_de_los_tres_fluidos_del_proyecto():
    fluidos = {p["fluido"] for _, p in PUNTOS}
    assert {d.nombre_coolprop(d.cargar(), f) for f in ("n-butano", "R1234yf", "MM")} <= fluidos
