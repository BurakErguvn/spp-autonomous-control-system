"""IE Modülü — Bakım Optimizasyon ve Karar Destek Çözücüsü (MILP + VRP).

Bu modül, arıza verilerini okur, maliyetleri hesaplar, MILP modeli ile
hangi arızalara öncelik verileceğini belirler ve en yakın komşu (NN)
algoritması ile VRP rotası oluşturur. Sonucu gorev_cizelgesi.json'a yazar.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pulp

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs")
FAULT_FILE = OUTPUTS_DIR / "ariza_verileri.json"
SCHEDULE_FILE = OUTPUTS_DIR / "gorev_cizelgesi.json"
LAYOUT_FILE = Path("modules") / "gui" / "assets" / "panel_layout.json"


class CostCalculator:
    """Arıza tiplerine göre fırsat ve bakım maliyetlerini hesaplar."""
    
    ENERGY_PRICE = 3.5  # TL/kWh
    TECHNICIAN_COST = 500.0  # Sabit araç/işçilik TL
    
    # Günlük kWh kayıpları
    LOSS_KWH = {
        "hotspot": 15.0,
        "mikro_catlak": 5.0,
        "tozlanma": 2.0
    }
    
    @classmethod
    def get_opportunity_cost(cls, hasar_tipi: str, days: int = 30) -> float:
        """Belirtilen gün boyunca arızanın tamir edilmemesinin maliyeti."""
        kwh_loss = cls.LOSS_KWH.get(hasar_tipi, 1.0)
        return kwh_loss * days * cls.ENERGY_PRICE
        
    @classmethod
    def get_maintenance_cost(cls, hasar_tipi: str) -> float:
        """Arızanın tamir maliyeti (Basitçe sabit alınmıştır)."""
        # Gelecekte hasar tipine göre değişen malzeme maliyeti eklenebilir.
        return cls.TECHNICIAN_COST

    @classmethod
    def get_priority(cls, hasar_tipi: str) -> str:
        """GUI için öncelik belirler."""
        if hasar_tipi == "hotspot":
            return "kritik"
        elif hasar_tipi == "mikro_catlak":
            return "orta"
        return "düşük"


class MaintenanceScheduler:
    """MILP ve VRP çözücüsünü birleştirip görev çizelgesi üretir."""
    
    def __init__(self, max_tasks_per_day: int = 10):
        self.max_tasks_per_day = max_tasks_per_day
        self.layout_data = self._load_layout()
        
    def _load_layout(self) -> dict:
        if not LAYOUT_FILE.exists():
            logger.warning("panel_layout.json bulunamadı!")
            return {}
        with open(LAYOUT_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _get_panel_gps(self, panel_id: int) -> tuple[float, float]:
        """Panel ID'sine göre GPS koordinatlarını döner."""
        panels = self.layout_data.get("panels", [])
        for p in panels:
            if p.get("panel_id") == panel_id:
                return (p["gps"][0], p["gps"][1])
        # Bulunamazsa origin
        origin = self.layout_data.get("origin_gps", [38.4200, 27.1400])
        return (origin[0], origin[1])

    def solve_and_generate_schedule(self) -> dict | None:
        """Tüm optimizasyon sürecini yürütür ve çizelge oluşturur."""
        # 1. Veriyi oku
        if not FAULT_FILE.exists():
            logger.info("ariza_verileri.json bulunamadı. Bekleniyor...")
            return None
            
        with open(FAULT_FILE, encoding="utf-8") as f:
            faults = json.load(f)
            
        if not faults:
            logger.info("arıza verisi boş.")
            return None
            
        # 2. MILP Optimizasyonu
        selected_faults = self._solve_milp(faults)
        if not selected_faults:
            logger.info("Bakım yapılmasına gerek duyulan veya kapasiteye uyan arıza yok.")
            return None
            
        # 3. VRP (En Yakın Komşu Rotalaması)
        route = self._solve_vrp(selected_faults)
        
        # 4. JSON Çıktısını Hazırla
        schedule = self._build_schedule_json(selected_faults, route)
        
        # 5. Dosyaya Yaz
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
            
        logger.info("Optimizasyon tamamlandı. Çizelge kaydedildi: %s", SCHEDULE_FILE)
        return schedule

    def _solve_milp(self, faults: list[dict]) -> list[dict]:
        """MILP modelini kullanarak en uygun görevleri seçer."""
        # Problemi Tanımla (Minimizasyon)
        prob = pulp.LpProblem("MaintenanceOptimization", pulp.LpMinimize)
        
        # Değişkenler: x[i] 1 ise i. arıza tamir edilecek, 0 ise ertelenecek
        x_vars = {}
        for i, fault in enumerate(faults):
            x_vars[i] = pulp.LpVariable(f"x_{i}", cat=pulp.LpBinary)
            
        # Amaç Fonksiyonu: Min sum(x_i * M_cost + (1 - x_i) * Opp_cost)
        objective_terms = []
        for i, fault in enumerate(faults):
            m_cost = CostCalculator.get_maintenance_cost(fault["hasar"])
            opp_cost = CostCalculator.get_opportunity_cost(fault["hasar"], days=30)
            # x_i * m_cost + (1 - x_i) * opp_cost = x_i * (m_cost - opp_cost) + opp_cost
            objective_terms.append(x_vars[i] * (m_cost - opp_cost) + opp_cost)
            
        prob += pulp.lpSum(objective_terms), "Total_Cost"
        
        # Kısıtlar: Maksimum günlük görev sayısı
        prob += pulp.lpSum([x_vars[i] for i in range(len(faults))]) <= self.max_tasks_per_day, "Max_Tasks"
        
        # Çöz
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        # Seçilenleri filtrele
        selected_faults = []
        for i, fault in enumerate(faults):
            if pulp.value(x_vars[i]) == 1.0:
                selected_faults.append(fault)
                
        return selected_faults

    def _solve_vrp(self, selected_faults: list[dict]) -> list[int]:
        """Basit En Yakın Komşu (TSP/VRP) algoritmasıyla rotayı hesaplar."""
        if not selected_faults:
            return []
            
        # Panel ID'lerini ve koordinatlarını al
        unvisited = [f["panel_id"] for f in selected_faults]
        
        # Aynı panele birden fazla arıza düşmüş olabilir, tekilleştir
        unvisited = list(set(unvisited))
        
        origin = self.layout_data.get("origin_gps", [38.4200, 27.1400])
        current_pos = (origin[0], origin[1])
        route = []
        
        while unvisited:
            best_node = None
            min_dist = float("inf")
            
            for node in unvisited:
                pos = self._get_panel_gps(node)
                # Basit Öklid uzaklığı (simülasyon için yeterlidir)
                dist = math.hypot(pos[0] - current_pos[0], pos[1] - current_pos[1])
                if dist < min_dist:
                    min_dist = dist
                    best_node = node
                    
            route.append(best_node)
            current_pos = self._get_panel_gps(best_node)
            unvisited.remove(best_node)
            
        return route

    def _build_schedule_json(self, selected_faults: list[dict], route: list[int]) -> dict:
        """GUI modülü için gorev_cizelgesi.json veri sözlüğünü oluşturur."""
        tasks = []
        total_cost = 0.0
        
        tomorrow = datetime.now() + timedelta(days=1)
        sched_date = tomorrow.strftime("%Y-%m-%d")
        
        for f in selected_faults:
            hasar = f["hasar"]
            cost = CostCalculator.get_maintenance_cost(hasar)
            total_cost += cost
            
            tasks.append({
                "panel_id": f["panel_id"],
                "hasar": hasar,
                "priority": CostCalculator.get_priority(hasar),
                "estimated_cost": cost,
                "scheduled_date": sched_date
            })
            
        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "total_cost": total_cost,
            "tasks": tasks,
            "route": route
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = MaintenanceScheduler()
    scheduler.solve_and_generate_schedule()
