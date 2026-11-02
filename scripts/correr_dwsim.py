"""Arma el ORC de cada punto en DWSIM (bloques Pump, Heater, Expander, Cooler) y lo resuelve (V2-V3).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.correr_dwsim              # CoolProp y Peng-Robinson, todos los puntos
    python -m scripts.correr_dwsim --paquete pr --punto VP-03

Sigue `03_verificacion/dwsim/GUIA_DWSIM.md` con las entradas de `entradas_puntos.csv` (las del
código, sacadas de los papers). Los calores de Heater/Cooler salen de las ε con dos corrientes
auxiliares a (P_ev, T_fuente) y (P_cd, T_sumidero), como la Spreadsheet de la guía; los lazos (h1 y
q_rec) se cierran recalculando el diagrama, como un Recycle. Propiedades: solo las del paquete de
DWSIM. Salidas: `dwsim/puntos/<id>_<paquete>.dwxmz` (resuelto) y `dwsim/resultados_dwsim_<paq>.csv`.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR = RAIZ / "03_verificacion" / "dwsim"
ENTRADAS = RAIZ / "03_verificacion" / "entradas_puntos.csv"
DWSIM = Path(r"D:\DWSIM")
PAQUETES = {"coolprop": "CoolProp", "pr": "Peng-Robinson (PR)"}
COMPUESTO = {"MM": "MM", "n-Butane": "N-butane", "Water": "Water", "IsoButane": "Isobutane",
             "R1234yf": "R1234yf", "Propane": "Propane", "R134a": "R134a", "R152a": "R152A",
             "Ammonia": "Ammonia"}
TOL_H, MAX_ITER = 1e-6, 300                 # kJ/kg, como el Recycle con tolerancia estrecha
POS = {"S1": (60, 420), "BOMBA": (160, 420), "S2": (260, 420), "REC-FRIO": (360, 420), "S2r": (460, 420),
       "EVAPORADOR": (560, 300), "S3": (660, 180), "EXPANSOR": (760, 180), "S4": (860, 180),
       "REC-CALIENTE": (860, 300), "S4r": (860, 420), "CONDENSADOR": (760, 560), "S1c": (60, 560),
       "AUXev": (560, 100), "AUXcd": (760, 680), "AUX2": (360, 680), "AUX4": (460, 100),
       "Ep": (160, 520), "Erf": (360, 520), "Eev": (480, 300), "Et": (860, 80), "Erc": (960, 300), "Ecd": (860, 560)}


def _cargar_dwsim():
    os.chdir(DWSIM)                          # DWSIM busca sus datos junto al ejecutable
    sys.path.append(str(DWSIM))
    import pythonnet
    pythonnet.load("netfx")
    import clr
    for n in ("CapeOpen", "DWSIM.Automation", "DWSIM.Interfaces", "DWSIM.GlobalSettings",
              "DWSIM.SharedClasses", "DWSIM.Thermodynamics", "DWSIM.UnitOperations"):
        clr.AddReference(str(DWSIM / f"{n}.dll"))
    from DWSIM.Automation import Automation3
    return Automation3()


class Ciclo:
    """Diagrama de un punto: S1→Bomba→S2→[Rec frío]→S2r→Evap→S3→Expansor→S4→[Rec caliente]→S4r→Cond→S1c."""

    def __init__(self, auto, fila: dict, paquete: str):
        from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType as T
        from DWSIM.Interfaces.Enums import StreamSpec
        from DWSIM.UnitOperations import UnitOperations as U
        import System
        self.auto, self.Spec = auto, StreamSpec
        self.fs = fs = auto.CreateFlowsheet()
        fs.AddCompound(COMPUESTO[fila["fluido_coolprop"]])
        fs.CreateAndAddPropertyPackage(PAQUETES[paquete])
        mk = lambda tipo, n: fs.AddObject(tipo, *POS[n], n).GetAsObject()  # noqa: E731
        s = {n: mk(T.MaterialStream, n) for n in ("S1", "S2", "S2r", "S3", "S4", "S4r", "S1c",
                                                  "AUXev", "AUXcd", "AUX2", "AUX4")}
        e = {n: mk(T.EnergyStream, n) for n in ("Ep", "Erf", "Eev", "Et", "Erc", "Ecd")}
        u = {"bomba": mk(T.Pump, "BOMBA"), "rec_f": mk(T.Heater, "REC-FRIO"),
             "evap": mk(T.Heater, "EVAPORADOR"), "turb": mk(T.Expander, "EXPANSOR"),
             "rec_c": mk(T.Cooler, "REC-CALIENTE"), "cond": mk(T.Cooler, "CONDENSADOR")}
        cadena = [("S1", "bomba", "S2", "Ep"), ("S2", "rec_f", "S2r", "Erf"),
                  ("S2r", "evap", "S3", "Eev"), ("S3", "turb", "S4", "Et"),
                  ("S4", "rec_c", "S4r", "Erc"), ("S4r", "cond", "S1c", "Ecd")]
        for ent, uo, sal, en in cadena:
            fs.ConnectObjects(s[ent].GraphicObject, u[uo].GraphicObject, -1, -1)
            fs.ConnectObjects(u[uo].GraphicObject, s[sal].GraphicObject, -1, -1)
            entra_energia = uo in ("bomba", "rec_f", "evap")
            a, b = (e[en], u[uo]) if entra_energia else (u[uo], e[en])
            fs.ConnectObjects(a.GraphicObject, b.GraphicObject, -1, -1)
        self.s, self.u = s, u
        self.f = f = {k: float(v) if v else None for k, v in fila.items() if k not in ("id_punto", "fluido_coolprop")}
        self.P_ev, self.P_cd = f["P_ev"] * 1e3, f["P_cd"] * 1e3          # Pa
        u["bomba"].CalcMode, u["bomba"].Pout = U.Pump.CalculationMode.OutletPressure, self.P_ev
        u["bomba"].Eficiencia = 100.0 * f["eta_p"]                          # DWSIM la pide en %
        u["turb"].CalcMode, u["turb"].POut = U.Expander.CalculationMode.OutletPressure, self.P_cd
        u["turb"].AdiabaticEfficiency = 100.0 * f["eta_t"]                  # DWSIM la pide en %
        for k, modo in (("rec_f", U.Heater.CalculationMode.HeatAdded), ("evap", U.Heater.CalculationMode.HeatAdded),
                        ("rec_c", U.Cooler.CalculationMode.HeatRemoved), ("cond", U.Cooler.CalculationMode.HeatRemoved)):
            u[k].CalcMode, u[k].DeltaP, u[k].Eficiencia = modo, 0.0, 100.0
        for n in s.values():
            n.SetMassFlow(f["m"])
            n.SetOverallComposition(System.Array[float]([1.0]))

    def _pt(self, n: str, P: float, T: float):
        self.s[n].SpecType = self.Spec.Temperature_and_Pressure
        self.s[n].SetPressure(P)
        self.s[n].SetTemperature(T)

    def _ph(self, n: str, P: float, h: float):
        self.s[n].SpecType = self.Spec.Pressure_and_Enthalpy
        self.s[n].SetPressure(P)
        self.s[n].SetMassEnthalpy(h)

    def h(self, n):
        return self.s[n].GetMassEnthalpy()

    def T(self, n):
        return self.s[n].GetTemperature()

    def calcular(self):
        err = self.auto.CalculateFlowsheet2(self.fs)
        if err is not None and len(err) > 0:
            raise RuntimeError("; ".join(str(x.Message) for x in err))

    def resolver(self) -> dict:
        f, U = self.f, self.u
        eps_rec = f["eps_rec"] or 0.0
        self._pt("AUXev", self.P_ev, f["T_fuente"])
        self._pt("AUXcd", self.P_cd, f["T_sumidero"])
        self._pt("S1", self.P_cd, f["T_sumidero"])          # arranque: líquido a (P_cd, T_sumidero)
        self._pt("AUX2", self.P_cd, f["T_sumidero"])
        self._pt("AUX4", self.P_ev, f["T_sumidero"])
        for k in ("rec_f", "evap", "rec_c", "cond"):
            U[k].DeltaQ = 0.0
        self.calcular()
        h1, q, m = self.h("S1"), 0.0, f["m"]
        for it in range(1, MAX_ITER + 1):           # Gauss-Seidel: cada Q con los estados de esta pasada
            self._ph("S1", self.P_cd, h1)
            U["rec_f"].DeltaQ = U["rec_c"].DeltaQ = m * q
            self.calcular()                                     # bomba → h2, T2
            h2, T2 = self.h("S2"), self.T("S2")
            U["evap"].DeltaQ = m * f["eps_ev"] * (self.h("AUXev") - (h2 + q))
            self.calcular()                                     # evaporador y expansor → S3, S4
            q_n = 0.0
            if eps_rec:
                self._pt("AUX2", self.P_cd, T2)
                self._pt("AUX4", self.P_ev, self.T("S4"))
                self.calcular()
                q_n = eps_rec * min(self.h("S4") - self.h("AUX2"), self.h("AUX4") - h2)
            U["cond"].DeltaQ = m * f["eps_cond"] * (self.h("S4r") - self.h("AUXcd"))
            self.calcular()                                     # condensador → S1c
            h1_n = self.h("S1c")
            d = max(abs(h1_n - h1), abs(q_n - q))
            h1, q = h1_n, q_n
            if d < TOL_H and it > 1:
                break
        else:
            raise RuntimeError(f"el lazo no convergió en {MAX_ITER} iteraciones (d={d:.2e})")
        self._ph("S1", self.P_cd, h1)
        U["rec_f"].DeltaQ = U["rec_c"].DeltaQ = m * q
        self.calcular()
        return self._salidas(it)

    def _salidas(self, it: int) -> dict:
        U, m = self.u, self.f["m"]
        Q_in, W_t, W_p = U["evap"].DeltaQ, abs(U["turb"].DeltaQ), U["bomba"].DeltaQ
        return {"W_net": W_t - W_p, "W_t": W_t, "W_p": W_p, "Q_in": Q_in,
                "Q_out": U["cond"].DeltaQ, "Q_rec": U["rec_f"].DeltaQ,
                "eta": (W_t - W_p) / Q_in, "dh_s": W_t / m / self.f["eta_t"],
                "T1": self.T("S1"), "T2": self.T("S2"), "T3": self.T("S3"), "T4": self.T("S4"),
                "x4": self.s["S4"].Phases[2].Properties.massfraction, "iter": it}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paquete", choices=list(PAQUETES), action="append")
    ap.add_argument("--punto", action="append")
    a = ap.parse_args()
    filas = list(csv.DictReader(ENTRADAS.open(encoding="utf-8")))
    auto = _cargar_dwsim()
    (DIR / "puntos").mkdir(exist_ok=True)
    for paq in a.paquete or list(PAQUETES):
        res = []
        for fila in filas:
            pid = fila["id_punto"]
            if a.punto and pid not in a.punto:
                continue
            try:
                c = Ciclo(auto, fila, paq)
                r = c.resolver()
                auto.SaveFlowsheet(c.fs, str(DIR / "puntos" / f"{pid}_{paq}.dwxmz"), True)
            except Exception as ex:                      # se anota y se sigue con el resto
                print(f"{paq} {pid}: ERROR {str(ex)[:200]}", flush=True)
                continue
            res.append({"id_punto": pid, **r})
            print(f"{paq} {pid}: W_net={r['W_net']:.2f} kW eta={r['eta']:.5f} iter={r['iter']}",
                  flush=True)
        if res:
            ruta = DIR / f"resultados_dwsim_{paq}.csv"
            nuevos = {r["id_punto"] for r in res}       # con --punto se conservan los demás puntos
            viejos = [r for r in csv.DictReader(ruta.open(encoding="utf-8"))] if ruta.exists() else []
            with ruta.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(res[0]))
                w.writeheader()
                w.writerows([r for r in viejos if r["id_punto"] not in nuevos] + res)
            print(f"{len(res)} puntos en {ruta}")


if __name__ == "__main__":
    main()
