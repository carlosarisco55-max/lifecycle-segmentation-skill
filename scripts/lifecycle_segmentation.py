"""Customer lifecycle-state segmentation (ciclo de vida) + repeat-purchase cycle.

Implements two linked models from the "ciclo de vida" method:

1. Repeat-purchase cycle (ciclo de repeticion): given two purchase dates per
   customer, computes the gap in days and derives the *strategic* cycle as
   the 75th percentile (NOT the mean, which is always pulled up by the long
   tail of occasional buyers) -- optionally split by channel, since different
   channels have different natural cadences.
2. Lifecycle state (termometro): classifies each customer as
   Caliente/Templado/Frio (active) or Congelado/Ultra Congelado/Iceberg
   (inactive) based on days since their last purchase, using the strategic
   cycle above as the unit of measurement instead of fixed arbitrary months.

Stdlib only (csv, statistics, datetime, argparse) -- no pandas required.

Usage:
    python lifecycle_segmentation.py --input ciclo.csv \
        --id-col Id_Cliente \
        --prev-date-col Fecha_Compra_Anterior \
        --last-date-col Fecha_Ultima_Compra \
        --channel-col Origen_de_pedido \
        --date-format "%m/%d/%Y" \
        --as-of 2026-11-10 \
        --output segmentos.csv
"""
import argparse
import csv
import statistics
from collections import defaultdict
from datetime import datetime


def percentile(values, pct):
    """pct in [0, 100]. Stdlib-only equivalent of numpy.percentile (linear interpolation)."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def cycle_stats(days_list):
    media = statistics.mean(days_list)
    mediana = statistics.median(days_list)
    p75 = percentile(days_list, 75)
    sesgo_pct = ((media - mediana) / mediana * 100) if mediana else 0
    return {"n": len(days_list), "media": media, "mediana": mediana, "p75": p75, "sesgo_pct": sesgo_pct}


def temperatura(dias_desde_ultima, ciclo):
    """Classify recency against the strategic cycle (ciclo), not fixed months.
    Active thresholds: 0.6x / 1x / 2x. Inactive: 4x / 6x / beyond."""
    if dias_desde_ultima <= ciclo * 0.6:
        return "Activo Caliente"
    if dias_desde_ultima <= ciclo:
        return "Activo Templado"
    if dias_desde_ultima <= ciclo * 2:
        return "Activo Frio"
    if dias_desde_ultima <= ciclo * 4:
        return "Inactivo Congelado"
    if dias_desde_ultima <= ciclo * 6:
        return "Inactivo Ultra Congelado"
    return "Inactivo Iceberg"


def salud_base(pct_activos):
    if pct_activos <= 25:
        return "20/80 - base quemada o mal gestionada: no hay tratamiento de campana que valga, hay que cambiar procesos"
    if pct_activos <= 55:
        return "50/50 - normal, se puede mejorar"
    return "65/35 - excelente, fidelizando bien"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--id-col", required=True)
    ap.add_argument("--prev-date-col", required=True, help="Fecha de la compra ANTERIOR a la ultima")
    ap.add_argument("--last-date-col", required=True, help="Fecha de la ULTIMA compra")
    ap.add_argument("--channel-col", default=None, help="Columna de canal (opcional); si se da, el ciclo se calcula por canal")
    ap.add_argument("--date-format", default="%m/%d/%Y")
    ap.add_argument("--as-of", default=None, help="Fecha de referencia 'hoy' (YYYY-MM-DD). Por defecto, la fecha actual del sistema.")
    args = ap.parse_args()

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else datetime.now()

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        prev = datetime.strptime(r[args.prev_date_col], args.date_format)
        last = datetime.strptime(r[args.last_date_col], args.date_format)
        r["_dias_repeticion"] = (last - prev).days
        r["_dias_desde_ultima"] = (as_of - last).days
        r["_canal"] = r[args.channel_col] if args.channel_col else "(global)"

    por_canal = defaultdict(list)
    for r in rows:
        por_canal[r["_canal"]].append(r["_dias_repeticion"])

    stats_por_canal = {canal: cycle_stats(dias) for canal, dias in por_canal.items()}
    stats_global = cycle_stats([r["_dias_repeticion"] for r in rows])

    print("=== Ciclo de repeticion (ch16): media vs mediana vs P75 ===")
    print(f"Global -> n={stats_global['n']} media={stats_global['media']:.1f} "
          f"mediana={stats_global['mediana']:.1f} P75={stats_global['p75']:.1f} "
          f"(sesgo media-mediana: {stats_global['sesgo_pct']:.1f}%)")
    if args.channel_col:
        for canal, s in sorted(stats_por_canal.items()):
            flag = "  <-- usar P75 de este canal, no la media" if s["sesgo_pct"] > 15 else ""
            print(f"  {canal:20s} n={s['n']:5d} media={s['media']:6.1f} mediana={s['mediana']:6.1f} P75={s['p75']:6.1f}{flag}")

    # Umbral: ciclo estrategico por canal del propio cliente, o global si no hay canal
    for r in rows:
        ciclo = stats_por_canal[r["_canal"]]["p75"] if args.channel_col else stats_global["p75"]
        r["_ciclo_estrategico_cliente"] = ciclo
        r["Estado_Ciclo_Vida"] = temperatura(r["_dias_desde_ultima"], ciclo)

    activos = sum(1 for r in rows if r["Estado_Ciclo_Vida"].startswith("Activo"))
    pct_activos = activos / len(rows) * 100
    print(f"\n=== Salud de la base (ch15) ===")
    print(f"Activos: {activos}/{len(rows)} ({pct_activos:.1f}%) -> {salud_base(pct_activos)}")

    print(f"\n=== Disparadores sugeridos (sobre el ciclo global P75={stats_global['p75']:.0f} dias) ===")
    c = stats_global["p75"]
    print(f"  Dia 0            : ultima compra, no impactar (dejar enfriar)")
    print(f"  Dia {c*0.5:.0f} (~mitad)   : disparador suave")
    print(f"  Dia {c*0.75:.0f} (avanzado) : segundo disparador, mas tecnico")
    print(f"  Dia {c*0.9:.0f} (cierre)   : venta persuasiva / cupon")
    print(f"  Dia {c:.0f}-{c*1.25:.0f} (prorroga): ventana de recuperacion -- la mas rentable, no esperar a 'iceberg'")

    fieldnames = list(rows[0].keys())
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nGuardado: {args.output}")


if __name__ == "__main__":
    main()
