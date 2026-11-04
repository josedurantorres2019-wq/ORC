# Papers usados

Referencias bibliográficas de las fuentes con las que se formula, verifica y valida el modelo ORC. Los archivos PDF **no** se incluyen en este repositorio (derechos de autor); la carpeta local `Papers/` está excluida en `.gitignore`.

## Artículos y tesis

- Bombarda, P., Invernizzi, C. M., y Pietra, C. (2010). Heat recovery from Diesel engines: A thermodynamic comparison between Kalina and ORC cycles. *Applied Thermal Engineering, 30*(2-3), 212-219. https://doi.org/10.1016/j.applthermaleng.2009.08.006 (versión de autor en HAL: hal-00521157)

- Campos Rodríguez, C. E., Escobar Palacio, J. C., Venturini, O. J., Silva Lora, E. E., Melián Cobas, V., Marques dos Santos, D., Lofrano Dotto, F. R., y Gialluca, V. (2013). Exergetic and economic comparison of ORC and Kalina cycle for low temperature enhanced geothermal system in Brazil. *Applied Thermal Engineering, 52*(1), 109-119.

- Campos Rodríguez, C. E. (2014). *Análise paramétrica das opções tecnológicas para a geração de eletricidade a partir de fontes geotérmicas melhoradas de baixa temperatura* [Tesis doctoral, Universidade Federal de Itajubá (UNIFEI)]. Itajubá, Brasil.

- Vera-Romero, I., Corona-Ruíz, S. L., Martínez Reyes, J., Moreno Nava, I., Ordaz Murillo, O., y Méndez Ábrego, V. M. (2018). Thermal comparison of an organic Rankine cycle activated by a low-temperature geothermal heat source. *Journal of Mechanics Engineering and Automation, 8*, 309-315. https://doi.org/10.17265/2159-5275/2018.07.004

- Yari, M., Mehr, A. S., Zare, V., Mahmoudi, S. M. S., y Rosen, M. A. (2015). Exergoeconomic comparison of TLC (trilateral Rankine cycle), ORC (organic Rankine cycle) and Kalina cycle using a low grade heat source. *Energy, 83*, 712-722. https://doi.org/10.1016/j.energy.2015.02.080

## Libro

- Çengel, Y. A., y Boles, M. A. *Termodinámica* (edición en español), cap. 10: Ciclos de potencia de vapor y combinados.

## Dónde se usa cada fuente

| Fuente | Uso en el repositorio | Archivo de caso |
|---|---|---|
| Bombarda et al. (2010) | Verificación del ORC con MM y recuperador (Tabla 5) | `01_referencias/casos/bombarda2010_orc_mm.yaml` |
| Campos Rodríguez et al. (2013) | Solo contraste de orden de magnitud (Tabla 4) | `01_referencias/casos/campos2013_tabla4.yaml` |
| Campos Rodríguez (2014) | Punto de n-butano | `01_referencias/casos/campos2014_nbutano.yaml` |
| Vera-Romero et al. (2018) | ORC geotérmico de Los Negritos, punto del R113 | `01_referencias/casos/vera2018_r113.yaml` |
| Yari et al. (2015) | Tablas 6 y 7 y Fig. 5 (Ẇ_net frente a T3) | `01_referencias/casos/yari2015_orc_tabla6.yaml`, `yari2015_fig5_digitalizada.csv` |
| Çengel y Boles | Pruebas de unidad con agua e isobutano (Ej. 10-1 a 10-3, Prob. 10-26, 10-29) | `01_referencias/casos/cengel_cap10.yaml`, `cengel_cap10_ampliacion.yaml` |
