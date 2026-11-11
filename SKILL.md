---
name: lifecycle-segmentation
description: "Calcula el estado de ciclo de vida del cliente (Activo Caliente/Templado/Frio, Inactivo Congelado/Ultra Congelado/Iceberg) por recencia, y el ciclo de repeticion de compra (percentil 75, no la media) con sus dias criticos de disparo, a partir de cualquier tabla con fecha de compra anterior y ultima compra por cliente. Usa este skill cuando el usuario pida 'segmentacion por ciclo de vida', 'estados de actividad del cliente', 'cada cuanto repite compra', 'cuando lanzar el disparador de recompra', 'journey de reactivacion de inactivos', o pase una tabla con fechas de pedidos por cliente (opcionalmente con canal)."
---

# Lifecycle Segmentation

Segmenta clientes por **estado de relación** (recencia) y calcula su **ciclo de repetición** (percentil 75 de los días entre compras) para decidir **cuándo** hablar con cada uno. Complementa a `rfm-segmentation`: el RFM ordena por valor; este skill ordena por si el cliente sigue vivo y en qué momento de su ciclo está.

## Paso 1: identifica las columnas

Necesitas:
- id de cliente
- fecha de la compra anterior y fecha de la última compra. Si el usuario tiene una tabla de transacciones (una fila por pedido), agrégala antes: por cliente, sus dos últimas compras. Los clientes con una sola compra no tienen ciclo; trátalos aparte (el objetivo con ellos es la 2ª compra).
- opcional: columna de canal (tienda física, online, app...)

Si no está claro cómo se llaman las columnas o el formato de fecha, pregunta antes de ejecutar.

## Paso 2: ejecuta el script

```bash
python scripts/lifecycle_segmentation.py --input <tabla.csv> \
  --id-col <col_id> \
  --prev-date-col <col_fecha_anterior> \
  --last-date-col <col_fecha_ultima> \
  --channel-col <col_canal> \
  --date-format "%m/%d/%Y" \
  --output segmentos.csv
```

- `--as-of` (opcional): fecha de referencia. **Por defecto es la última compra registrada, no hoy.** No la cambies a la fecha actual salvo que los datos estén al día; si lo haces y queda más de 30 días por detrás, el script avisa.
- `--cuts` (opcional): límites en días de Caliente, Templado, Frío, Congelado y Ultra Congelado. Por defecto, los de clase: `120,240,365,730,1095`.
- Si el input es `.xlsx`, conviértelo a CSV primero. Si las fechas vienen de Excel con fórmulas (`NOW()`, tablas con `#REF!`), lee los valores originales de las columnas de fecha, no las columnas calculadas.

## Paso 3: explica el resultado, no solo lo entregues

1. **Estado = recencia, nunca ritmo.** Si el dataset trae una columna "Activo" calculada con los días entre compras (p. ej. `IF(Dias_Repeticion<366,"Activo")`), señálalo como error y cuantifica cuántos clientes clasifica mal (en el ejercicio de validación fueron 903 de 2.500).
2. **Fecha de referencia fija.** Si el dataset usa `NOW()`/`HOY()`, explica que el diagnóstico cambia cada día que se abre el archivo. En el ejercicio de validación, el porcentaje de activos pasaba del 65% (base sana) al 42% (base mediocre) solo por abrirlo seis meses después.
3. **Media nunca sin mediana al lado.** El script avisa cuando el sesgo supera el 15%. El ciclo estratégico es el **percentil 75**: responde a "¿hasta qué día tengo que llegar para cubrir a la mayoría antes de que se caiga?". La mediana responde a otra pregunta ("¿cómo es el cliente típico?") y deja fuera a la mitad.
4. **Comprueba el ciclo por canal**, pero no lo separes si no cambia nada: si todos los canales tienen un P75 parecido, un único calendario sirve para toda la base. Si uno se aparta más de un 15%, valora un calendario propio, sobre todo si es un canal grande.
5. **Salud de la base**: ≤25% activos = base quemada (no hay campaña que lo arregle, hay que cambiar procesos); 25-55% = normal; >55% = sana.
6. **Días críticos**: del día 0 a la mitad del ciclo no se impacta, porque parte de la base iba a volver sola y gastar ahí es pagar por ventas hechas. Después: disparador suave (mitad del ciclo), segundo disparador (3/4), oferta (90%) y prórroga (ciclo + 30 días), que es la ventana de recuperación más rentable. Escribe los disparadores en negativo: "si NO ha comprado el día N, sale la pieza P".
7. **Journey para inactivos**: "fuego lento" a los activos (presencia, sin descuento) y "microondas" a los inactivos (pocas veces, incentivo fuerte, en el pico comercial del año). Nunca "más impactos" a quien no responde: tras dos picos sin respuesta, hibernación. Mide con grupo de control (venta incremental, no ventas brutas).

## Antigüedad y convenciones (díselo al usuario cuando aplique)

- **Antigüedad**: la clase cruza actividad × antigüedad (Altas nuevas vinculadas / Vinculado / Desvinculado / Lover / Perdido). Sin fecha de alta solo se conoce la **antigüedad mínima** (`Antiguedad_minima_dias`, desde la penúltima compra). Con ella se confirman algunos segmentos (p. ej. inactivos con 3er año como poco = perdidos), pero los clientes con sus dos compras en el último año quedan indeterminados (pueden ser altas nuevas o históricos). Pide la fecha de primera compra; también hace falta para las cohortes.
- **Dos escalas de inactivos**: la de clase (Congelado 12-24 / Ultra Congelado 24-36 / Iceberg >36 meses, desde la última compra) y la del libro, cap. 15 (Helado / Congelado / Iceberg, desde que el cliente sale de la actividad). Este skill usa la de clase. Lo que importa es usar una sola convención, escribirla y mantenerla en todos los informes.
- **Los cortes son de partida, no una ley**: en negocios de compra muy espaciada (mueble, maquinaria, regalos anuales) hay que estirarlos. Una buena comprobación es que el corte de "Caliente" quede cerca del P75 del ciclo de repetición (en el ejercicio de validación coincidían: 120 días).
