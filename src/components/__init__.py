"""Componentes del ciclo ORC (D-14): bomba, evaporador, turbina, condensador, recuperador.

Funciones puras `resolver(...)`: reciben `EstadoTermo` de entrada, un `PropertyBackend`
(solo la interfaz, nunca un motor concreto) y sus parámetros por palabra clave, y
devuelven `EstadoTermo` de salida más un dict con las energías en kW. Ecuaciones en la
bóveda, `MODELO_MATEMATICO_ORC_2026-10-30.md` §2.3.

Hipótesis comunes a todos (D-15): H1 estacionario, H2 adiabático hacia el ambiente,
H3 ΔP = 0 (la presión de salida es la de entrada salvo en bomba y turbina),
H4 Δe_c = Δe_p = 0. Balance de masa: un solo caudal ṁ en todo el lazo del fluido.
"""
