# Guía del diagrama en DWSIM (modo R, cierre B)

Plan de verificación, niveles V0–V2. Las entradas de cada punto están en
`03_verificacion/entradas_puntos.csv` (las mismas del código Python).

**Para qué sirve:** DWSIM es un tercer programa. Cierra el reciclo de otra forma y permite **cambiar la ecuación de estado**: con el paquete CoolProp debe coincidir casi exacto (tolerancias estrechas del §7 del plan); con Peng-Robinson mide cuánto depende el resultado del motor de propiedades.

## 1. Preparar la simulación

1. **Compuestos:** el fluido del punto (n-butano, R1234yf, isobutano, …; MM = hexametildisiloxano). [No verificado] Confirmar que existe en la base de compuestos y en el paquete CoolProp de tu versión.
2. **Paquetes de propiedades**, uno por corrida:
   - `CoolProp` (comparación principal);
   - `Peng-Robinson` (sensibilidad a la EoS);
   - agua: `Steam Tables (IAPWS-IF97)`.
3. **Unidades:** K, kPa, kJ/kg, kg/s, kW.

## 2. Diagrama

```
                 [AUX-ev: fluido a (P_ev, T_fuente)]      [AUX-cd: fluido a (P_cd, T_sumidero)]
                          │ (solo se lee h)                          │ (solo se lee h)
                          ▼                                          ▼
 S1 ──► BOMBA ──► S2 ──► CALENTADOR (Heater) ──► S3 ──► EXPANSOR ──► S4 ──► ENFRIADOR (Cooler) ──► S1*
  ▲                         ▲ Q_in de la hoja                                ▲ Q_out de la hoja       │
  └──────────────────────── RECYCLE (cierra el lazo en h1) ◄────────────────────────────────────────┘
```

| Equipo del modelo | Bloque de DWSIM | Especificación |
|---|---|---|
| Bomba | Pump | Presión de salida = P_ev; eficiencia = η_p |
| Turbina | Expander | Presión de salida = P_cd; eficiencia adiabática = η_t |
| Evaporador (ε) | Heater | **Calor añadido** = Q̇_in de la Spreadsheet |
| Condensador (ε) | Cooler | **Calor retirado** = Q̇_out de la Spreadsheet |
| h_3max, h_1min | 2 Material Streams auxiliares, sin conectar | mismo fluido y caudal; AUX-ev a (P_ev, T_fuente), AUX-cd a (P_cd, T_sumidero) |
| Lazo en h1 | Recycle | entre S1* (salida del Cooler) y S1 (entrada de la bomba) |
| Recuperador (solo VP-06) | Heat Exchanger, o un Heater y un Cooler con el mismo Q̇_rec | Q̇_rec = ε_rec·ṁ·q_max en la Spreadsheet [no verificado: si el bloque acepta efectividad, usarla] |

**Por qué las corrientes auxiliares:** la ε del modelo se define sobre el lado del fluido, h_3max = h(P_ev, T_fuente). No es la ε clásica de un intercambiador con dos corrientes. Las corrientes auxiliares dan esa h sin escribir scripts.

**Spreadsheet** (lee las entalpías específicas de las corrientes y escribe los calores):

```
Q_in  = m · eps_ev   · (h_AUXev − h_S2)
Q_out = m · eps_cond · (h_S4 − h_AUXcd)
```
(con recuperador: h_S2 → h_S2r y h_S4 → h_S4r)

**Arranque del Recycle:** S1 como líquido saturado a P_cd (fracción de vapor 0). Es el mismo arranque del Python. Si no converge con ε_cond baja (estado 1 bifásico), anotarlo como dato de convergencia: no es un error del modelo.

## 3. Qué exportar

La tabla de corrientes (Results > Material Streams) y los equipos a CSV, en `03_verificacion/dwsim/resultados_dwsim_<paquete>.csv`, con las columnas de `03_verificacion/README.md`.

## 4. Tolerancias (aprobadas en V-D, §7 del plan)

| Indicador | Python ↔ DWSIM-CoolProp | Python ↔ DWSIM-PR |
|---|---|---|
| T de cada estado | ±0,5 K | ±3 K |
| Δh, Q̇, Ẇ | ±0,5 % | ±3 % |
| η_th | ±0,1 pp | ±0,5 pp |
| x4 | ±0,005 | ±0,02 |
