# Lifecycle Segmentation (ciclo de vida del cliente)

[![CI](https://github.com/carlosarisco55-max/lifecycle-segmentation-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/carlosarisco55-max/lifecycle-segmentation-skill/actions/workflows/ci.yml)

Herramienta en Python que clasifica a los clientes de cualquier negocio en estados de ciclo de vida (Activo Caliente/Templado/Frío, Inactivo Congelado/Ultra Congelado/Iceberg) y calcula su **ciclo de repetición de compra** — el tiempo real entre dos compras de un mismo cliente, usado como unidad de medida en vez de cortes fijos arbitrarios (ej. "30/90/365 días").

Complementa a [`rfm-segmentation-skill`](https://github.com/carlosarisco55-max/rfm-segmentation-skill): el RFM ordena por valor, esta herramienta ordena por **estado de relación** (¿sigue vivo o ya se fue?) — son preguntas distintas sobre la misma base de clientes.

Script de Python de librería estándar (sin pandas ni dependencias que instalar), empaquetado también como *skill* de Claude Code.

## Qué resuelve

Dado un CSV con la fecha de la compra anterior y la última compra de cada cliente, responde:

- **¿Cada cuánto repite compra un cliente, de verdad?** (no la media, que el sesgo de la cola larga siempre infla)
- **¿Qué clientes están activos y cuáles ya se fueron?**, usando como corte el ciclo real del negocio, no un número inventado
- **¿Qué porcentaje de la base está realmente viva** (indicador 20/80 vs 50/50 vs 65/35)?
- **¿Cuándo hay que lanzar el disparador de recompra** antes de que el cliente cruce su ciclo esperado?

## Cómo funciona (resumen)

1. Para cada cliente, calcula los días entre su penúltima y su última compra (`Dias_Repeticion`).
2. Calcula el **percentil 75** de esa distribución (no la media ni la mediana) como "ciclo estratégico" — el tramo donde ya ha repetido el 75% de los clientes. Si hay columna de canal, lo calcula **por canal** (el ciclo de una compra en tienda física no es el mismo que online).
3. Clasifica a cada cliente según los días transcurridos desde su última compra, usando múltiplos de ese ciclo estratégico (no meses fijos):

| Estado | Corte (sobre el ciclo estratégico) |
|---|---|
| Activo Caliente | ≤ 0.6× |
| Activo Templado | ≤ 1× |
| Activo Frío | ≤ 2× |
| Inactivo Congelado | ≤ 4× |
| Inactivo Ultra Congelado | ≤ 6× |
| Inactivo Iceberg | > 6× |

4. Calcula el indicador de salud de la base (% activos) y lo compara contra los umbrales 20/80, 50/50, 65/35.
5. Sugiere los días críticos ("disparadores") del calendario de recuperación: a qué día desde la última compra conviene lanzar cada pieza, y por qué los primeros días del ciclo no deben llevar impacto.

## Uso

```bash
python scripts/lifecycle_segmentation.py \
  --input clientes.csv \
  --id-col Id_Cliente \
  --prev-date-col Fecha_Compra_Anterior \
  --last-date-col Fecha_Ultima_Compra \
  --channel-col Origen_de_pedido \
  --date-format "%m/%d/%Y" \
  --as-of 2026-11-10 \
  --output segmentos.csv
```

`--channel-col` y `--as-of` son opcionales (sin `--as-of` usa la fecha actual del sistema). Solo librería estándar de Python (`csv`, `statistics`, `datetime`) — sin pandas ni dependencias que instalar.

## Output

Un CSV con el estado de ciclo de vida por cliente, más un resumen en consola: ciclo de repetición (media/mediana/P75, global y por canal, con aviso cuando la media se desvía de la mediana en más del 15%), salud de la base, y el calendario de disparadores sugerido.

## Origen

Validado contra el ejercicio del Módulo 9 (Marketing Digital e IA Generativa, INESDI) sobre "Segmentación de estados de ciclo de vida" — 2.500 clientes reales con fechas de compra por canal (App / Tienda física / Tienda online). Los resultados del script coinciden con el cálculo manual en pandas usado para resolver el ejercicio.
