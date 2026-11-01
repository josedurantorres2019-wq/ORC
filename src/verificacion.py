"""Comparación de un valor del código contra una referencia (plan de verificación, V-D y V-E).

`comparar` arma una fila de la hoja `verificacion` del Excel único: error absoluto y relativo,
y el veredicto con la regla del plan (§7):

    pasa       |error| ≤ tolerancia
    explicado  fuera de tolerancia, pero con una causa documentada (EoS, dato redondeado, ...)
    falla      fuera de tolerancia y sin causa: se para hasta encontrarla

Las tolerancias las da quien llama, tal como se aprobaron en V-D; aquí no hay ninguna fija.
Función pura: no toca el disco (eso lo hace `exportar_excel.agregar_verificacion`).
"""

from __future__ import annotations

from datetime import datetime

__all__ = ["comparar", "VEREDICTOS"]

VEREDICTOS = ("pasa", "explicado", "falla")


def comparar(*, id_punto: str, nivel: str, herramienta: str, referencia: str, variable: str,
             unidad: str, valor_ref: float, valor_python: float, tolerancia: float,
             tipo_tolerancia: str, causa: str | None = None,
             id_corrida: int | None = None) -> dict:
    """Fila de `verificacion`. ``tipo_tolerancia``: "abs" (en ``unidad``) o "rel" (fracción)."""
    if tipo_tolerancia not in ("abs", "rel"):
        raise ValueError(f"tipo_tolerancia debe ser 'abs' o 'rel', no {tipo_tolerancia!r}")
    if tolerancia < 0:
        raise ValueError(f"tolerancia negativa: {tolerancia}")
    error_abs = valor_python - valor_ref
    error_rel = error_abs / abs(valor_ref) if valor_ref != 0 else None
    if tipo_tolerancia == "rel" and error_rel is None:
        raise ValueError("tolerancia relativa con valor_ref = 0: usar tolerancia absoluta")
    error = abs(error_abs) if tipo_tolerancia == "abs" else abs(error_rel)
    if error <= tolerancia:
        veredicto = "pasa"
    else:
        veredicto = "explicado" if causa else "falla"
    return {"id_corrida": id_corrida, "id_punto": id_punto, "nivel": nivel,
            "herramienta": herramienta, "referencia": referencia, "variable": variable,
            "unidad": unidad, "valor_ref": valor_ref, "valor_python": valor_python,
            "error_abs": error_abs, "error_rel": error_rel, "tolerancia": tolerancia,
            "tipo_tolerancia": tipo_tolerancia, "veredicto": veredicto, "causa": causa,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
