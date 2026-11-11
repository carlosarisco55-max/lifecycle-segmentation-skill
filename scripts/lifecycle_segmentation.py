"""Customer lifecycle-state segmentation (ciclo de vida) + repeat-purchase cycle.

Two linked models:

1. Repeat-purchase cycle (ciclo de repeticion): days between each customer's
   previous and last purchase. The *strategic* cycle is the 75th percentile,
   not the mean (the long tail of slow repeaters always inflates the mean).
   Computed globally and, optionally, per channel.
2. Lifecycle state (termometro): Activo Caliente/Templado/Frio or
   Inactivo Congelado/Ultra Congelado/Iceberg, based on RECENCY (days since the
   last purchase) -- never on the repeat gap. Default cuts are the class ones
   (4/8/12/24/36 months, in days) and can be changed with --cuts.

The reference date defaults to the LAST purchase in the file, never today:
with today() the result changes every day the script runs, and stale
training datasets look "dead" for no business reason.

Stdlib only (csv, statistics, datetime, argparse) -- no pandas required.

Usage:
    python lifecycle_segmentation.py --input ciclo.csv \
        --id-col Id_Cliente \
        --prev-date-col Fecha_Compra_Anterior \
        --last-date-col Fecha_Ultima_Compra \
        --channel-col Origen_de_pedido \
        --date-format "%m/%d/%Y" \
        --output segmentos.csv
"""
import argparse
import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime

LABELS = ["Activo Caliente", "Activo Templado", "Activo Frio",
          "Inactivo Congelado", "Inactivo Ultra Congelado", "Inactivo Iceberg"]


def percentile(values, pct):
    """pct in [0, 100]. Same as Excel PERCENTILE.INC / numpy linear interpolation."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def cycle_stats(days):
    media = statistics.mean(days)
    mediana = statistics.median(days)
    return {"n": len(days), "media": media, "mediana": mediana, "p75": percentile(days, 75),
            "sesgo_pct": (media - mediana) / mediana * 100 if mediana else 0}


def subestado(recencia, cuts):
    for label, cut in zip(LABELS, cuts):
        if recencia <= cut:
            return label
    return LABELS[-1]


def momento(recencia, ciclo):
    if recencia <= ciclo * 0.5:
        return "1. Silencio (no impactar)"
    if recencia <= ciclo:
        return "2. Disparadores de recompra"
    if recencia <= ciclo + 30:
        return "3. Prorroga (recuperar ya)"
    return "4. Fuera de ciclo"


def salud_base(pct_activos):
    if pct_activos <= 25:
        return "20/80 - base quemada o mal gestionada: hay que cambiar procesos, no mandar mas campanas"
    if pct_activos <= 55:
        return "50/50 - normal, se puede mejorar"
    return "65/35 - base sana, se esta fidelizando bien"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--id-col", required=True)
    ap.add_argument("--prev-date-col", required=True, help="Fecha de la compra ANTERIOR a la ultima")
    ap.add_argument("--last-date-col", required=True, help="Fecha de la ULTIMA compra")
    ap.add_argument("--channel-col", default=None, help="Columna de canal (opcional): el ciclo se calcula tambien por canal")
    ap.add_argument("--date-format", default="%m/%d/%Y")
    ap.add_argument("--as-of", default=None,
                    help="Fecha de referencia YYYY-MM-DD. Por defecto, la ultima compra registrada en el fichero (nunca hoy).")
    ap.add_argument("--cuts", default="120,240,365,730,1095",
                    help="Limites en dias de Caliente,Templado,Frio,Congelado,Ultra Congelado (por defecto los de clase: 4/8/12/24/36 meses)")
    args = ap.parse_args()

    cuts = [int(x) for x in args.cuts.split(",")]
    if len(cuts) != 5 or cuts != sorted(cuts):
        ap.error("--cuts necesita 5 valores crecientes")

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        ap.error("el fichero de entrada no tiene filas")

    for r in rows:
        r["_prev"] = datetime.strptime(r[args.prev_date_col], args.date_format)
        r["_last"] = datetime.strptime(r[args.last_date_col], args.date_format)
    max_last = max(r["_last"] for r in rows)
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else max_last
    print(f"Fecha de referencia: {as_of:%Y-%m-%d}" + ("" if args.as_of else " (ultima compra registrada)"))
    gap = (as_of - max_last).days
    if gap > 30:
        print(f"  AVISO: la referencia es {gap} dias posterior a la ultima compra del fichero. "
              f"Todos los clientes 'envejecen' {gap} dias sin que haya pasado nada en el negocio.")

    for r in rows:
        r["Dias_Repeticion"] = (r["_last"] - r["_prev"]).days
        r["Dias_Desde_Ultima"] = (as_of - r["_last"]).days
        r["Antiguedad_minima_dias"] = (as_of - r["_prev"]).days
        r["_canal"] = r[args.channel_col] if args.channel_col else "(global)"

    stats_global = cycle_stats([r["Dias_Repeticion"] for r in rows])
    ciclo = stats_global["p75"]
    print("\n=== Ciclo de repeticion: media vs mediana vs P75 ===")
    print(f"Global -> n={stats_global['n']} media={stats_global['media']:.1f} mediana={stats_global['mediana']:.1f} "
          f"P75={ciclo:.1f} (sesgo media-mediana {stats_global['sesgo_pct']:.1f}%"
          f"{' -> no presentar la media' if stats_global['sesgo_pct'] > 15 else ''})")
    if args.channel_col:
        por_canal = defaultdict(list)
        for r in rows:
            por_canal[r["_canal"]].append(r["Dias_Repeticion"])
        for canal, dias in sorted(por_canal.items()):
            s = cycle_stats(dias)
            aviso = "  <-- ciclo distinto del global, valorar calendario propio" if abs(s["p75"] - ciclo) > 0.15 * ciclo else ""
            print(f"  {canal:20s} n={s['n']:5d} ({s['n'] / len(rows):5.1%}) media={s['media']:6.1f} "
                  f"mediana={s['mediana']:6.1f} P75={s['p75']:6.1f}{aviso}")

    for r in rows:
        r["Subestado"] = subestado(r["Dias_Desde_Ultima"], cuts)
        r["Estado"] = "Activo" if r["Subestado"].startswith("Activo") else "Inactivo"
        r["Momento_del_ciclo"] = momento(r["Dias_Desde_Ultima"], ciclo)

    print("\n=== Estados (por recencia, nunca por dias entre compras) ===")
    cnt = Counter(r["Subestado"] for r in rows)
    for lab in LABELS:
        print(f"  {lab:26s} {cnt.get(lab, 0):6d}  {cnt.get(lab, 0) / len(rows):6.1%}")
    activos = sum(1 for r in rows if r["Estado"] == "Activo")
    print(f"Salud de la base: {activos / len(rows):.1%} activos -> {salud_base(activos / len(rows) * 100)}")

    print(f"\n=== Dias criticos (ciclo estrategico P75 = {ciclo:.0f} dias) ===")
    print(f"  0-{ciclo * 0.5:.0f}     : silencio, no impactar (la mitad iba a volver sola)")
    print(f"  {ciclo * 0.5:.0f}        : disparador suave")
    print(f"  {ciclo * 0.75:.0f}        : segundo disparador")
    print(f"  {ciclo * 0.9:.0f}       : venta persuasiva / oferta")
    print(f"  {ciclo:.0f}-{ciclo + 30:.0f}  : prorroga, ventana de recuperacion mas rentable")
    mom = Counter(r["Momento_del_ciclo"] for r in rows)
    print("Clientes hoy en cada momento:")
    for k in sorted(mom):
        print(f"  {k:30s} {mom[k]:6d}")

    out_cols = [c for c in rows[0] if not c.startswith("_")]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nGuardado: {args.output}")


if __name__ == "__main__":
    main()
