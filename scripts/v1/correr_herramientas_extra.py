"""Corre EES y DWSIM con fluidos que los scripts congelados de v1.0.0 no tienen en su tabla (R113).

Uso (desde la raíz del repo; solo con orden del usuario):
    python -m scripts.v1.correr_herramientas_extra ees            # EES, todos los puntos
    python -m scripts.v1.correr_herramientas_extra dwsim --punto VP-18

No edita `scripts/correr_ees.py` ni `scripts/correr_dwsim.py`: agrega el nombre del fluido a sus
tablas en memoria y llama a su `main()`.
"""

from __future__ import annotations

import sys

from scripts import correr_dwsim, correr_ees

FLUIDOS_EES = {"R113": "R113"}
COMPUESTOS_DWSIM = {"R113": "R113"}

if __name__ == "__main__":
    herramienta = sys.argv.pop(1)
    correr_ees.FLUIDO_EES.update(FLUIDOS_EES)
    correr_dwsim.COMPUESTO.update(COMPUESTOS_DWSIM)
    (correr_ees if herramienta == "ees" else correr_dwsim).main()
