"""Estados punto por punto contra Çengel (ampliación v1.0.0, familia F3).

Çengel Ej. 10-1 (p. 564) y Ej. 10-3 a/b/c (pp. 571-572) publican h, s y x de cada estado del
ciclo ideal de agua. Las tablas del libro (IAPWS-95) y CoolProp usan el mismo estado de
referencia en agua, así que se comparan h absolutas. Los ciclos se arman con los mismos puntos
de verificación (VP-01, VP-16a/b/c) y su mapeo a modo R, sin tocar el código.

Tolerancias fijadas antes de correr (2026-11-02): h ±0,5 kJ/kg, s ±0,002 kJ/kg·K y x4 ±0,002
(las tablas redondean a 0,01–0,1 kJ/kg y a 4 decimales en s y x). El libro calcula la bomba con
v·ΔP (Ec. 10-3); el código, con h(P2, s1). Esa diferencia es de centésimas de kJ/kg.
"""

from __future__ import annotations

import pytest

from src.cycle_solver import resolver_ciclo_R
from src.properties.coolprop_adapter import CoolPropAdapter

from scripts._mapeo_papers import entradas_modo_R
from scripts.comparar_verificacion import _puntos

PUNTOS = {p["id_punto"]: p for _, p in _puntos()}

# id_punto → (h1, h2, h3, s3, x4, h4), tal como los imprime el libro
LIBRO = {
    "VP-01": (384.44, 387.47, 3116.1, 6.7450, 0.8861, 2403.0),    # Ej. 10-1, p. 564
    "VP-16a": (191.81, 194.83, 3116.1, 6.7450, 0.8128, 2136.1),   # Ej. 10-3a, p. 571
    "VP-16b": (191.81, 194.83, 3682.8, None, 0.915, 2380.3),      # Ej. 10-3b, p. 571
    "VP-16c": (191.81, 206.95, 3583.1, None, 0.804, 2115.3),      # Ej. 10-3c, p. 572
}


@pytest.mark.parametrize("pid", list(LIBRO))
def test_estados_como_el_libro(pid):
    b = CoolPropAdapter("Water")
    r = resolver_ciclo_R(b, **entradas_modo_R(PUNTOS[pid], b))
    e = r["estados"]
    h1, h2, h3, s3, x4, h4 = LIBRO[pid]
    assert e["e1"].h == pytest.approx(h1, abs=0.5)
    assert e["e2"].h == pytest.approx(h2, abs=0.5)
    assert e["e3"].h == pytest.approx(h3, abs=0.5)
    assert e["e4"].h == pytest.approx(h4, abs=0.5)
    assert e["e4"].q == pytest.approx(x4, abs=0.002)
    if s3 is not None:
        assert e["e3"].s == pytest.approx(s3, abs=0.002)
