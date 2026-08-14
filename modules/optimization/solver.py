"""IE Modülü — Bakım Optimizasyonu ve Karar Destek Çözücüsü (MILP + CVRP).

Bu modül üç aşamada çalışır:

1. **Tekilleştirme:** ariza_verileri.json'daki çoklu tespitler panel başına
   en yüksek öncelikli tek hasara indirgenir.
2. **MILP Seçim:** Karma Tamsayılı Doğrusal Programlama ile her arızanın
   tamir edilip edilmemesine karar verilir. Hotspot ve mikro_catlak
   güvenlik gereği zorunlu (must_fix); tozlanma TL bazlı kararla
   filtrelenir. Toplam servis süresi 3 ekibin günlük mesaisini aşamaz.
3. **CVRP Atama:** Clarke–Wright + 2-opt, ALNS ve OR-Tools aynı örnekte
   koşar; en iyi kapsama/mesafe seçilir. Çıktı `gorev_cizelgesi.json`.

Parametreler IE Araştırma Raporu (dokumanlar/ie_arastirma_rapor.md ve
Parametre Tablosu.csv) kaynaklıdır.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pulp

from .routing import solve_cvrp_portfolio

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs")
FAULT_FILE = OUTPUTS_DIR / "ariza_verileri.json"
SCHEDULE_FILE = OUTPUTS_DIR / "gorev_cizelgesi.json"
LAYOUT_FILE = Path("modules") / "gui" / "assets" / "panel_layout.json"

# Hasar öncelik sıralaması (tekilleştirmede yüksek öncelik kazanır)
HASAR_PRIORITY: dict[str, int] = {"hotspot": 0, "mikro_catlak": 1, "tozlanma": 2}

# Güvenlik gereği MILP kararından bağımsız olarak zorunlu tamir edilen sınıflar
MUST_FIX_CLASSES: set[str] = {"hotspot", "mikro_catlak"}


# ─────────────────────────────────────────────────────────────────────────────
# IE Parametreleri (kaynak: dokumanlar/ie_arastirma_rapor.md)
# ─────────────────────────────────────────────────────────────────────────────


class Parameters:
    """IE araştırma raporundan gelen tüm sayısal sabitler."""

    # Fırsat maliyeti
    ENERGY_TL_PER_KWH: float = 2.0           # PTF ortalama
    PANEL_DAILY_KWH: float = 1.5             # ~300W panel * 5h verimli güneş
    HOTSPOT_LOSS_RATIO: float = 0.20
    CRACK_LOSS_RATIO: float = 0.05
    DUST_LOSS_RATIO_PER_MONTH: float = 0.10  # aylık → günlük: /30

    # Bakım maliyeti
    TECH_TL_PER_HOUR: float = 200.0
    HOTSPOT_DURATION_MIN: int = 45
    CRACK_DURATION_MIN: int = 60
    DUST_DURATION_MIN: int = 7
    DIODE_COST_TL: float = 100.0
    PANEL_COST_TL: float = 4500.0
    DIODE_PROB: float = 0.70                 # arızaların %70'i sadece diyot

    # Operasyonel kısıtlar
    DAILY_SHIFT_MIN: int = 480
    TEAM_COUNT: int = 3
    FUEL_TL_PER_KM: float = 3.0

    # Karar ufku — bakım yapılmaması durumunda fırsat maliyetinin
    # değerlendirileceği süre (gün).
    DECISION_HORIZON_DAYS: int = 30

    # CVRP çözücü zaman aşımı (saniye)
    CVRP_TIME_LIMIT_S: int = 60


# ─────────────────────────────────────────────────────────────────────────────
# Maliyet hesaplayıcı
# ─────────────────────────────────────────────────────────────────────────────


class CostCalculator:
    """Hasar tipine göre fırsat ve bakım maliyetlerini IE formülleriyle hesaplar."""

    @staticmethod
    def service_minutes(hasar: str) -> int:
        """Müdahale süresi (dakika)."""
        return {
            "hotspot": Parameters.HOTSPOT_DURATION_MIN,
            "mikro_catlak": Parameters.CRACK_DURATION_MIN,
            "tozlanma": Parameters.DUST_DURATION_MIN,
        }.get(hasar, 30)

    @staticmethod
    def daily_loss_kwh(hasar: str) -> float:
        """Arızanın panele yol açtığı günlük kWh kaybı."""
        if hasar == "hotspot":
            return Parameters.PANEL_DAILY_KWH * Parameters.HOTSPOT_LOSS_RATIO
        if hasar == "mikro_catlak":
            return Parameters.PANEL_DAILY_KWH * Parameters.CRACK_LOSS_RATIO
        if hasar == "tozlanma":
            return Parameters.PANEL_DAILY_KWH * (
                Parameters.DUST_LOSS_RATIO_PER_MONTH / 30.0
            )
        return 0.0

    @classmethod
    def opportunity_cost(
        cls, hasar: str, days: int = Parameters.DECISION_HORIZON_DAYS
    ) -> float:
        """Bakım yapılmazsa karar ufku boyunca üretim kaybının TL karşılığı."""
        return cls.daily_loss_kwh(hasar) * days * Parameters.ENERGY_TL_PER_KWH

    @classmethod
    def maintenance_cost(cls, hasar: str) -> float:
        """Tek seferlik bakım maliyeti: işçilik + beklenen malzeme."""
        labor_tl = (cls.service_minutes(hasar) / 60.0) * Parameters.TECH_TL_PER_HOUR
        if hasar == "tozlanma":
            material_tl = 0.0
        else:
            material_tl = (
                Parameters.DIODE_PROB * Parameters.DIODE_COST_TL
                + (1.0 - Parameters.DIODE_PROB) * Parameters.PANEL_COST_TL
            )
        return labor_tl + material_tl

    @staticmethod
    def priority(hasar: str) -> str:
        """GUI etiket önceliği."""
        if hasar == "hotspot":
            return "kritik"
        if hasar == "mikro_catlak":
            return "orta"
        return "düşük"


# ─────────────────────────────────────────────────────────────────────────────
# Bakım Çizelgeleyici
# ─────────────────────────────────────────────────────────────────────────────


class MaintenanceScheduler:
    """MILP seçim + CVRP atama ile gün bazlı görev çizelgesi üretir.

    Args:
        fault_file: Okunacak ariza_verileri.json yolu (None ise varsayılan).
        schedule_file: Yazılacak gorev_cizelgesi.json yolu (None ise varsayılan).
    """

    def __init__(
        self,
        fault_file: Path | None = None,
        schedule_file: Path | None = None,
    ) -> None:
        self.fault_file = Path(fault_file) if fault_file else FAULT_FILE
        self.schedule_file = Path(schedule_file) if schedule_file else SCHEDULE_FILE
        self.layout = self._load_layout()
        origin = self.layout.get("origin_gps", [38.4200, 27.1400])
        self.depot_gps: tuple[float, float] = (float(origin[0]), float(origin[1]))
        self._last_routing_solver: str = "none"

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def solve_and_generate_schedule(self) -> dict | None:
        """Tüm optimizasyon sürecini yürütür ve çizelge dosyasını üretir."""
        faults = self._load_faults()
        if faults is None:
            logger.info("ariza_verileri.json okunamadı — çizelge üretilmedi.")
            return None

        if not faults:
            logger.info("Arıza verisi boş — boş çizelge yazıldı.")
            schedule = self._empty_schedule("Arıza tespiti yok.")
            self._write_schedule(schedule)
            return schedule

        # 1. Tekilleştir: panel başına en kritik hasar
        panel_hasar = self._dedupe_per_panel(faults)
        logger.info("Tekilleştirme sonrası %d benzersiz panel arızası.", len(panel_hasar))

        # 2. MILP seçim
        selected = self._select_tasks(panel_hasar)
        if not selected:
            logger.info("MILP: hiç arıza ekonomik veya kapasite uygun değil.")
            schedule = self._empty_schedule(
                "MILP: arızaların tamiri ekonomik değil — bakım ertelendi."
            )
            self._write_schedule(schedule)
            return schedule

        logger.info("MILP %d arızanın bu hafta tamirine karar verdi.", len(selected))

        # 3. CVRP atama
        routes = self._solve_cvrp(selected, panel_hasar)

        # 4. JSON çıktısı
        schedule = self._build_schedule(selected, panel_hasar, routes)
        self._write_schedule(schedule)
        return schedule

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Veri yükleme & tekilleştirme
    # ──────────────────────────────────────────────────────────────────────────

    def _load_faults(self) -> list[dict] | None:
        if not self.fault_file.exists():
            return None
        try:
            with open(self.fault_file, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("ariza_verileri.json okunamadı: %s", exc)
            return None

    def _load_layout(self) -> dict:
        if not LAYOUT_FILE.exists():
            logger.warning("panel_layout.json bulunamadı: %s", LAYOUT_FILE)
            return {}
        with open(LAYOUT_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _dedupe_per_panel(self, faults: list[dict]) -> dict[int, str]:
        """Aynı panelde birden fazla tespit varsa en kritik hasarı tutar."""
        best: dict[int, str] = {}
        for f in faults:
            pid = int(f.get("panel_id", -1))
            hasar = f.get("hasar")
            if pid < 0 or hasar not in HASAR_PRIORITY:
                continue
            current = best.get(pid)
            if current is None or HASAR_PRIORITY[hasar] < HASAR_PRIORITY[current]:
                best[pid] = hasar
        return best

    # ──────────────────────────────────────────────────────────────────────────
    # 2. MILP seçim
    # ──────────────────────────────────────────────────────────────────────────

    def _select_tasks(self, panel_hasar: dict[int, str]) -> list[int]:
        """MILP: panel başına tamir/erteleme ikili kararı.

        Amaç fonksiyonu (her panel için):
            x_i * maintenance_cost + (1 - x_i) * opportunity_cost
            = x_i * (maintenance_cost - opportunity_cost) + sabit

        x_i = 1 sadece (must_fix) veya (opportunity > maintenance) ise tercih
        edilir. Toplam servis süresi 3 ekibin günlük kapasitesini aşamaz.
        """
        if not panel_hasar:
            return []

        prob = pulp.LpProblem("MaintenanceSelection", pulp.LpMinimize)

        panel_ids = sorted(panel_hasar.keys())
        x = {pid: pulp.LpVariable(f"x_{pid}", cat=pulp.LpBinary) for pid in panel_ids}

        # Amaç: must_fix olan sınıflara (hotspot ve mikro_catlak) büyük bir teşvik (negative penalty)
        # ekleyerek kapasite elverdiği ölçüde çözücünün bunları seçmesini zorluyoruz.
        # Hotspot yangın riski taşıdığı için mikro_catlak'tan daha yüksek öncelik teşviki alır.
        objective = []
        for pid in panel_ids:
            hasar = panel_hasar[pid]
            mc = CostCalculator.maintenance_cost(hasar)
            oc = CostCalculator.opportunity_cost(hasar)
            coeff = mc - oc
            
            if hasar == "hotspot":
                coeff -= 1000000.0
            elif hasar == "mikro_catlak":
                coeff -= 500000.0
                
            objective.append(x[pid] * coeff + oc)
        prob += pulp.lpSum(objective)

        # Kapasite kısıtı: Σ servis süresi ≤ ekip sayısı × günlük mesai
        capacity_min = Parameters.TEAM_COUNT * Parameters.DAILY_SHIFT_MIN
        prob += (
            pulp.lpSum(
                x[pid] * CostCalculator.service_minutes(panel_hasar[pid])
                for pid in panel_ids
            )
            <= capacity_min,
            "daily_capacity",
        )

        try:
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            status = pulp.LpStatus[prob.status]
        except Exception as exc:
            logger.warning("MILP çözücü çalıştırılamadı (%s) — sezgisel seçime geçiliyor.", exc)
            selected_heur = []
            total_time = 0
            for hasar_type in ["hotspot", "mikro_catlak"]:
                for pid, hasar in sorted(panel_hasar.items()):
                    if hasar == hasar_type:
                        s = CostCalculator.service_minutes(hasar)
                        if total_time + s <= capacity_min:
                            selected_heur.append(pid)
                            total_time += s
            return selected_heur

        if status != "Optimal":
            logger.warning(
                "MILP optimal değil (status=%s) — boş seçim döndürülüyor.",
                status,
            )
            return []

        return [pid for pid in panel_ids if pulp.value(x[pid]) and pulp.value(x[pid]) > 0.5]

    # ──────────────────────────────────────────────────────────────────────────
    # 3. CVRP atama (3 araç + MTZ)
    # ──────────────────────────────────────────────────────────────────────────

    def _solve_cvrp(
        self, panels: list[int], panel_hasar: dict[int, str]
    ) -> dict[int, list[int]]:
        """3 araç paralel rotalama. Returns: {team_id: [panel_id, ...]}.

        Adaylar: Clarke–Wright + 2-opt, ALNS, OR-Tools (varsa).
        En yüksek kapsama, eşitlikte en kısa mesafe seçilir.
        """
        K = Parameters.TEAM_COUNT
        empty_routes: dict[int, list[int]] = {k: [] for k in range(1, K + 1)}

        if not panels:
            self._last_routing_solver = "empty"
            return empty_routes

        locs: list[tuple[float, float]] = [self.depot_gps] + [
            self._panel_gps(p) for p in panels
        ]
        service: list[int] = [0] + [
            CostCalculator.service_minutes(panel_hasar[p]) for p in panels
        ]
        dist = self._distance_matrix_km(locs)
        n = len(panels)
        ot_limit = 2 if n <= 12 else (8 if n <= 40 else min(30, Parameters.CVRP_TIME_LIMIT_S))

        routes, name = solve_cvrp_portfolio(
            panels,
            dist,
            service,
            K,
            Parameters.DAILY_SHIFT_MIN,
            time_limit_s=ot_limit,
        )
        covered = {pid for seq in routes.values() for pid in seq}
        missing = set(panels) - covered
        if missing:
            logger.warning(
                "Rota portföyü %d paneli kaçırdı (%s) — NN fallback.",
                len(missing),
                name,
            )
            routes = self._cvrp_fallback(panels, panel_hasar)
            name = "nearest_neighbor"
        self._last_routing_solver = name
        logger.info("Seçilen rota çözücü: %s", name)
        return routes

    def _cvrp_fallback(
        self, panels: list[int], panel_hasar: dict[int, str]
    ) -> dict[int, list[int]]:
        """En yakın komşu ile sırayla aracı doldur (capacity-aware NN)."""
        K = Parameters.TEAM_COUNT
        capacity = Parameters.DAILY_SHIFT_MIN
        routes: dict[int, list[int]] = {k: [] for k in range(1, K + 1)}
        loads: dict[int, int] = {k: 0 for k in range(1, K + 1)}

        unvisited = list(panels)
        for k in range(1, K + 1):
            current_pos = self.depot_gps
            while unvisited:
                # En yakın & sığacak panel
                best_pid = None
                best_d = math.inf
                for pid in unvisited:
                    s = CostCalculator.service_minutes(panel_hasar[pid])
                    if loads[k] + s > capacity:
                        continue
                    pos = self._panel_gps(pid)
                    d = self._haversine_km(current_pos, pos)
                    if d < best_d:
                        best_d = d
                        best_pid = pid
                if best_pid is None:
                    break
                routes[k].append(best_pid)
                loads[k] += CostCalculator.service_minutes(panel_hasar[best_pid])
                current_pos = self._panel_gps(best_pid)
                unvisited.remove(best_pid)

        if unvisited:
            logger.warning(
                "Fallback: %d panel kapasite yetersizliği nedeniyle atanamadı.",
                len(unvisited),
            )
        return routes

    # ──────────────────────────────────────────────────────────────────────────
    # 4. JSON çıktısı
    # ──────────────────────────────────────────────────────────────────────────

    def _build_schedule(
        self,
        selected: list[int],
        panel_hasar: dict[int, str],
        routes: dict[int, list[int]],
    ) -> dict:
        """gorev_cizelgesi.json yapısını oluşturur."""
        sched_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        # Panel → ekip eşleştirmesi
        panel_team: dict[int, int] = {}
        for team_id, panel_list in routes.items():
            for pid in panel_list:
                panel_team[pid] = team_id

        tasks: list[dict] = []
        total_cost = 0.0
        total_service = 0
        for pid in selected:
            hasar = panel_hasar[pid]
            cost = CostCalculator.maintenance_cost(hasar)
            service = CostCalculator.service_minutes(hasar)
            total_cost += cost
            total_service += service
            tasks.append(
                {
                    "panel_id": pid,
                    "hasar": hasar,
                    "priority": CostCalculator.priority(hasar),
                    "estimated_cost": round(cost, 2),
                    "service_min": service,
                    "team_id": panel_team.get(pid, 0),
                    "scheduled_date": sched_date,
                }
            )

        # Rota mesafesi (depo dahil tur)
        total_km = 0.0
        for panel_list in routes.values():
            if not panel_list:
                continue
            current = self.depot_gps
            for pid in panel_list:
                nxt = self._panel_gps(pid)
                total_km += self._haversine_km(current, nxt)
                current = nxt
            total_km += self._haversine_km(current, self.depot_gps)
        fuel_cost = total_km * Parameters.FUEL_TL_PER_KM

        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "total_cost_tl": round(total_cost + fuel_cost, 2),
            "total_distance_km": round(total_km, 3),
            "total_service_time_min": total_service,
            "team_count": Parameters.TEAM_COUNT,
            "tasks": tasks,
            "routes": {str(k): v for k, v in routes.items()},
            "routing_solver": self._last_routing_solver,
        }

    def _empty_schedule(self, reason: str) -> dict:
        """Hiç görev seçilmediğinde yazılan boş çizelge."""
        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "total_cost_tl": 0.0,
            "total_distance_km": 0.0,
            "total_service_time_min": 0,
            "team_count": Parameters.TEAM_COUNT,
            "tasks": [],
            "routes": {str(k): [] for k in range(1, Parameters.TEAM_COUNT + 1)},
            "note": reason,
        }

    def _write_schedule(self, schedule: dict) -> None:
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.schedule_file, "w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
        logger.info("Çizelge kaydedildi: %s", self.schedule_file)

    # ──────────────────────────────────────────────────────────────────────────
    # Yardımcılar
    # ──────────────────────────────────────────────────────────────────────────

    def _panel_gps(self, panel_id: int) -> tuple[float, float]:
        """Panel ID → (lat, lon)."""
        for p in self.layout.get("panels", []):
            if int(p["panel_id"]) == int(panel_id):
                return (float(p["gps"][0]), float(p["gps"][1]))
        return self.depot_gps

    def _distance_matrix_km(
        self, locs: list[tuple[float, float]]
    ) -> list[list[float]]:
        n = len(locs)
        d = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    d[i][j] = self._haversine_km(locs[i], locs[j])
        return d

    @staticmethod
    def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
        """İki GPS noktası arasındaki büyük daire mesafesi (km)."""
        lat1, lon1 = math.radians(a[0]), math.radians(a[1])
        lat2, lon2 = math.radians(b[0]), math.radians(b[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * 6371.0 * math.asin(math.sqrt(h))


# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scheduler = MaintenanceScheduler()
    scheduler.solve_and_generate_schedule()
