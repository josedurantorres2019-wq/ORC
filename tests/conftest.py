"""Fixtures comunes. Los backends son reales (CoolProp): las pruebas validan contra el motor."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import definiciones as d                         # noqa: E402
from src.properties.coolprop_adapter import CoolPropAdapter  # noqa: E402

FLUIDOS_ESTUDIO = ("n-butano", "R1234yf", "MM")


@pytest.fixture(scope="session")
def defs():
    return d.cargar()


@pytest.fixture(scope="session")
def agua():
    return CoolPropAdapter("Water")


@pytest.fixture(scope="session", params=FLUIDOS_ESTUDIO)
def fluido(request, defs):
    """(clave del proyecto, backend) para cada fluido de D-05."""
    return request.param, CoolPropAdapter(d.nombre_coolprop(defs, request.param))
