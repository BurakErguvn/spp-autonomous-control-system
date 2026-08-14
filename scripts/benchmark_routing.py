"""CW+2-opt vs ALNS on the real 30-panel layout.

OR-Tools was measured once (same km as ALNS, 2–8 s vs ~0.07 s) and removed.

Usage (repo root):
    python scripts/benchmark_routing.py
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.optimization.routing import (  # noqa: E402
    alns,
    clarke_wright,
    pack_into_k,
    route_distance,
    route_load,
    two_opt_route,
)

LAYOUT_FILE = ROOT / "modules" / "gui" / "assets" / "panel_layout.json"
OUT_FILE = ROOT / "outputs" / "reports" / "routing_benchmark.json"

N_VEHICLES = 3
CAPACITY = 480
FUEL_TL_PER_KM = 3.0

# Frozen 3-way run (2026-08-14, venv OR-Tools 9.15). OR-Tools == ALNS km.
ORTOOLS_FROZEN = {
    "B_2_hotspot": {"km": 0.373532, "s": 2.35},
    "C_10_crack": {"km": 0.4904, "s": 2.00},
    "mixed_15": {"km": 0.793761, "s": 8.00},
    "hotspot_20": {"km": 0.690965, "s": 8.00},
    "crack_24_tight": {"km": 0.941398, "s": 8.00},
    "all_30_hotspot": {"km": 1.124522, "s": 8.00},
}


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def distance_matrix(locs: list[tuple[float, float]]) -> list[list[float]]:
    n = len(locs)
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                d[i][j] = haversine_km(locs[i], locs[j])
    return d


def load_layout() -> dict:
    with open(LAYOUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def panel_gps(layout: dict, pid: int) -> tuple[float, float]:
    for p in layout["panels"]:
        if int(p["panel_id"]) == pid:
            return (float(p["gps"][0]), float(p["gps"][1]))
    origin = layout["origin_gps"]
    return (float(origin[0]), float(origin[1]))


def build_instance(
    layout: dict, panels: list[int], service_min: list[int]
) -> tuple[list[list[float]], list[int]]:
    origin = layout["origin_gps"]
    depot = (float(origin[0]), float(origin[1]))
    locs = [depot] + [panel_gps(layout, pid) for pid in panels]
    return distance_matrix(locs), [0] + list(service_min)


def evaluate(routes: list[list[int]], dist: list[list[float]], service: list[int], n: int) -> dict:
    covered = {c for r in routes for c in r}
    loads = [route_load(r, service) for r in routes]
    feasible = all(load <= CAPACITY for load in loads)
    km = sum(route_distance(r, dist) for r in routes)
    return {
        "coverage": len(covered),
        "n": n,
        "distance_km": round(km, 6),
        "fuel_tl": round(km * FUEL_TL_PER_KM, 4),
        "feasible": feasible,
        "loads": loads,
        "ok": feasible and len(covered) == n,
    }


def run_cw(n: int, dist: list[list[float]], service: list[int]) -> list[list[int]]:
    routes = clarke_wright(n, dist, service, CAPACITY)
    routes = [two_opt_route(r, dist) for r in routes]
    return pack_into_k(routes, N_VEHICLES, service, CAPACITY, dist)


def run_alns(n: int, dist: list[list[float]], service: list[int], seed: int) -> list[list[int]]:
    packed = run_cw(n, dist, service)
    return alns(
        packed,
        dist,
        service,
        CAPACITY,
        N_VEHICLES,
        iterations=max(200, min(1200, 80 * n)),
        rng=random.Random(seed),
    )


def time_call(fn):
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0


def instances(layout: dict) -> list[dict]:
    all_ids = [int(p["panel_id"]) for p in layout["panels"]]
    return [
        {"name": "B_2_hotspot", "panels": [0, 29], "service": [45, 45]},
        {
            "name": "C_10_crack",
            "panels": [0, 3, 6, 9, 12, 15, 18, 21, 24, 27],
            "service": [60] * 10,
        },
        {
            "name": "mixed_15",
            "panels": [0, 2, 4, 7, 9, 11, 13, 16, 18, 20, 22, 24, 26, 28, 29],
            "service": [45, 60, 45, 60, 45, 60, 45, 60, 45, 60, 45, 60, 45, 60, 45],
        },
        {"name": "hotspot_20", "panels": all_ids[:20], "service": [45] * 20},
        {"name": "crack_24_tight", "panels": all_ids[:24], "service": [60] * 24},
        {"name": "all_30_hotspot", "panels": all_ids, "service": [45] * 30},
    ]


def rank_key(row: dict) -> tuple:
    dist = row["distance_km"] if row["distance_km"] is not None else 1e9
    return (-row["coverage"], 0 if row["feasible"] else 1, dist, row["runtime_s"])


def main() -> None:
    layout = load_layout()
    solvers = ("clarke_wright_2opt", "alns")
    rows: list[dict] = []

    for inst in instances(layout):
        n = len(inst["panels"])
        dist, service = build_instance(layout, inst["panels"], inst["service"])
        runners = {
            "clarke_wright_2opt": lambda n=n, dist=dist, service=service: run_cw(n, dist, service),
            "alns": lambda n=n, dist=dist, service=service: run_alns(n, dist, service, seed=0),
        }
        for name in solvers:
            routes, elapsed = time_call(runners[name])
            metrics = evaluate(routes, dist, service, n)
            row = {
                "instance": inst["name"],
                "solver": name,
                "n": n,
                "runtime_s": round(elapsed, 4),
                **metrics,
            }
            rows.append(row)
            frozen = ORTOOLS_FROZEN[inst["name"]]
            print(
                f"{inst['name']:18} {name:20} n={n:2} "
                f"cov={metrics['coverage']:2}/{n} "
                f"ok={str(metrics['ok']):5} "
                f"km={metrics['distance_km']} "
                f"t={elapsed:.4f}s "
                f"(ortools frozen km={frozen['km']} t={frozen['s']}s)"
            )

    wins: dict[str, int] = {s: 0 for s in solvers}
    for inst_name in {r["instance"] for r in rows}:
        group = [r for r in rows if r["instance"] == inst_name]
        group.sort(key=rank_key)
        wins[group[0]["solver"]] += 1

    print("\nWins by instance:", wins)
    winner = max(solvers, key=lambda s: wins[s])
    print("Selected winner:", winner)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "winner": winner,
        "wins": wins,
        "ortools_removed": True,
        "ortools_frozen": ORTOOLS_FROZEN,
        "rows": rows,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
