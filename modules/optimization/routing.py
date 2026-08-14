"""CVRP rota çözücüleri: Clarke–Wright + 2-opt, ALNS, OR-Tools.

Üç yöntem aynı örnek üzerinde koşar; en yüksek kapsama, eşitlikte en kısa
toplam mesafe seçilir. OR-Tools yoksa atlanır.
"""

from __future__ import annotations

import logging
import math
import random
from copy import deepcopy

logger = logging.getLogger(__name__)

RouteDict = dict[int, list[int]]  # team_id -> panel_id listesi


def solve_cvrp_portfolio(
    panels: list[int],
    dist: list[list[float]],
    service: list[int],
    n_vehicles: int,
    capacity: int,
    time_limit_s: int = 8,
    rng_seed: int = 0,
) -> tuple[RouteDict, str]:
    """CW+2-opt, ALNS ve OR-Tools adaylarından en iyisini döner.

    ``dist`` ve ``service`` indeks 0 = depo, 1..N = ``panels`` sırası.
    """
    empty: RouteDict = {k: [] for k in range(1, n_vehicles + 1)}
    if not panels:
        return empty, "empty"

    n = len(panels)
    candidates: list[tuple[str, list[list[int]]]] = []

    cw_routes = clarke_wright(n, dist, service, capacity)
    cw_routes = [two_opt_route(r, dist) for r in cw_routes]
    packed = pack_into_k(cw_routes, n_vehicles, service, capacity, dist)
    candidates.append(("clarke_wright_2opt", packed))

    alns_routes = alns(
        packed,
        dist,
        service,
        capacity,
        n_vehicles,
        iterations=max(200, min(1200, 80 * n)),
        rng=random.Random(rng_seed),
    )
    candidates.append(("alns", alns_routes))

    ortools_routes = solve_ortools(
        n, dist, service, n_vehicles, capacity, time_limit_s
    )
    if ortools_routes is not None:
        candidates.append(("ortools", ortools_routes))

    best_name, best_idx = _pick_best(candidates, dist, service, capacity, n)
    return _to_panel_routes(best_idx, panels, n_vehicles), best_name


def route_distance(route: list[int], dist: list[list[float]]) -> float:
    """Depo dahil tur mesafesi: 0 → r0 → … → rk → 0."""
    if not route:
        return 0.0
    total = dist[0][route[0]] + dist[route[-1]][0]
    for a, b in zip(route, route[1:]):
        total += dist[a][b]
    return total


def route_load(route: list[int], service: list[int]) -> int:
    return sum(service[i] for i in route)


def clarke_wright(
    n: int,
    dist: list[list[float]],
    service: list[int],
    capacity: int,
) -> list[list[int]]:
    """Paralel Clarke–Wright tasarruf sezgiseli (kapasite kısıtlı)."""
    routes: list[list[int]] = [[i] for i in range(1, n + 1)]
    loc = {i: r for r, route in enumerate(routes) for i in route}

    savings: list[tuple[float, int, int]] = []
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            s = dist[0][i] + dist[0][j] - dist[i][j]
            savings.append((s, i, j))
    savings.sort(reverse=True)

    for _, i, j in savings:
        ri, rj = loc[i], loc[j]
        if ri == rj:
            continue
        a, b = routes[ri], routes[rj]
        if i not in (a[0], a[-1]) or j not in (b[0], b[-1]):
            continue
        if route_load(a, service) + route_load(b, service) > capacity:
            continue
        merged = _join_endpoints(a, b, i, j)
        if merged is None:
            continue
        routes[ri] = merged
        routes[rj] = []
        for node in merged:
            loc[node] = ri

    return [r for r in routes if r]


def two_opt_route(route: list[int], dist: list[list[float]]) -> list[int]:
    """Tek rota üzerinde 2-opt (depo sabit)."""
    if len(route) < 4:
        return list(route)
    best = list(route)
    improved = True
    while improved:
        improved = False
        n = len(best)
        for i in range(n - 1):
            for j in range(i + 2, n):
                candidate = best[: i + 1] + best[i + 1 : j + 1][::-1] + best[j + 1 :]
                if route_distance(candidate, dist) + 1e-12 < route_distance(best, dist):
                    best = candidate
                    improved = True
                    break
            if improved:
                break
    return best


def pack_into_k(
    routes: list[list[int]],
    k: int,
    service: list[int],
    capacity: int,
    dist: list[list[float]],
) -> list[list[int]]:
    """Rotayı en fazla k araca sığdır; gerekirse tasarruflu birleştir."""
    current = [list(r) for r in routes if r]
    current.sort(key=lambda r: route_load(r, service))
    while len(current) > k:
        merged_any = False
        best = None
        for i in range(len(current)):
            for j in range(i + 1, len(current)):
                if route_load(current[i], service) + route_load(current[j], service) > capacity:
                    continue
                a, b = current[i], current[j]
                cand = two_opt_route(a + b, dist)
                extra = (
                    route_distance(cand, dist)
                    - route_distance(a, dist)
                    - route_distance(b, dist)
                )
                if best is None or extra < best[0]:
                    best = (extra, i, j, cand)
        if best is None:
            break
        _, i, j, cand = best
        current[i] = cand
        del current[j]
        merged_any = True
        if not merged_any:
            break
    current.sort(key=lambda r: route_distance(r, dist), reverse=True)
    if len(current) > k:
        leftover: list[int] = []
        kept = current[:k]
        for extra in current[k:]:
            leftover.extend(extra)
        for node in leftover:
            placed = False
            best_pos = None
            for ridx, route in enumerate(kept):
                if route_load(route, service) + service[node] > capacity:
                    continue
                for pos in range(len(route) + 1):
                    trial = route[:pos] + [node] + route[pos:]
                    delta = route_distance(trial, dist) - route_distance(route, dist)
                    if best_pos is None or delta < best_pos[0]:
                        best_pos = (delta, ridx, pos)
            if best_pos is not None:
                _, ridx, pos = best_pos
                kept[ridx] = kept[ridx][:pos] + [node] + kept[ridx][pos:]
                placed = True
            if not placed:
                logger.warning("CW paketleme: düğüm %d sığmadı.", node)
        current = kept
    while len(current) < k:
        current.append([])
    return current[:k]


def alns(
    seed_routes: list[list[int]],
    dist: list[list[float]],
    service: list[int],
    capacity: int,
    n_vehicles: int,
    iterations: int,
    rng: random.Random,
) -> list[list[int]]:
    """Adaptive Large Neighborhood Search (rastgele/worst/shaw + greedy/regret)."""
    current = [list(r) for r in seed_routes]
    while len(current) < n_vehicles:
        current.append([])
    current = current[:n_vehicles]
    best = deepcopy(current)
    best_cost = _solution_cost(best, dist)

    destroy_w = [1.0, 1.0, 1.0]
    repair_w = [1.0, 1.0]
    temperature = max(best_cost * 0.05, 1e-3)
    cooling = 0.995
    n_cust = sum(len(r) for r in current)
    if n_cust == 0:
        return current

    for _ in range(iterations):
        d_idx = _roulette(destroy_w, rng)
        r_idx = _roulette(repair_w, rng)
        q = max(1, min(n_cust, int(0.15 * n_cust) + rng.randint(0, max(1, n_cust // 5))))
        partial, removed = _destroy(current, q, d_idx, dist, rng)
        candidate = _repair(partial, removed, r_idx, dist, service, capacity, rng)
        cand_cost = _solution_cost(candidate, dist)
        cur_cost = _solution_cost(current, dist)
        accept = cand_cost < cur_cost or rng.random() < math.exp(
            -(cand_cost - cur_cost) / max(temperature, 1e-9)
        )
        score = 0.0
        if accept:
            current = candidate
            score = 1.0
            if cand_cost + 1e-12 < best_cost:
                best = deepcopy(candidate)
                best_cost = cand_cost
                score = 3.0
            elif cand_cost < cur_cost:
                score = 2.0
        destroy_w[d_idx] = 0.85 * destroy_w[d_idx] + 0.15 * (score + 0.1)
        repair_w[r_idx] = 0.85 * repair_w[r_idx] + 0.15 * (score + 0.1)
        temperature *= cooling

    return [two_opt_route(r, dist) for r in best]


def solve_ortools(
    n: int,
    dist: list[list[float]],
    service: list[int],
    n_vehicles: int,
    capacity: int,
    time_limit_s: int,
) -> list[list[int]] | None:
    """Google OR-Tools Routing (PATH_CHEAPEST_ARC + Guided Local Search)."""
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        logger.info("ortools yüklü değil — bu aday atlandı.")
        return None

    manager = pywrapcp.RoutingIndexManager(n + 1, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)
    scale = 1000

    def distance_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return int(dist[i][j] * scale)

    transit_idx = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    def demand_cb(from_index: int) -> int:
        return int(service[manager.IndexToNode(from_index)])

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,
        [capacity] * n_vehicles,
        True,
        "Capacity",
    )

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromSeconds(max(1, time_limit_s))

    solution = routing.SolveWithParameters(params)
    if solution is None:
        logger.warning("OR-Tools çözüm bulamadı.")
        return None

    routes: list[list[int]] = []
    for v in range(n_vehicles):
        index = routing.Start(v)
        route: list[int] = []
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                route.append(node)
            index = solution.Value(routing.NextVar(index))
        routes.append(route)
    return routes


def _join_endpoints(
    a: list[int], b: list[int], i: int, j: int
) -> list[int] | None:
    a, b = list(a), list(b)
    if a[-1] == i and b[0] == j:
        return a + b
    if a[-1] == i and b[-1] == j:
        return a + b[::-1]
    if a[0] == i and b[-1] == j:
        return b + a
    if a[0] == i and b[0] == j:
        return b[::-1] + a
    return None


def _destroy(
    routes: list[list[int]],
    q: int,
    kind: int,
    dist: list[list[float]],
    rng: random.Random,
) -> tuple[list[list[int]], list[int]]:
    customers = [c for r in routes for c in r]
    if not customers:
        return [list(r) for r in routes], []
    q = min(q, len(customers))
    if kind == 0:
        removed = rng.sample(customers, q)
    elif kind == 1:
        scored = []
        for ridx, route in enumerate(routes):
            for pos, node in enumerate(route):
                prev = 0 if pos == 0 else route[pos - 1]
                nxt = 0 if pos == len(route) - 1 else route[pos + 1]
                cost = dist[prev][node] + dist[node][nxt] - dist[prev][nxt]
                scored.append((cost, node))
        scored.sort(reverse=True)
        removed = [node for _, node in scored[:q]]
    else:
        seed = rng.choice(customers)
        related = sorted(customers, key=lambda c: dist[seed][c])
        removed = related[:q]
    removed_set = set(removed)
    partial = [[c for c in r if c not in removed_set] for r in routes]
    return partial, removed


def _repair(
    partial: list[list[int]],
    removed: list[int],
    kind: int,
    dist: list[list[float]],
    service: list[int],
    capacity: int,
    rng: random.Random,
) -> list[list[int]]:
    routes = [list(r) for r in partial]
    pending = list(removed)
    rng.shuffle(pending)
    if kind == 1:
        pending = _regret_order(pending, routes, dist, service, capacity)
    for node in pending:
        best = _best_insert(node, routes, dist, service, capacity)
        if best is None:
            continue
        _, ridx, pos = best
        routes[ridx].insert(pos, node)
    return routes


def _best_insert(
    node: int,
    routes: list[list[int]],
    dist: list[list[float]],
    service: list[int],
    capacity: int,
) -> tuple[float, int, int] | None:
    best = None
    for ridx, route in enumerate(routes):
        if route_load(route, service) + service[node] > capacity:
            continue
        for pos in range(len(route) + 1):
            prev = 0 if pos == 0 else route[pos - 1]
            nxt = 0 if pos == len(route) else route[pos]
            delta = dist[prev][node] + dist[node][nxt] - dist[prev][nxt]
            if best is None or delta < best[0]:
                best = (delta, ridx, pos)
    return best


def _regret_order(
    pending: list[int],
    routes: list[list[int]],
    dist: list[list[float]],
    service: list[int],
    capacity: int,
) -> list[int]:
    def regret(node: int) -> float:
        deltas: list[float] = []
        for route in routes:
            if route_load(route, service) + service[node] > capacity:
                continue
            best_here = math.inf
            for pos in range(len(route) + 1):
                prev = 0 if pos == 0 else route[pos - 1]
                nxt = 0 if pos == len(route) else route[pos]
                delta = dist[prev][node] + dist[node][nxt] - dist[prev][nxt]
                best_here = min(best_here, delta)
            if best_here < math.inf:
                deltas.append(best_here)
        deltas.sort()
        if len(deltas) >= 2:
            return deltas[1] - deltas[0]
        return deltas[0] if deltas else -math.inf

    return sorted(pending, key=regret, reverse=True)


def _solution_cost(routes: list[list[int]], dist: list[list[float]]) -> float:
    return sum(route_distance(r, dist) for r in routes)


def _roulette(weights: list[float], rng: random.Random) -> int:
    total = sum(weights)
    pick = rng.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if pick <= acc:
            return i
    return len(weights) - 1


def _pick_best(
    candidates: list[tuple[str, list[list[int]]]],
    dist: list[list[float]],
    service: list[int],
    capacity: int,
    n: int,
) -> tuple[str, list[list[int]]]:
    ranked: list[tuple[int, float, int, str, list[list[int]]]] = []
    for name, routes in candidates:
        feasible = all(route_load(r, service) <= capacity for r in routes)
        covered = {c for r in routes for c in r}
        coverage = len(covered)
        dist_km = _solution_cost(routes, dist)
        penalty = 0 if feasible and coverage == n else 1
        ranked.append((penalty, -coverage, dist_km, name, routes))
        logger.info(
            "Rota adayı %s: kapsama=%d/%d mesafe=%.4f km uygun=%s",
            name,
            coverage,
            n,
            dist_km,
            feasible,
        )
    ranked.sort()
    return ranked[0][3], ranked[0][4]


def _to_panel_routes(
    idx_routes: list[list[int]], panels: list[int], n_vehicles: int
) -> RouteDict:
    out: RouteDict = {k: [] for k in range(1, n_vehicles + 1)}
    for k, route in enumerate(idx_routes[:n_vehicles], start=1):
        out[k] = [panels[i - 1] for i in route]
    return out
