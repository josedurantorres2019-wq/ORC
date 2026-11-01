"""Exportación al Excel ÚNICO del proyecto: `datos/resultados_orc.xlsx`.

Cada punto resuelto se AGREGA como una corrida nueva (nunca se sobrescribe ni se crea otro
Excel: la lección de los 11 Excel del Kalina). Hojas, todas unidas por `id_corrida`:

    corridas     una fila por punto: metadatos, entradas, salidas globales, exergía, clase
    estados      una fila por estado (1, 2, 2r, 3, 4, 4r) de cada corrida
    componentes  Ṡ_gen y Ė_d por componente de cada corrida
    fallas       una fila por falla de las restricciones (vacía si el punto es ADMISIBLE)
    verificacion una fila por comparación contra EES, DWSIM o un paper (V-E; filas de
                 `src/verificacion.py`, con `id_corrida` de la corrida de Python comparada)
    diccionario  qué es y en qué unidad está cada columna (se escribe al crear el archivo)

Se guardan los datos crudos; la clasificación va en columnas aparte (no filtra filas).
`filas_corrida` es pura (arma las filas); `agregar_corrida` y `agregar_verificacion` son las
únicas que tocan el disco.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

__all__ = ["RUTA", "HOJAS", "filas_corrida", "agregar_corrida", "agregar_verificacion"]

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "datos" / "resultados_orc.xlsx"

# (columna, unidad, descripción). El orden aquí es el orden de las columnas en el Excel.
_META = [("id_corrida", "-", "número correlativo de la corrida"),
         ("fecha", "-", "fecha y hora de la exportación"),
         ("commit", "-", "commit de git del código (+ si había cambios sin commit)"),
         ("version_definiciones", "-", "campo `version` de definiciones.yaml"),
         ("etiqueta", "-", "nombre libre de la corrida o del estudio"),
         ("fluido", "-", "clave del proyecto"), ("fluido_coolprop", "-", "nombre en CoolProp"),
         ("caso", "-", "clave de `casos` en definiciones.yaml"), ("modo", "-", "modo del solver")]
_ENTRADAS = [("T_fuente", "K", "temperatura del reservorio caliente"),
             ("T_sumidero", "K", "temperatura del reservorio frío"),
             ("P_ev", "kPa", "presión del evaporador"), ("P_cd", "kPa", "presión del condensador"),
             ("eps_ev", "-", "efectividad del evaporador"),
             ("eps_cond", "-", "efectividad del condensador"),
             ("eps_rec", "-", "efectividad del recuperador (vacío = apagado)"),
             ("eta_t", "-", "rendimiento isentrópico de la turbina"),
             ("eta_p", "-", "rendimiento isentrópico de la bomba"), ("m", "kg/s", "caudal de fluido")]
_GLOBALES = [("Qin", "kW", "calor absorbido en el evaporador"),
             ("Qout", "kW", "calor cedido en el condensador"), ("Wt", "kW", "potencia de la turbina"),
             ("Wp", "kW", "potencia de la bomba"), ("Wnet", "kW", "Ẇ_t − Ẇ_p"),
             ("Qrec", "kW", "calor del recuperador"), ("eta", "-", "rendimiento térmico η_I"),
             ("eta_carnot", "-", "1 − T_sumidero/T_fuente"), ("eta_sobre_carnot", "-", "η_I/η_Carnot"),
             ("w_net", "kJ/kg", "trabajo neto específico"), ("r_p", "-", "P_ev/P_cd"),
             ("P_ev_sobre_Pcrit", "-", "P_ev/P_crit"), ("dh_s", "kJ/kg", "salto isentrópico h3 − h4s"),
             ("VR", "-", "v4/v3"), ("r_bw", "-", "Ẇ_p/Ẇ_t"),
             ("dT_sh3", "K", "sobrecalentamiento a la entrada de la turbina"),
             ("T_sat_cd", "K", "T de saturación a P_cd"),
             ("N2", "-", "residuo relativo del balance de energía"),
             ("iteraciones", "-", "iteraciones del lazo en h1"), ("residuo_h1", "kJ/kg", "residuo del lazo en h1")]
_EXERGIA = [("T0", "K", "T del estado muerto"), ("P0", "kPa", "P del estado muerto"),
            ("Ex_Qin", "kW", "exergía del calor absorbido"), ("Ex_Qout", "kW", "exergía del calor cedido"),
            ("eta_II", "-", "Ẇ_net/Ė_Qin"), ("Ed_total", "kW", "Σ Ė_d"),
            ("cierre_exergia", "-", "residuo relativo del balance de exergía")]
_CLASE = [("clasificacion", "-", "ADMISIBLE / CORREGIBLE / INVIABLE / NO_CONVERGIO"),
          ("falla_principal", "-", "código de la falla más severa"),
          ("codigos_fallas", "-", "todos los códigos, separados por coma")]
_ESTADO = [("id_corrida", "-", "corrida a la que pertenece"), ("estado", "-", "1, 2, 2r, 3, 4, 4r"),
           ("T", "K", ""), ("P", "kPa", ""), ("h", "kJ/kg", ""), ("s", "kJ/(kg·K)", ""),
           ("v", "m³/kg", ""), ("q", "-", "título (vacío fuera de la campana)"), ("fase", "-", ""),
           ("exergia_fisica", "kJ/kg", "(h − h0) − T0 (s − s0)")]
_COMPONENTE = [("id_corrida", "-", ""), ("componente", "-", ""), ("Sgen", "kW/K", "entropía generada"),
               ("Ed", "kW", "exergía destruida T0·Ṡ_gen"), ("Ed_sobre_total", "-", "Ė_d/ΣĖ_d")]
_FALLA = [("id_corrida", "-", ""), ("codigo", "-", ""), ("severidad", "-", ""), ("clasificacion", "-", ""),
          ("variable", "-", ""), ("valor_medido", "-", ""), ("valor_esperado", "-", ""),
          ("mensaje", "-", ""), ("sugerencia", "-", "")]
_VERIFICACION = [("id_corrida", "-", "corrida de Python comparada (vacío si no aplica)"),
                 ("id_punto", "-", "VP-01…VP-13 del plan de verificación"),
                 ("nivel", "-", "V0…V5"), ("herramienta", "-", "EES, DWSIM-CoolProp, DWSIM-PR o paper"),
                 ("referencia", "-", "tabla y página, o archivo del CSV"), ("variable", "-", ""),
                 ("unidad", "-", ""), ("valor_ref", "-", "valor de la referencia"),
                 ("valor_python", "-", "valor del código"), ("error_abs", "-", "python − ref"),
                 ("error_rel", "-", "(python − ref)/|ref|"), ("tolerancia", "-", "aprobada en V-D"),
                 ("tipo_tolerancia", "-", "abs o rel"), ("veredicto", "-", "pasa / explicado / falla"),
                 ("causa", "-", "explicación documentada si no pasa"), ("fecha", "-", "")]

_CORRIDA = _META + _ENTRADAS + _GLOBALES + _EXERGIA + _CLASE
HOJAS = {"corridas": _CORRIDA, "estados": _ESTADO, "componentes": _COMPONENTE, "fallas": _FALLA,
         "verificacion": _VERIFICACION}


def _commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                             text=True, check=True).stdout.strip()
        sucio = subprocess.run(["git", "status", "--porcelain", "--", "src", "02_modelo"], cwd=RAIZ,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("+" if sucio else "")
    except (OSError, subprocess.CalledProcessError):
        return "sin_git"


def filas_corrida(resultado: dict, exergia: dict | None, validacion, *, meta: dict,
                  entradas: dict) -> dict[str, list[dict]]:
    """Filas de cada hoja para UN punto (sin `id_corrida`: lo pone `agregar_corrida`).

    ``meta``: fluido, fluido_coolprop, caso, version_definiciones y etiqueta (opcional).
    ``entradas``: los argumentos que recibió `resolver_ciclo_R` (incluidas P_ev y P_cd).
    """
    ex = exergia or {}
    fila = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "commit": _commit(),
            "modo": resultado.get("modo"), **meta}
    fila.update({k: entradas.get(k) for k, _, _ in _ENTRADAS})
    fila.update({k: resultado.get(k) for k, _, _ in _GLOBALES})
    fila.update({k: ex.get(k) for k, _, _ in _EXERGIA})
    fallas = list(validacion.fallas) if validacion is not None else []
    fila["clasificacion"] = validacion.clasificacion.value if validacion is not None else None
    fila["falla_principal"] = validacion.principal.codigo if fallas else None
    fila["codigos_fallas"] = ", ".join(f.codigo for f in fallas) or None

    estados = ex.get("estados", resultado["estados"])
    f_estados = [{"estado": e.etiqueta, "T": e.T, "P": e.P, "h": e.h, "s": e.s, "v": e.v, "q": e.q,
                  "fase": e.fase, "exergia_fisica": e.exergia_fisica} for e in estados.values()]
    Ed_total = ex.get("Ed_total")
    f_comp = [{"componente": k, "Sgen": ex["Sgen"][k], "Ed": v,
               "Ed_sobre_total": v / Ed_total if Ed_total else None}
              for k, v in ex.get("Ed", {}).items()]
    f_fallas = [{"codigo": f.codigo, "severidad": f.severidad.value,
                 "clasificacion": f.clasificacion.value, "variable": f.variable,
                 "valor_medido": f.valor_medido, "valor_esperado": f.valor_esperado,
                 "mensaje": f.mensaje, "sugerencia": f.sugerencia} for f in fallas]
    return {"corridas": [fila], "estados": f_estados, "componentes": f_comp, "fallas": f_fallas}


def _hoja(wb, nombre, cols):
    from openpyxl.styles import Font

    ws = wb.create_sheet(nombre, index=list(HOJAS).index(nombre))
    ws.append([c for c, _, _ in cols])
    ws.append([u for _, u, _ in cols])               # fila 2: unidades
    for celda in ws[1]:
        celda.font = Font(bold=True)
    ws.freeze_panes = "B3"


def _diccionario(wb):
    if "diccionario" in wb.sheetnames:
        wb.remove(wb["diccionario"])
    ws = wb.create_sheet("diccionario")
    ws.append(["hoja", "columna", "unidad", "descripcion"])
    for nombre, cols in HOJAS.items():
        for c, u, desc in cols:
            ws.append([nombre, c, u, desc])


def _abrir(ruta: Path):
    """Abre el Excel único (o lo crea) y agrega las hojas que le falten (archivos viejos)."""
    from openpyxl import Workbook, load_workbook

    if ruta.exists():
        wb = load_workbook(ruta)
    else:
        wb = Workbook()
        wb.remove(wb.active)
    faltan = [n for n in HOJAS if n not in wb.sheetnames]
    for nombre in faltan:
        _hoja(wb, nombre, HOJAS[nombre])
    if faltan:
        _diccionario(wb)
    return wb


def _guardar(wb, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(ruta)
    except PermissionError as err:
        raise PermissionError(f"no se pudo escribir {ruta}: ciérralo en Excel y repite") from err


def agregar_corrida(filas: dict[str, list[dict]], ruta: Path | str = RUTA) -> int:
    """Agrega las filas de `filas_corrida` al Excel único (lo crea si no existe). Devuelve el id."""
    ruta = Path(ruta)
    wb = _abrir(ruta)
    ws = wb["corridas"]
    ids = [c.value for c in ws["A"][2:] if isinstance(c.value, int)]
    id_corrida = max(ids, default=0) + 1
    for nombre, cols in HOJAS.items():
        for f in filas.get(nombre, []):
            f = {**f, "id_corrida": id_corrida}
            wb[nombre].append([f.get(c) for c, _, _ in cols])
    _guardar(wb, ruta)
    return id_corrida


def agregar_verificacion(filas: list[dict], ruta: Path | str = RUTA) -> int:
    """Agrega filas de `verificacion.comparar` a la hoja `verificacion`. Devuelve cuántas."""
    ruta = Path(ruta)
    wb = _abrir(ruta)
    for f in filas:
        wb["verificacion"].append([f.get(c) for c, _, _ in _VERIFICACION])
    _guardar(wb, ruta)
    return len(filas)
