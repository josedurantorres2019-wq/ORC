"""Lector de `02_modelo/definiciones.yaml`, la ÚNICA fuente de valores y criterios.

Nadie en `src/` escribe un valor físico a mano: el solver los recibe por palabra clave y
quien llama (pruebas, `scripts/`) los saca de aquí. Así un cambio en el YAML llega a todo
el código y queda en el historial de git (sin `_v2` ni `_final`).
"""

from __future__ import annotations

from pathlib import Path

import yaml

__all__ = ["RUTA", "cargar", "valor", "nombre_coolprop", "entradas_R", "criterios"]

RUTA = Path(__file__).resolve().parents[1] / "02_modelo" / "definiciones.yaml"


def cargar(ruta: Path | str = RUTA) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def valor(defs: dict, clave: str):
    """``valor(defs, "entradas_modo_R.eta_t")`` → 0.85. Si el nodo es {valor: ...}, lo abre."""
    nodo = defs
    for parte in clave.split("."):
        nodo = nodo[parte]
    return nodo["valor"] if isinstance(nodo, dict) and "valor" in nodo else nodo


def nombre_coolprop(defs: dict, fluido: str) -> str:
    """Clave del proyecto ("n-butano") → nombre CoolProp ("n-Butane")."""
    return defs["fluidos"][fluido]["coolprop"]


def entradas_R(defs: dict, *, caso: str = "diseno") -> dict:
    """Argumentos de `resolver_ciclo_R`, cierre B (D-16), salvo ``P_ev`` y ``P_cd``.

    P_ev y P_cd son las variables de decisión (como P_alta y P_baja del Kalina). Si
    ``eps_cond`` es null en el YAML, quien llama debe darlo: no se inventa.
    """
    return {
        "T_fuente": valor(defs, f"casos.{caso}.T_fuente"),
        "T_sumidero": valor(defs, f"casos.{caso}.T_sumidero"),
        "eps_cond": valor(defs, "entradas_modo_R.eps_cond"),
        "dT_cd": None,
        "dT_sc": None,
        "eta_t": valor(defs, "entradas_modo_R.eta_t"),
        "eta_p": valor(defs, "entradas_modo_R.eta_p"),
        "eps_ev": valor(defs, "entradas_modo_R.eps_ev"),
        "m": valor(defs, "entradas_modo_R.m"),
        "eps_rec": valor(defs, "entradas_modo_R.eps_rec"),
    }


def criterios(defs: dict, *, fluido: str) -> dict:
    """Umbrales y tolerancias de `restricciones.evaluar_ciclo` para ``fluido`` (clave del proyecto)."""
    return {
        "tol_N2": valor(defs, "tolerancias.balance_energia_rel"),
        "tol_exergia": valor(defs, "tolerancias.cierre_exergia_rel"),
        "x4_min": valor(defs, "umbrales.x4_min"),
        "x3_min": valor(defs, "umbrales.x3_min"),
        "T_amb_max": valor(defs, "umbrales.cavitacion_O2.T_amb_max"),   # None = sumidero
        "f_Pcrit": valor(defs, "umbrales.f_Pcrit"),
        "T3_max": valor(defs, "umbrales.T3_max_MM") if fluido == "MM"
        else valor(defs, "umbrales.T3_max_otros"),
        "dT_pp_ev": valor(defs, "umbrales.dT_pp_ev"),
        "dT_pp_cd": valor(defs, "umbrales.dT_pp_cd"),
    }
