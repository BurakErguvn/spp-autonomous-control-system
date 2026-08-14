"""Isolated routing tests: Clarke–Wright seed vs production ALNS.

3-way bench (scripts/benchmark_routing.py, real 30-panel layout, 3×480 min):

| instance        | CW km   | ALNS km | OR-Tools km | CW s   | ALNS s | OR-Tools s |
|-----------------|---------|---------|-------------|---------|--------|------------|
| B_2_hotspot     | 0.3735  | 0.3735  | 0.3735      | 0.000  | 0.003  | 2.35       |
| C_10_crack      | 0.4904  | 0.4904  | 0.4904      | 0.000  | 0.022  | 2.00       |
| mixed_15        | 0.8136  | 0.7938  | 0.7938      | 0.000  | 0.050  | 8.00       |
| hotspot_20      | 0.7500  | 0.6910  | 0.6910      | 0.000  | 0.068  | 8.00       |
| crack_24_tight  | 1.0436  | 0.9414  | 0.9414      | 0.000  | 0.069  | 8.00       |
| all_30_hotspot  | 1.2869  | 1.1245  | 1.1245      | 0.000  | 0.064  | 8.00       |

OR-Tools = ALNS mesafe, ~100× yavaş → kaldırıldı.
CW büyük örneklerde %2–13 daha uzun → yalnızca ALNS tohumu.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from modules.optimization.routing import (
    alns,
    clarke_wright,
    pack_into_k,
    route_distance,
    route_load,
    solve_cvrp,
    two_opt_route,
)

LAYOUT_FILE = Path("modules") / "gui" / "assets" / "panel_layout.json"
N_VEHICLES = 3
CAPACITY = 480


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _layout() -> dict:
    with open(LAYOUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def _gps(layout: dict, pid: int) -> tuple[float, float]:
    for p in layout["panels"]:
        if int(p["panel_id"]) == pid:
            return (float(p["gps"][0]), float(p["gps"][1]))
    origin = layout["origin_gps"]
    return (float(origin[0]), float(origin[1]))


def _instance(panels: list[int], service_min: list[int]) -> tuple[list[list[float]], list[int]]:
    layout = _layout()
    origin = layout["origin_gps"]
    depot = (float(origin[0]), float(origin[1]))
    locs = [depot] + [_gps(layout, pid) for pid in panels]
    n = len(locs)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist[i][j] = _haversine_km(locs[i], locs[j])
    return dist, [0] + list(service_min)


def _cw_packed(n: int, dist: list[list[float]], service: list[int]) -> list[list[int]]:
    routes = clarke_wright(n, dist, service, CAPACITY)
    routes = [two_opt_route(r, dist) for r in routes]
    return pack_into_k(routes, N_VEHICLES, service, CAPACITY, dist)


def _alns(n: int, dist: list[list[float]], service: list[int]) -> list[list[int]]:
    packed = _cw_packed(n, dist, service)
    return alns(
        packed,
        dist,
        service,
        CAPACITY,
        N_VEHICLES,
        iterations=max(200, min(1200, 80 * n)),
        rng=random.Random(0),
    )


def _metrics(routes: list[list[int]], dist: list[list[float]], service: list[int], n: int) -> tuple[int, float, bool]:
    covered = {c for r in routes for c in r}
    km = sum(route_distance(r, dist) for r in routes)
    feasible = all(route_load(r, service) <= CAPACITY for r in routes)
    return len(covered), km, feasible and len(covered) == n


# ── Isolated: Clarke–Wright + 2-opt ──────────────────────────────────────────


class TestClarkeWrightIsolated:
    def test_scenario_c_covers_and_fits(self):
        panels = [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
        dist, service = _instance(panels, [60] * 10)
        routes = _cw_packed(10, dist, service)
        cov, _, ok = _metrics(routes, dist, service, 10)
        assert cov == 10
        assert ok
        assert len(routes) == 3

    def test_all_30_hotspot_feasible(self):
        panels = list(range(30))
        dist, service = _instance(panels, [45] * 30)
        routes = _cw_packed(30, dist, service)
        cov, _, ok = _metrics(routes, dist, service, 30)
        assert cov == 30
        assert ok


# ── Isolated: ALNS ───────────────────────────────────────────────────────────


class TestAlnsIsolated:
    def test_scenario_b_covers(self):
        panels = [0, 29]
        dist, service = _instance(panels, [45, 45])
        routes, name = solve_cvrp(panels, dist, service, N_VEHICLES, CAPACITY)
        assert name == "alns"
        visited = [p for seq in routes.values() for p in seq]
        assert sorted(visited) == [0, 29]

    def test_tight_24_crack_capacity(self):
        panels = list(range(24))
        dist, service = _instance(panels, [60] * 24)
        routes = _alns(24, dist, service)
        cov, _, ok = _metrics(routes, dist, service, 24)
        assert cov == 24
        assert ok
        assert sum(route_load(r, service) for r in routes) == 24 * 60


# ── Selection: ALNS not worse than CW seed ───────────────────────────────────


class TestAlnsBeatsClarkeWright:
    def test_mixed_15_shorter_or_equal(self):
        panels = [0, 2, 4, 7, 9, 11, 13, 16, 18, 20, 22, 24, 26, 28, 29]
        service_min = [45, 60, 45, 60, 45, 60, 45, 60, 45, 60, 45, 60, 45, 60, 45]
        dist, service = _instance(panels, service_min)
        cw = _cw_packed(15, dist, service)
        al = _alns(15, dist, service)
        _, cw_km, cw_ok = _metrics(cw, dist, service, 15)
        _, al_km, al_ok = _metrics(al, dist, service, 15)
        assert cw_ok and al_ok
        assert al_km <= cw_km + 1e-9

    def test_all_30_shorter_or_equal(self):
        panels = list(range(30))
        dist, service = _instance(panels, [45] * 30)
        cw = _cw_packed(30, dist, service)
        al = _alns(30, dist, service)
        _, cw_km, cw_ok = _metrics(cw, dist, service, 30)
        _, al_km, al_ok = _metrics(al, dist, service, 30)
        assert cw_ok and al_ok
        assert al_km <= cw_km + 1e-9
        assert al_km < cw_km  # bench: 1.12 vs 1.29 km
