# Preguntas y criterios del modelo ORC (F0 · control G1)

Decisión D-01, aprobada por el usuario el 2026-10-30. **Pendiente de revisión del profesor.** Los
valores que se citan están en [`../02_modelo/definiciones.yaml`](../02_modelo/definiciones.yaml).
Plan y justificación: bóveda, `04_PROJECTS/active/Ciclo ORC/` (D-01, D-03, D-05, D-07 y D-15).

## Alcance

- Modelo: ORC subcrítico simple, con el recuperador opcional apagado (D-14).
- Dos modos de cierre (D-15):
  - **R:** convención del Kalina, para convalidar con él.
  - **F:** fuente finita con pinch, para el benchmark.
- Fluidos (D-05): n-butano y R1234yf a 390–434 K; MM a 623,15 K.
- **Fuera de esta etapa:** la comparación ORC–Kalina. Aquí solo se asegura que el planteamiento
  matemático sea paralelo al del Kalina (D-15). Los datos de la corrida de comparación se definen
  más adelante, y las corridas de la campaña Kalina no se usan.

Todas las preguntas están escritas para que la respuesta pueda ser «no». Las tolerancias se fijan
aquí, **antes** de correr.

## Preguntas

### P1 · Caso de diseño
Con la fuente a 420 K en modo R y las entradas base de `definiciones.yaml`, ¿qué η_I,
η_II, η/η_Carnot y w_net dan el n-butano y el R1234yf? ¿**Existe**, para cada uno, un punto que
pase todos los filtros de D-07?

- **Maqueta de respuesta:**

  | Fluido | P_ev (kPa) | T3 (K) | x4 | η_I | η_II | η/η_Carnot | w_net (kJ/kg) | ε_cd,eq | Restricción activa |
  |---|---|---|---|---|---|---|---|---|---|
  | n-butano | | | | | | | | | |
  | R1234yf | | | | | | | | | |

- **Criterio:**
  - balance de energía: |Q̇_in − Q̇_out − Ẇ_net| ≤ 10⁻³·Q̇_in;
  - cierre exergético: |Ė_Qin − Ẇ_net − Ė_Qout − ΣĖ_d| ≤ 10⁻³·Ė_Qin;
  - S1, S2 y S5–S8 cumplidas.

### P2 · Validación
En modo F, ¿el modelo reproduce Yari et al. (2015, Tabla 6) y Bombarda et al. (2010, ORC con MM)?

- **Maqueta de respuesta:** una tabla por caso de `01_referencias/casos/`, con valor publicado,
  valor del modelo y Δ % de Ẇ_net, η_th y ṁ.
- **Criterio:** |ΔẆ_net| ≤ 1 % por caso.
  - Es propuesta y no viene de una fuente; se fijó antes de correr.
  - Una diferencia mayor solo se acepta si se atribuye y documenta. Ejemplo: la EoS, como en
    R1234yf, que dio −3,5 % en la prueba previa.

### P3 · Sensibilidad
¿Cómo cambian η_I y η_II con P_ev y con T_fuente entre 390 y 434 K? ¿El óptimo queda dentro del
dominio, o lo fija un umbral de D-07 (0,9·P_c, x4,min o cavitación)?

- **Maqueta de respuesta:**
  - curvas de η frente a P_ev, una por T_fuente y por fluido;
  - tabla del umbral activo en cada óptimo;
  - barrido de f·P_c entre 0,80 y 0,95.
- **Criterio:** 10 a 20 puntos por variable, y en cada óptimo se informa qué umbral lo limita.

### P4 · Fluido
Entre 390 y 434 K, ¿uno de los dos fluidos supera al otro en η_II en **toda** la ventana, o el
orden cambia con T_fuente?

- **Maqueta de respuesta:** curva de η_II frente a T_fuente por fluido, con el punto de cruce si
  lo hay.
- **Criterio:** solo cuenta una diferencia mayor que 0,5 pp. Es propuesta, inspirada en la banda
  «no concluyente» de 0,4 a 0,7 pp del Kalina.

### P5 · Enunciado
Con la fuente a 623,15 K del enunciado, ¿puede operar un ORC con MM respetando
T3 ≤ 240 °C? ¿Con qué η_I y η_II? ¿Cuánto cambia si el límite es 300 °C?

- **Maqueta de respuesta:** tabla con los dos límites. En modo F, perfil T–Q, siempre que D-08
  esté cerrada.
- **Criterio:** que haya un punto admisible bajo D-07. Si no lo hay, la respuesta es «no» y se dice
  qué restricción lo impide.

## Aprobación

| Control | Quién | Estado |
|---|---|---|
| G1 (estas preguntas) | usuario | aprobado, 2026-10-30 |
| G1 (estas preguntas) | profesor | pendiente |
