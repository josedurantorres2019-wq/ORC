"""`CoolPropAdapter`: implementación de `PropertyBackend` con CoolProp HEOS (H6, D-15).

Es el ÚNICO archivo del proyecto que importa CoolProp. Convierte unidades en la frontera:
CoolProp trabaja en SI (Pa, J/kg, J/(kg·K)); la interfaz en kPa, kJ/kg y kJ/(kg·K).

Hipótesis H6: ecuación de estado de Helmholtz de CoolProp (backend "HEOS"). Como el
modelo solo usa diferencias de h y s, el estado de referencia de entalpía del motor se
cancela (riesgo R-04); la exergía usa h0, s0 del mismo motor.

Los estados saturados se piden con el título (PQ): pedir (P, T_sat) es ambiguo y CoolProp
puede fallar o caer del lado equivocado de la campana.
"""

from __future__ import annotations

from typing import Optional

import CoolProp.CoolProp as CP

from .adapter import PropertyBackend, PropertyRangeError

__all__ = ["CoolPropAdapter"]

_K = 1e3          # kPa → Pa y kJ → J
_TOL_Q = 1e-9     # tolerancia para clasificar líquido/vapor saturado


class CoolPropAdapter(PropertyBackend):
    """Fluido puro de CoolProp. ``fluido`` es el nombre CoolProp (p.ej. "n-Butane", "MM")."""

    def __init__(self, fluido: str, motor: str = "HEOS") -> None:
        try:
            self._st = CP.AbstractState(motor, fluido)
        except ValueError as exc:
            raise PropertyRangeError(f"CoolProp no reconoce el fluido {fluido!r}: {exc}") from exc
        self.fluido = fluido
        self.motor = motor
        self._P_crit = self._st.p_critical() / _K
        self._T_crit = self._st.T_critical()

    # --- constantes del fluido -------------------------------------------------------
    @property
    def P_crit(self) -> float:
        return self._P_crit

    @property
    def T_crit(self) -> float:
        return self._T_crit

    # --- núcleo: un solo punto de entrada a CoolProp ------------------------------------
    def _actualizar(self, P: float, *, T=None, h=None, s=None, q=None) -> None:
        dados = [n for n, v in (("T", T), ("h", h), ("s", s), ("q", q)) if v is not None]
        if len(dados) != 1:
            raise ValueError(f"se necesita P y exactamente una de T, h, s, q; llegó {dados}")
        Pa = P * _K
        try:
            if T is not None:
                self._st.update(CP.PT_INPUTS, Pa, T)
            elif h is not None:
                self._st.update(CP.HmassP_INPUTS, h * _K, Pa)
            elif s is not None:
                self._st.update(CP.PSmass_INPUTS, Pa, s * _K)
            else:
                self._st.update(CP.PQ_INPUTS, Pa, q)
        except ValueError as exc:
            raise PropertyRangeError(
                f"{self.fluido}: CoolProp no resolvió P={P} kPa, {dados[0]}="
                f"{T if T is not None else h if h is not None else s if s is not None else q}"
                f": {exc}") from exc

    # --- contrato ----------------------------------------------------------------------
    def h(self, P: float, *, T: Optional[float] = None, s: Optional[float] = None,
          q: Optional[float] = None) -> float:
        self._actualizar(P, T=T, s=s, q=q)
        return self._st.hmass() / _K

    def s(self, P: float, *, T: Optional[float] = None, h: Optional[float] = None,
          q: Optional[float] = None) -> float:
        self._actualizar(P, T=T, h=h, q=q)
        return self._st.smass() / _K

    def T_sat(self, P: float) -> float:
        if P >= self._P_crit:
            raise PropertyRangeError(f"{self.fluido}: P={P} kPa >= P_crit, no hay saturación")
        self._actualizar(P, q=0.0)
        return self._st.T()

    def P_sat(self, T: float) -> float:
        if T >= self._T_crit:
            raise PropertyRangeError(f"{self.fluido}: T={T} K >= T_crit, no hay saturación")
        try:
            self._st.update(CP.QT_INPUTS, 0.0, T)
        except ValueError as exc:
            raise PropertyRangeError(f"{self.fluido}: P_sat({T} K) falló: {exc}") from exc
        return self._st.p() / _K

    def estado_Ph(self, P: float, h: float) -> dict:
        self._actualizar(P, h=h)
        T, s, v = self._st.T(), self._st.smass() / _K, 1.0 / self._st.rhomass()
        if P >= self._P_crit:
            return {"T": T, "s": s, "v": v, "q": None, "fase": "supercritico"}
        if self._st.phase() == CP.iphase_twophase:
            q = min(max(self._st.Q(), 0.0), 1.0)
        else:
            # Monofásico: se ubica contra las entalpías de saturación a la misma P.
            h_l, h_v = self.h(P, q=0.0), self.h(P, q=1.0)
            q = 0.0 if h <= h_l else 1.0 if h >= h_v else (h - h_l) / (h_v - h_l)
        if q <= _TOL_Q:
            fase = "liquido"
        elif q >= 1.0 - _TOL_Q:
            fase = "vapor"
        else:
            fase = "bifasico"
        return {"T": T, "s": s, "v": v, "q": q, "fase": fase}
