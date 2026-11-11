# Lifecycle Segmentation (ciclo de vida del cliente)

[![CI](https://github.com/carlosarisco55-max/lifecycle-segmentation-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/carlosarisco55-max/lifecycle-segmentation-skill/actions/workflows/ci.yml)

Herramienta en Python que clasifica a los clientes de cualquier negocio en estados de ciclo de vida (Activo Caliente/Templado/Frío, Inactivo Congelado/Ultra Congelado/Iceberg) y calcula su **ciclo de repetición de compra**: cada cuánto vuelve de verdad un cliente (percentil 75, no la media). Con ese ciclo fija los días críticos en los que conviene activar cada disparador de recompra.

Complementa a [`rfm-segmentation-skill`](https://github.com/carlosarisco55-max/rfm-segmentation-skill): el RFM ordena por valor, esta herramienta ordena por **estado de relación** (¿sigue vivo o ya se fue?) y por **momento** (¿cuándo toca hablarle?).

Script de Python de librería estándar (sin pandas ni dependencias que instalar), empaquetado también como *skill* de Claude Code.

## Qué resuelve

Dado un CSV con la fecha de la compra anterior y la última compra de cada cliente, responde:

- **¿Cada cuánto repite compra un cliente, de verdad?** La media no sirve: siempre la infla la cola de clientes que tardan más de un año.
- **¿Qué clientes están activos y cuáles ya se fueron?**, y con qué "temperatura".
- **¿Qué porcentaje de la base está viva?** (indicador 20/80 · 50/50 · 65/35).
- **¿Cuándo hay que lanzar el disparador de recompra**, y cuántos clientes hay hoy en cada momento del ciclo?

## Dos reglas que el script aplica siempre

1. **El estado se calcula con la recencia** (días desde la última compra), **nunca con los días entre compras**. Clasificar como "activo" a quien repitió rápido hace dos años es el error más común; en el ejercicio de validación, una fórmula así clasificaba mal a 903 de 2.500 clientes.
2. **La fecha de referencia es la última compra registrada, no hoy.** Con `today()` el resultado cambia cada día que se ejecuta. En el ejercicio de validación, ejecutarlo seis meses después de la última compra bajaba los activos del 65% al 42%, sin que hubiera pasado nada en el negocio. Se puede fijar otra con `--as-of`; si queda más de 30 días por detrás de la última compra, el script avisa.

## Cómo funciona

1. Para cada cliente calcula los días entre su penúltima y su última compra (`Dias_Repeticion`).
2. Calcula media, mediana y **percentil 75**, que es el ciclo estratégico: el día en que ya ha repetido el 75% de los clientes. Si hay columna de canal, lo calcula también por canal y avisa cuando un canal se aparta más de un 15% del global.
3. Clasifica a cada cliente por días desde la última compra. Por defecto usa los cortes de la clase, que se pueden cambiar con `--cuts`:

| Subestado | Días desde la última compra |
|---|---|
| Activo Caliente | ≤ 120 (4 meses) |
| Activo Templado | 121-240 (4-8 meses) |
| Activo Frío | 241-365 (8-12 meses) |
| Inactivo Congelado | 366-730 (12-24 meses) |
| Inactivo Ultra Congelado | 731-1.095 (24-36 meses) |
| Inactivo Iceberg | > 1.095 |

4. Calcula la salud de la base (% activos) frente a los umbrales 20/80, 50/50 y 65/35.
5. Sitúa a cada cliente en su momento del ciclo: silencio (no impactar hasta la mitad del ciclo), disparadores, prórroga (30 días tras cerrar el ciclo: la ventana de recuperación más rentable) o fuera de ciclo.
6. Añade la **antigüedad mínima** (días desde la penúltima compra). Sin fecha de alta es lo único que se puede afirmar sobre la antigüedad: el cliente existe, como poco, desde esa compra.

## Uso

```bash
python scripts/lifecycle_segmentation.py \
  --input clientes.csv \
  --id-col Id_Cliente \
  --prev-date-col Fecha_Compra_Anterior \
  --last-date-col Fecha_Ultima_Compra \
  --channel-col Origen_de_pedido \
  --date-format "%m/%d/%Y" \
  --output segmentos.csv
```

`--channel-col`, `--as-of` y `--cuts` son opcionales. Solo librería estándar de Python (`csv`, `statistics`, `datetime`).

## Output

Un CSV con, por cliente: `Dias_Repeticion`, `Dias_Desde_Ultima`, `Antiguedad_minima_dias`, `Subestado`, `Estado` y `Momento_del_ciclo`. En consola sale además un resumen con el ciclo de repetición (global y por canal), el reparto por estados, la salud de la base, el calendario de días críticos y cuántos clientes hay hoy en cada momento.

## Origen y validación

Validado contra el ejercicio del Módulo 9 (Marketing Digital e IA Generativa, INESDI), "Segmentación de estados de ciclo de vida": 2.500 clientes con sus dos últimas compras por canal (App / Tienda física / Tienda online). Los resultados coinciden cliente a cliente con el libro de Excel resuelto a mano con fórmulas: P75 de 120 días, 64,7% de activos y 116 clientes en prórroga.
