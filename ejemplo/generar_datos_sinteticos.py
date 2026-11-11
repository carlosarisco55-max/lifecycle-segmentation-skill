"""Genera clientes INVENTADOS con forma realista para el ejemplo publicable.

No deriva de ningún dataset real: distribuciones paramétricas con semilla fija.
Uso: python ejemplo/generar_datos_sinteticos.py
"""
import csv
import random
from datetime import date, timedelta

random.seed(2026)
N = 1200
REF = date(2026, 6, 30)
CANALES = [("Tienda online", 0.50, 1.0), ("Tienda física", 0.35, 1.0), ("App", 0.15, 1.45)]


def canal():
    x, acc = random.random(), 0.0
    for nombre, peso, lentitud in CANALES:
        acc += peso
        if x <= acc:
            return nombre, lentitud
    return CANALES[-1][0], CANALES[-1][2]


def dias_repeticion(lentitud):
    u = random.random()
    if u < 0.85:
        d = random.gammavariate(2.2, 40) * lentitud
    elif u < 0.97:
        d = random.uniform(120, 360)
    else:
        d = random.uniform(361, 520)
    return max(7, round(d))


def recencia():
    u = random.random()
    if u < 0.60:
        return min(365, round(random.expovariate(1 / 140)))
    if u < 0.95:
        return round(random.uniform(366, 1000))
    return round(random.uniform(1100, 1260))


rows = []
for i in range(1, N + 1):
    nombre, lentitud = canal()
    ultima = REF - timedelta(days=recencia())
    anterior = ultima - timedelta(days=dias_repeticion(lentitud))
    rows.append((f"SIN{i:05d}", nombre, anterior.isoformat(), ultima.isoformat()))
rows[0] = (rows[0][0], rows[0][1], (REF - timedelta(days=40)).isoformat(), REF.isoformat())

with open("ejemplo/clientes_sinteticos.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Id_Cliente", "Origen_de_pedido", "Fecha_Compra_Anterior", "Fecha_Ultima_Compra"])
    w.writerows(rows)
print(f"{N} clientes sintéticos -> ejemplo/clientes_sinteticos.csv")
