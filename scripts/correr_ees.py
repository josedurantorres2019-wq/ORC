"""Genera un programa de EES por punto de verificación y lo corre sin interfaz (nivel V2-V3).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.correr_ees                 # genera y corre todos los puntos
    python -m scripts.correr_ees --solo-generar  # solo escribe los programas

Cada programa sale de `03_verificacion/ees/orc_modo_R.txt` (las ecuaciones, sin tocarlas) con las
entradas de una fila de `03_verificacion/entradas_puntos.csv`. EES se lanza con
``EES.exe <programa> /solve /nosplash``: resuelve, escribe su CSV con ``$Export`` y se cierra.
Los CSV de cada punto se juntan en `03_verificacion/ees/resultados_ees.csv` (columnas del README).
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR = RAIZ / "03_verificacion" / "ees"
PLANTILLA = DIR / "orc_modo_R.txt"
ENTRADAS = RAIZ / "03_verificacion" / "entradas_puntos.csv"
SALIDA = DIR / "resultados_ees.csv"
EES = Path(r"D:\Desktop\varios\Nueva carpeta\EES\EES.exe")

# Nombre de cada fluido en EES V10
FLUIDO_EES = {"MM": "MM", "n-Butane": "n-Butane", "Water": "Water", "IsoButane": "Isobutane",
              "R1234yf": "R1234yf", "Propane": "Propane", "R134a": "R134a", "R152a": "R152a",
              "Ammonia": "Ammonia"}

# Lo que EES exporta, en este orden (columnas del README, sin exergía, más los residuos)
EXPORTA = ["W_net", "W_t", "W_p", "Q_in", "Q_out", "Q_rec", "eta", "dh_s", "T[1]", "T[2]", "T[3]",
           "T[4]", "x[4]", "res_h1", "res_rec", "N2"]


def _partes() -> tuple[str, str]:
    """(PROCEDURE lazo, ecuaciones desde los lazos hasta el final) de la plantilla."""
    t = PLANTILLA.read_text(encoding="utf-8")
    proc = t[t.index("PROCEDURE lazo("):t.index("$UnitSystem")].rstrip()
    return proc, t[t.index("{ ===== Lazos"):t.index("{ PARA TODOS")].rstrip()


def programa(fila: dict, csv_salida: Path) -> str:
    v = {k: fila[k] for k in ("P_ev", "P_cd", "T_fuente", "T_sumidero", "eps_ev", "eps_cond",
                              "eta_t", "eta_p", "m")}
    v["eps_rec"] = fila["eps_rec"] or "0"            # celda vacía = recuperador apagado
    proc, ecs = _partes()
    return "\n".join([
        f"{{ Punto {fila['id_punto']}: generado por scripts/correr_ees.py desde "
        f"entradas_puntos.csv y orc_modo_R.txt. No editar a mano. }}",
        proc, "", "$UnitSystem SI Mass K kPa kJ", "",
        f"F$ = '{FLUIDO_EES[fila['fluido_coolprop']]}'",
        *(f"{k} = {x}" for k, x in v.items()), "", ecs, "",
        f"$Export /A '{csv_salida}' {', '.join(EXPORTA)}", ""])


def _leer_csv_ees(ruta: Path) -> list[float]:
    """EES exporta con la configuración regional: ';' y coma decimal."""
    texto = ruta.read_text(encoding="latin-1").strip().splitlines()[-1]
    sep = ";" if ";" in texto else ","
    return [float(x.replace(",", ".")) if sep == ";" else float(x) for x in texto.split(sep)]


def _ventanas(pid: int) -> set[str]:
    """Títulos de las ventanas visibles del proceso (para ver si EES dejó avisos abiertos)."""
    u, titulos = ctypes.windll.user32, set()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(h, b, 256)
            titulos.add(b.value)
        return True
    u.EnumWindows(cb, 0)
    return titulos


def correr(prog: Path, out: Path, espera: float = 120.0) -> tuple[bool, str]:
    """Lanza EES, espera su CSV y lo cierra.

    Tras resolver, EES escribe el ``$Export`` y luego deja abierta la ventana «Warnings» si hubo
    avisos durante la iteración (p. ej. T fuera de rango con los valores iniciales por defecto).
    Esa ventana no deja que EES se cierre solo: se anota y se termina el proceso.
    """
    out.unlink(missing_ok=True)
    p = subprocess.Popen([str(EES), str(prog), "/solve", "/nosplash"])
    t0, titulos = time.time(), set()
    while time.time() - t0 < espera and p.poll() is None:
        if out.exists() and out.stat().st_size > 0:
            time.sleep(1.0)
            break
        time.sleep(0.5)
    if p.poll() is None:
        titulos = _ventanas(p.pid)
        p.kill()
        p.wait()
    avisos = "Warnings" in titulos
    otras = titulos - {"Warnings", prog.name, ""}
    return out.exists(), ("avisos de EES" if avisos else "") + (f" ventanas: {otras}" if otras else "")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo-generar", action="store_true")
    a = ap.parse_args()
    (DIR / "puntos").mkdir(exist_ok=True)
    filas = []
    for fila in csv.DictReader(ENTRADAS.open(encoding="utf-8")):
        pid = fila["id_punto"]
        prog, out = DIR / "puntos" / f"{pid}.txt", DIR / "puntos" / f"{pid}_salida.csv"
        prog.write_text(programa(fila, out), encoding="latin-1")
        if a.solo_generar:
            continue
        ok, nota = correr(prog, out)
        if not ok:
            print(f"{pid}: EES no escribió resultados ({nota or 'sin ventanas'})", flush=True)
            continue
        val = dict(zip(EXPORTA, _leer_csv_ees(out)))
        filas.append({"id_punto": pid, **{k.replace("[", "").replace("]", ""): x
                                          for k, x in val.items()}, "nota_ees": nota.strip()})
        print(f"{pid}: W_net={val['W_net']:.2f} kW  eta={val['eta']:.5f}  {nota}", flush=True)
    if filas:
        with SALIDA.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print(f"{len(filas)} puntos en {SALIDA}")


if __name__ == "__main__":
    main()
