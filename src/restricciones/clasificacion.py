"""Orquestador: `evaluar_ciclo` corre todos los criterios sobre un punto ya resuelto.

Recibe los criterios ya leídos de `definiciones.yaml` (`definiciones.criterios`). No lanza:
un punto que no convergió no llega aquí (N1, lo marca quien llama al solver).
"""

from __future__ import annotations

from .modelos import ORDEN, Clasificacion, ResultadoValidacion
from .numericos import verificar_numericos
from .operativos import verificar_operativos
from .segunda_ley import verificar_segunda_ley

__all__ = ["evaluar_ciclo", "NO_APLICA"]

NO_APLICA = ("S3", "N3", "C1", "C2", "C3")   # sin válvula; fluido puro sin balance de especie


def evaluar_ciclo(resultado: dict, exergia: dict | None, backend, *, criterios: dict,
                  eps: dict) -> ResultadoValidacion:
    """``backend``: lo usa O2 para re-resolver el condensador en el peor ambiente."""
    fallas = verificar_numericos(resultado, exergia, tol_N2=criterios["tol_N2"],
                                 tol_exergia=criterios["tol_exergia"])
    fallas += verificar_segunda_ley(resultado, eps=eps,
                                    sgen=None if exergia is None else exergia["Sgen"])
    fallas += verificar_operativos(
        resultado, backend, **{k: criterios[k] for k in ("x4_min", "x3_min", "T_amb_max", "f_Pcrit",
                                                "T3_max")})
    clase = (min((f.clasificacion for f in fallas), key=ORDEN.__getitem__)
             if fallas else Clasificacion.ADMISIBLE)
    return ResultadoValidacion(clasificacion=clase, fallas=fallas, no_aplica=NO_APLICA)
