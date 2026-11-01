"""Traduce un caso publicado (bloque `verificacion` de `01_referencias/casos/*.yaml`) al modo R.

Plan de verificación (bóveda, PLAN_VERIFICACION_ORC_2026-10-31):
- V-B: las efectividades salen de los estados del paper, como en `tests/test_cengel.py`:
      ε_ev   = (h3 − h2r) / (h(P_ev, T_fuente) − h2r)
      ε_cond = (h4r − h1) / (h4r − h(P_cd, T_sumidero))
      ε_rec  = q_rec / q_max,  q_max = mín[h4 − h(P_cd, T2), h(P_ev, T4) − h2]  (recuperador.py)
  Luego `resolver_ciclo_R` debe VOLVER a esos estados: el lazo en h1 queda probado.
- V-A: el caudal del fluido de Yari y Campos se saca con el pinch del paper, y el de Çengel
  10-29 con el balance del agua geotérmica. Solo aquí, nunca en `src/` (memoria «solo modo R»).

Todos los números salen del YAML; aquí solo hay conversiones (°C → K).
"""

from __future__ import annotations

from src.components import bomba, turbina
from src.components._estado import estado_Ph
from src.properties.coolprop_adapter import CoolPropAdapter

__all__ = ["entradas_modo_R", "salidas", "componentes"]

K = 273.15
_AGUA = None


def _agua() -> CoolPropAdapter:
    global _AGUA
    if _AGUA is None:
        _AGUA = CoolPropAdapter("Water")
    return _AGUA


def _presion(b, spec: dict) -> float:
    return spec["kPa"] if "kPa" in spec else b.P_sat(spec["T_sat_degC"] + K)


def _h(b, P: float, spec: dict) -> float:
    return b.h(P, q=spec["q"]) if "q" in spec else b.h(P, T=spec["T_degC"] + K)


def _eta_t(b, spec, P_cd: float, e3) -> float:
    if not isinstance(spec, dict):
        return spec
    h4 = b.h(P_cd, T=spec["desde_T4_degC"] + K)                # η_t derivada de T4 del paper
    return (e3.h - h4) / (e3.h - b.h(P_cd, s=e3.s))


def _m(spec: dict, b, *, P_ev: float, h2: float, h3: float) -> float:
    if "kg_s" in spec:
        return spec["kg_s"]
    w = _agua()
    if "pinch" in spec:                    # pinch en el punto de burbuja (Yari, Campos)
        p = spec["pinch"]
        T_pp = b.T_sat(P_ev) + p["dT_pinch"]
        q_fuente = w.h(p["P_fuente_kPa"], T=p["T_fuente_degC"] + K) - w.h(p["P_fuente_kPa"], T=T_pp)
        return p["m_fuente"] * q_fuente / (h3 - b.h(P_ev, q=0.0))
    f = spec["flash"]                      # Çengel 10-27/10-29: líquido del separador
    P = f["P_flash_kPa"]
    h_pozo = w.h(w.P_sat(f["T_pozo_degC"] + K), q=0.0)
    hl, hv = w.h(P, q=0.0), w.h(P, q=1.0)
    m_liq = f["m_pozo"] * (1.0 - (h_pozo - hl) / (hv - hl))
    return m_liq * (hl - w.h(P, T=f["T_salida_degC"] + K)) / (h3 - h2)


def entradas_modo_R(punto: dict, b) -> dict:
    """Argumentos de `resolver_ciclo_R` equivalentes al caso del paper."""
    P_ev, P_cd = _presion(b, punto["P_ev"]), _presion(b, punto["P_cd"])
    T_f, T_s = punto["T_fuente_degC"] + K, punto["T_sumidero_degC"] + K
    e1 = estado_Ph(b, P_cd, _h(b, P_cd, punto["estado_1"]), m=1.0, etiqueta="1")
    e2, _ = bomba.resolver(e1, b, P_salida=P_ev, eta_p=punto["eta_p"], m=1.0)
    h3 = _h(b, P_ev, punto["estado_3"])
    e3 = estado_Ph(b, P_ev, h3, m=1.0, etiqueta="3")
    eta_t = _eta_t(b, punto["eta_t"], P_cd, e3)
    e4, _ = turbina.resolver(e3, b, P_salida=P_cd, eta_t=eta_t)
    m = _m(punto["m"], b, P_ev=P_ev, h2=e2.h, h3=h3)
    eps_rec, q_rec = None, 0.0
    if "Q_rec_kW" in punto:
        q_rec = punto["Q_rec_kW"] / m
        q_max = min(e4.h - b.h(P_cd, T=e2.T), b.h(P_ev, T=e4.T) - e2.h)
        eps_rec = q_rec / q_max
    h2r, h4r = e2.h + q_rec, e4.h - q_rec
    return {"P_ev": P_ev, "P_cd": P_cd, "T_fuente": T_f, "T_sumidero": T_s,
            "eps_ev": (h3 - h2r) / (b.h(P_ev, T=T_f) - h2r),
            "eps_cond": (h4r - e1.h) / (h4r - b.h(P_cd, T=T_s)),
            "eps_rec": eps_rec, "eta_t": eta_t, "eta_p": punto["eta_p"], "m": m}


def salidas(r: dict, punto: dict) -> dict:
    """Magnitudes comparables con el paper (potencia eléctrica fuera del solver, como Bombarda)."""
    s = {k: r[k] for k in ("eta", "Wnet", "Wt", "Wp", "Qin", "Qout", "Qrec", "dh_s", "m")}
    if "electrico" in punto:
        el = punto["electrico"]
        s["W_el"] = el["eta_gen"] * r["Wt"] - r["Wp"] / el["eta_motor"]
        s["eta_el"] = s["W_el"] / r["Qin"]
    return s


def componentes(punto: dict, b) -> dict:
    """Nivel V1: bomba y turbina por separado (Çengel Ej. 10-2, que tiene ΔP en el ciclo)."""
    pb, pt = punto["bomba"], punto["turbina"]
    e1 = estado_Ph(b, pb["P_entrada_kPa"], b.h(pb["P_entrada_kPa"], T=pb["T_entrada_degC"] + K),
                   m=1.0, etiqueta="1")
    _, bo = bomba.resolver(e1, b, P_salida=pb["P_salida_kPa"], eta_p=pb["eta_p"], m=1.0)
    e3 = estado_Ph(b, pt["P_entrada_kPa"], b.h(pt["P_entrada_kPa"], T=pt["T_entrada_degC"] + K),
                   m=1.0, etiqueta="3")
    _, tu = turbina.resolver(e3, b, P_salida=pt["P_salida_kPa"], eta_t=pt["eta_t"])
    return {"w_bomba": bo["Wp"], "w_turbina": tu["Wt"]}
