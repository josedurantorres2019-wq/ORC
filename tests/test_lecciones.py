"""Lecciones del Kalina convertidas en pruebas (convenciones del proyecto ORC).

Cada prueba dice qué lección protege. Si una falla, la lección se está repitiendo.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from src import cycle_solver, definiciones as d
from src.components import condensador
from src.components._estado import estado_Ph

SRC = Path(__file__).resolve().parents[1] / "src"
ARCHIVOS = sorted(SRC.rglob("*.py"))


@pytest.mark.parametrize("ruta", ARCHIVOS, ids=lambda p: str(p.relative_to(SRC)))
def test_archivos_de_200_lineas_como_maximo(ruta):
    """Lección: módulos cortos; el Kalina acabó con archivos imposibles de revisar."""
    assert len(ruta.read_text(encoding="utf-8").splitlines()) <= 200


def test_solo_el_adapter_importa_coolprop():
    """Lección: el motor se inyecta; así el Kalina cambió de motor sin tocar la física."""
    culpables = [p.name for p in ARCHIVOS if p.name != "coolprop_adapter.py"
                 and re.search(r"^\s*(import|from)\s+CoolProp", p.read_text(encoding="utf-8"), re.M)]
    assert culpables == []


def test_src_no_llama_a_scripts_ni_tiene_sufijos_de_version():
    """Lección: `scripts/` → `src/` y nunca al revés; versiones con tags de git, no `_v2`."""
    for p in ARCHIVOS:
        texto = p.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+scripts", texto, re.M), p.name
        assert not re.search(r"_(v\d+|final|nuevo|viejo)\.py$", p.name), p.name


def test_sin_valores_fisicos_por_defecto():
    """Lección: ninguna cifra escrita a mano; los valores vienen de definiciones.yaml."""
    numericos = {"tol_h", "max_iter"}
    con_defecto = {n for n, p in inspect.signature(cycle_solver.resolver_ciclo_R).parameters.items()
                   if p.default is not inspect.Parameter.empty}
    assert con_defecto <= numericos


def test_definiciones_alimentan_al_solver(defs):
    """Las claves que el código lee existen en el YAML para todos los fluidos de D-05."""
    entradas = d.entradas_R(defs)
    assert set(entradas) | {"P_ev", "P_cd"} == set(inspect.signature(cycle_solver.resolver_ciclo_R)
                                           .parameters) - {"backend", "tol_h", "max_iter"}
    for fluido in defs["fluidos"]:
        crit = d.criterios(defs, fluido=fluido)
        assert all(k in crit for k in ("x4_min", "x3_min", "T_amb_max", "f_Pcrit"))
    assert d.criterios(defs, fluido="MM")["T3_max"] == d.valor(defs, "umbrales.T3_max_MM")


def test_eps_cond_baja_deja_bifasico(fluido, defs):
    """Lección §2.6: con ε_cond = 0,80 (Kalina) un fluido puro llega bifásico a la bomba.

    Con el cierre B (D-16) el componente NO lo esconde: devuelve el estado bifásico para que
    O2 lo marque. Se comprueba con un 4r de vapor saturado (estado genérico, no del estudio).
    """
    _, b = fluido
    T_sum = d.valor(defs, "casos.diseno.T_sumidero")
    P_cd = b.P_sat(T_sum + d.valor(defs, "umbrales.dT_cd"))
    e4r = estado_Ph(b, P_cd, b.h(P_cd, q=1.0), m=1.0, etiqueta="4r")
    e1, _ = condensador.resolver(e4r, b, T_sumidero=T_sum, eps=0.80, m=1.0)
    assert e1.fase == "bifasico"
    e1_lim, _ = condensador.resolver(e4r, b, T_sumidero=T_sum, eps=1.0, m=1.0)
    assert e1_lim.fase == "liquido" and e1_lim.T == pytest.approx(T_sum, abs=1e-6)
