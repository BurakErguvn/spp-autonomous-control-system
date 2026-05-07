"""IE Optimizasyon Modülü birim testleri.

Çalıştırma:
    pytest tests/test_optimization.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from modules.optimization import CostCalculator, MaintenanceScheduler, Parameters

# ── Yardımcılar ──────────────────────────────────────────────────────────────


def _make_layout() -> dict:
    """5 panellik küçük test layout'u (depo orijinde)."""
    return {
        "panel_count": 5,
        "origin_gps": [38.4200, 27.1400],
        "panels": [
            {"panel_id": 0, "row": 0, "col": 0, "gps": [38.4200, 27.1400]},
            {"panel_id": 1, "row": 0, "col": 1, "gps": [38.4200, 27.1403]},
            {"panel_id": 2, "row": 0, "col": 2, "gps": [38.4200, 27.1406]},
            {"panel_id": 3, "row": 0, "col": 3, "gps": [38.4200, 27.1409]},
            {"panel_id": 4, "row": 0, "col": 4, "gps": [38.4200, 27.1412]},
        ],
    }


def _make_fault(panel_id: int, hasar: str, ts: str = "2026-04-25T10:00:00+00:00") -> dict:
    return {
        "timestamp": ts,
        "panel_id": panel_id,
        "gps": [38.42, 27.14 + 0.0003 * panel_id],
        "hasar": hasar,
        "koordinat": [100, 100, 50, 50],
        "guven_skoru": 0.85,
    }


@pytest.fixture
def temp_workspace():
    """Geçici çalışma dizini + 5 panellik layout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        layout_dir = root / "modules" / "gui" / "assets"
        layout_dir.mkdir(parents=True)
        (layout_dir / "panel_layout.json").write_text(
            json.dumps(_make_layout()), encoding="utf-8"
        )

        outputs_dir = root / "outputs"
        outputs_dir.mkdir()

        yield {
            "root": root,
            "fault_file": outputs_dir / "ariza_verileri.json",
            "schedule_file": outputs_dir / "gorev_cizelgesi.json",
            "layout_file": layout_dir / "panel_layout.json",
        }


# ─────────────────────────────────────────────────────────────────────────────
# CostCalculator
# ─────────────────────────────────────────────────────────────────────────────


class TestCostCalculator:
    """Maliyet formülleri IE araştırma raporuyla uyumlu olmalı."""

    def test_service_minutes(self):
        assert CostCalculator.service_minutes("hotspot") == Parameters.HOTSPOT_DURATION_MIN
        assert CostCalculator.service_minutes("mikro_catlak") == Parameters.CRACK_DURATION_MIN
        assert CostCalculator.service_minutes("tozlanma") == Parameters.DUST_DURATION_MIN

    def test_hotspot_maintenance_formula(self):
        """Hotspot bakım = işçilik + (0.7 × diyot + 0.3 × panel)."""
        expected_labor = (45 / 60.0) * 200.0
        expected_material = 0.7 * 100.0 + 0.3 * 4500.0
        expected = expected_labor + expected_material
        assert CostCalculator.maintenance_cost("hotspot") == pytest.approx(expected, abs=0.01)

    def test_dust_maintenance_no_material(self):
        """Tozlanma bakımında yalnızca işçilik vardır."""
        expected = (7 / 60.0) * 200.0
        assert CostCalculator.maintenance_cost("tozlanma") == pytest.approx(expected, abs=0.01)
        assert CostCalculator.maintenance_cost("tozlanma") < 30.0

    def test_opportunity_cost_positive(self):
        """Bütün hasar tipleri için fırsat maliyeti > 0."""
        for h in ["hotspot", "mikro_catlak", "tozlanma"]:
            assert CostCalculator.opportunity_cost(h) > 0

    def test_opportunity_cost_scales_with_days(self):
        """Daha uzun karar ufkunda fırsat maliyeti orantılı artmalı."""
        c30 = CostCalculator.opportunity_cost("hotspot", days=30)
        c90 = CostCalculator.opportunity_cost("hotspot", days=90)
        assert c90 == pytest.approx(c30 * 3.0, rel=0.001)

    def test_priority_labels(self):
        assert CostCalculator.priority("hotspot") == "kritik"
        assert CostCalculator.priority("mikro_catlak") == "orta"
        assert CostCalculator.priority("tozlanma") == "düşük"


# ─────────────────────────────────────────────────────────────────────────────
# MaintenanceScheduler — MILP seçim
# ─────────────────────────────────────────────────────────────────────────────


class TestMilpSelection:
    """MILP seçim mantığı: must_fix + ekonomik karar."""

    def test_empty_faults_writes_empty_schedule(self, temp_workspace):
        """Arıza listesi boşsa boş çizelge yazılmalı."""
        ws = temp_workspace
        ws["fault_file"].write_text("[]", encoding="utf-8")
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        # Layout dosyası başka yerdeyse hata atlamak için _load_layout monkey-patch:
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None
        assert result["tasks"] == []

    def test_dust_only_skips_all(self, temp_workspace):
        """Sadece tozlanma → MILP ekonomik bulmamalı, boş çizelge."""
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(p, "tozlanma") for p in [1, 2]]),
            encoding="utf-8",
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None
        assert result["tasks"] == []
        assert "ertelendi" in result.get("note", "").lower()

    def test_hotspot_must_fix(self, temp_workspace):
        """Hotspot ekonomik olmasa bile zorunlu tamir edilmeli."""
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(0, "hotspot"), _make_fault(4, "hotspot")]),
            encoding="utf-8",
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None
        assert len(result["tasks"]) == 2
        assert all(t["hasar"] == "hotspot" for t in result["tasks"])

    def test_dedupe_keeps_highest_priority(self, temp_workspace):
        """Aynı panelde tozlanma + hotspot varsa hotspot tutulmalı."""
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(2, "tozlanma"), _make_fault(2, "hotspot")]),
            encoding="utf-8",
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["panel_id"] == 2
        assert result["tasks"][0]["hasar"] == "hotspot"


# ─────────────────────────────────────────────────────────────────────────────
# MaintenanceScheduler — CVRP atama
# ─────────────────────────────────────────────────────────────────────────────


class TestCvrpAssignment:
    """CVRP rotalama: 3 ekip, kapasite kısıtı, MTZ subtour eliminasyonu."""

    def test_routes_have_three_teams(self, temp_workspace):
        """Çıktı routes dict'i 3 ekip anahtarı içermeli."""
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(p, "hotspot") for p in [0, 2, 4]]),
            encoding="utf-8",
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None
        assert set(result["routes"].keys()) == {"1", "2", "3"}

    def test_each_panel_visited_once(self, temp_workspace):
        """Her seçilen panel toplam rotalarda tam bir kez görünmeli."""
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(p, "mikro_catlak") for p in [0, 1, 2, 3, 4]]),
            encoding="utf-8",
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None

        all_visited: list[int] = []
        for panel_list in result["routes"].values():
            all_visited.extend(panel_list)

        assert sorted(all_visited) == [0, 1, 2, 3, 4]
        assert len(all_visited) == len(set(all_visited))  # tekrar yok

    def test_team_capacity_respected(self, temp_workspace):
        """Hiçbir ekibin toplam servisi günlük mesayı aşmamalı."""
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(p, "hotspot") for p in [0, 1, 2, 3, 4]]),
            encoding="utf-8",
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert result is not None

        team_loads: dict[str, int] = {k: 0 for k in result["routes"]}
        for task in result["tasks"]:
            team_loads[str(task["team_id"])] += task["service_min"]

        for team_id, load in team_loads.items():
            assert load <= Parameters.DAILY_SHIFT_MIN, (
                f"Ekip {team_id} kapasite aşımı: {load} > {Parameters.DAILY_SHIFT_MIN}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# JSON şeması
# ─────────────────────────────────────────────────────────────────────────────


class TestScheduleJsonSchema:
    """Yeni gorev_cizelgesi.json zorunlu alanlarını içermeli."""

    def test_required_top_level_keys(self, temp_workspace):
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(0, "hotspot")]), encoding="utf-8"
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        for key in [
            "generated_at",
            "total_cost_tl",
            "total_distance_km",
            "total_service_time_min",
            "team_count",
            "tasks",
            "routes",
        ]:
            assert key in result, f"Eksik anahtar: {key}"

    def test_task_has_team_and_service(self, temp_workspace):
        ws = temp_workspace
        ws["fault_file"].write_text(
            json.dumps([_make_fault(1, "hotspot")]), encoding="utf-8"
        )
        scheduler = MaintenanceScheduler(
            fault_file=ws["fault_file"], schedule_file=ws["schedule_file"]
        )
        scheduler.layout = json.loads(ws["layout_file"].read_text(encoding="utf-8"))

        result = scheduler.solve_and_generate_schedule()
        assert len(result["tasks"]) == 1
        task = result["tasks"][0]
        for key in ["panel_id", "hasar", "priority", "estimated_cost", "service_min", "team_id"]:
            assert key in task
