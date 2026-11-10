---
name: lifecycle-segmentation
description: "Calcula el estado de ciclo de vida del cliente (Activo Caliente/Templado/Frio, Inactivo Congelado/Ultra Congelado/Iceberg) y el ciclo de repeticion de compra (percentil 75, no la media) a partir de cualquier tabla de clientes/transacciones con fecha de compra anterior y ultima compra. Usa este skill cuando el usuario pida 'segmentacion por ciclo de vida', 'estados de actividad del cliente', 'cada cuanto repite compra', 'cuando esta un cliente inactivo', o pase una tabla con fechas de pedidos por cliente (opcionalmente con canal)."
---

# Lifecycle Segmentation

Segmenta clientes por **estado de ciclo de vida** (actividad cruzada con el ciclo real de repeticion de compra, no con meses fijos inventados), usando el percentil 75 de los dias entre compras como unidad de medida. Complementa a `rfm-segmentation`: el RFM ordena por valor, este skill ordena por si el cliente sigue vivo o ya se fue.

## Paso 1 — identifica las columnas en la tabla del usuario

Necesitas:
- Un id de cliente
- Una fecha de compra anterior y una fecha de ultima compra (si el usuario tiene una tabla de transacciones con una fila por pedido en vez de 2 fechas por cliente, hay que agregarla primero: para cada cliente, quedarse con sus 2 ultimas compras)
- Opcional: una columna de canal (tienda fisica, online, app...) — si existe, el ciclo se calcula por canal, no mezclado, porque el capitulo de origen advierte que mezclar canales con pesos distintos desplaza el percentil hacia el canal mas grande

Si no esta claro como se llaman las columnas relevantes o el formato de fecha, pregunta al usuario antes de ejecutar nada — no adivines.

## Paso 2 — ejecuta el script

```bash
python scripts/lifecycle_segmentation.py --input <tabla.csv> \
  --id-col <col_id> \
  --prev-date-col <col_fecha_anterior> \
  --last-date-col <col_fecha_ultima> \
  --channel-col <col_canal>  \
  --date-format "%m/%d/%Y" \
  --as-of <YYYY-MM-DD> \
  --output segmentos.csv
```

`--channel-col` y `--as-of` son opcionales. `--as-of` fija la fecha de referencia ("hoy"); si se omite usa la fecha actual del sistema — pero en datasets de ejercicio/formación conviene pasarla explícita porque la fecha "real" de hoy puede estar muy alejada de cuándo se generaron los datos (y eso hace que toda la base salga "inactiva" de forma artificial — avisa de esto si lo detectas).

Solo depende de la libreria estandar de Python (`csv`, `statistics`, `datetime`) — no requiere pandas ni instalar nada. Si el input es `.xlsx`, convierte primero a CSV (con `openpyxl` si el usuario lo tiene) antes de ejecutar.

## Paso 3 — explica el resultado, no solo lo entregues

1. **Nunca presentes la media del ciclo de repeticion sin la mediana al lado.** La distribucion de dias entre compras siempre tiene cola larga (pocos clientes muy espaciados tiran la media hacia arriba) — el script avisa automaticamente cuando el sesgo supera el 15%.
2. **El ciclo estrategico es el percentil 75, no un numero de meses inventado.** Explica que responde a "¿hasta donde tengo que llegar para cubrir a la mayoria antes de que se caiga?", no "¿como es el cliente tipico?" (eso seria la mediana).
3. Si hay columna de canal, **nunca mezcles canales con pesos muy distintos** en un solo ciclo — el canal pequeño (ej. app al 15% del volumen) queda enmascarado por el grande y el percentil no sirve para ninguno de los dos.
4. El indicador de salud de la base (% activos) tiene 3 lecturas, no una escala continua:

| % activos | Lectura | Que hacer |
|---|---|---|
| ≤25% (20/80) | Base quemada o mal gestionada | NO mandar mas campanas — hay que cambiar procesos/herramientas, el problema no se arregla con una pieza de marketing |
| 25-55% (50/50) | Normal, mejorable | Diagnosticar donde se pierde y tratar por tramo |
| >55% (65/35) | Excelente | Fidelizando bien, casi siempre con programa de por medio |

5. Los **cortes de temperatura (0.6x/1x/2x/4x/6x del ciclo)** son un punto de partida razonable, no una ley — si el negocio tiene compra muy espaciada por naturaleza (ej. mueble, maquinaria, juguetes de cumpleaños con compra anual por niño), avisa de que estos multiplicadores pueden necesitar ajuste con el propio comercial/marketing del cliente antes de usarse en produccion.
6. Cierra siempre con el calendario de disparadores que imprime el script: la idea central es que **los primeros dias del ciclo no deben llevar ningun impacto** (todavia hay gente que iba a volver sola) y que la ventana de recuperacion mas rentable es justo despues de cruzar el ciclo esperado, no cuando el cliente ya lleva meses "congelado".

## Aviso sobre datasets de ejercicio/formacion

Si el dataset solo trae 2 fechas de compra por cliente (sin fecha de alta ni historial mas largo) y la fecha de referencia real ("hoy") esta muy alejada de esas fechas, el modelo de **ciclo de repeticion** (ch16: percentil 75, por canal) se puede calcular con total fiabilidad — pero el modelo de **estado de ciclo de vida** (ch15: Activo/Inactivo segun recencia) puede salir degenerado (toda la base como "Inactiva" solo porque pasaron años desde que se grabaron los datos, no porque el negocio este mal). Dilo explicitamente al usuario en vez de presentar el indicador de salud como si fuera un diagnostico real del negocio: en ese caso solo sirve para practicar el calculo, no para decidir nada.
