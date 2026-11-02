"""Lecciones de la primera corrida en EES (2026-11-01), sin abrir EES."""

import csv
import re

from scripts.correr_ees import ENTRADAS, PLANTILLA, programa


def _nombres(texto: str) -> set[str]:
    sin_comentarios = re.sub(r"\{.*?\}", "", texto, flags=re.S)
    return set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", sin_comentarios))


def test_plantilla_sin_variables_que_solo_difieren_en_mayusculas():
    """EES no distingue mayúsculas: Q_rec y q_rec eran la misma variable y el sistema no cerraba."""
    vistos: dict[str, set[str]] = {}
    for n in _nombres(PLANTILLA.read_text(encoding="utf-8")):
        vistos.setdefault(n.lower(), set()).add(n)
    assert {k: v for k, v in vistos.items() if len(v) > 1} == {}


def test_programa_generado_tiene_el_procedure_entero_antes_de_las_ecuaciones(tmp_path):
    """El encabezado nombra «PROCEDURE lazo»: cortar por ese texto partía el comentario."""
    fila = next(csv.DictReader(ENTRADAS.open(encoding="utf-8")))
    p = programa(fila, tmp_path / "salida.csv")
    assert p.count("PROCEDURE lazo(") == 1
    assert p.index("PROCEDURE lazo(") < p.index("END") < p.index("$UnitSystem") < p.index("CALL lazo(")
    assert p.count("{") == p.count("}")
