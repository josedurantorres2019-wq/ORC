"""Tablas Markdown del reporte de verificación (las escribe `comparar_herramientas`)."""

from __future__ import annotations

__all__ = ["escribir_tablas"]


def _fmt(v, err=None) -> str:
    if v in (None, ""):
        return "—"
    s = f"{v:.5g}" if abs(v) >= 1 else f"{v:.5f}"
    return s if err is None else f"{s} ({100 * err:+.2f} %)"


def escribir_tablas(tabla: list[dict], hs: list[str], VARIABLES: dict, ruta) -> None:
    """Tablas del reporte: contra el paper (valor y error) y resumen Python ↔ herramienta."""
    L = ["## Contra el paper", "", "| Punto | Variable | Paper | Código | " + " | ".join(hs) + " |",
         "|---|---|---|---|" + "---|" * len(hs)]
    for t in (t for t in tabla if t["comparacion"] == "paper"):
        e_py = (t["Python"] - t["paper"]) / abs(t["paper"])
        L.append(f"| {t['id_punto']} | {t['variable']} | {_fmt(t['paper'])} | {_fmt(t['Python'], e_py)} | "
                 + " | ".join(_fmt(t.get(h), t.get(f"err_{h}")) + (f" {t[f'ver_{h}']}" if f"ver_{h}" in t else "")
                              for h in hs) + " |")
    L += ["", "## Python ↔ herramienta (máximo error por punto)", "",
          "| Punto | " + " | ".join(f"{h} máx ΔE (%) | {h} máx ΔT (K) | {h} fuera de tol."
                                   for h in hs) + " |",
          "|---|" + "---|" * (3 * len(hs))]
    for pid in dict.fromkeys(t["id_punto"] for t in tabla):
        fila = [pid]
        for h in hs:
            rows = [t for t in tabla if t["id_punto"] == pid and t["comparacion"] == "Python" and h in t]
            if not rows:
                fila += ["—"] * 3
                continue
            eE = [abs(r[f"err_{h}"]) * 100 for r in rows if VARIABLES[r["variable"]][0] == "energia"]
            eT = [abs(r[f"err_{h}"]) for r in rows if VARIABLES[r["variable"]][0] == "T"]
            nf = sum(r[f"ver_{h}"] != "pasa" for r in rows)
            fila += [f"{max(eE):.2f}", f"{max(eT):.2f}", f"{nf}/{len(rows)}"]
        L.append("| " + " | ".join(fila) + " |")
    ruta.write_text(chr(10).join(L) + chr(10), encoding="utf-8")
    print(f"Tablas: {ruta}")
