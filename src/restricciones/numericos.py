"""Criterios numéricos: N2 (balance de energía) y N2x (cierre exergético). D-01, P1.

N1 es la ausencia de `CicloNoConvergeError`: lo sabe quien llama al solver, no este módulo.
Tolerancias de `definiciones.yaml` (`tolerancias`), fijadas antes de correr.
"""

from __future__ import annotations

from .modelos import Clasificacion, Falla, Severidad

__all__ = ["verificar_numericos"]


def verificar_numericos(resultado: dict, exergia: dict | None, *, tol_N2: float,
                        tol_exergia: float) -> list[Falla]:
    fallas = []
    if resultado["N2"] > tol_N2:
        fallas.append(Falla(
            "N2", Severidad.NUMERICO, Clasificacion.NO_CONVERGIO,
            "el balance global de energía no cierra", "|Qin − Qout − Wnet|/Qin",
            resultado["N2"], f"<= {tol_N2}",
            "revisar la tolerancia del lazo o el balance de algún componente"))
    if exergia is not None and exergia["cierre_exergia"] > tol_exergia:
        fallas.append(Falla(
            "N2x", Severidad.NUMERICO, Clasificacion.NO_CONVERGIO,
            "el balance de exergía no cierra con ΣĖ_d", "cierre relativo",
            exergia["cierre_exergia"], f"<= {tol_exergia}",
            "revisar las fórmulas de Ṡ_gen o el estado muerto"))
    return fallas
