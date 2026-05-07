"""Üç senaryoyu (A, B, C) sırayla koşar ve çıktılarını ayrı dizinlere yazar.

İP 7 gereksinimi: Her senaryonun ariza_verileri.json + gorev_cizelgesi.json
çıktıları `outputs/scenarios/{A,B,C}/` altına kaydedilir. Bu çıktılar
`scripts/comparison_report.py` tarafından geleneksel yöntemle karşılaştırma
için okunur.

İki çalışma modu:

* **Tam pipeline (varsayılan):** main.run_pipeline → DataFeeder + YOLO26 +
  Optimizasyon. Ultralytics + Torch + models/best.pt gerekir.
* **--no-inference:** Sentetik fault verisi (senaryonun hedef sınıfı +
  panellerinden türetilir) → yalnızca Optimizasyon. YZ ortamı kurulmadan
  IE modülünün kabul testi için kullanılır.

Kullanım:
    python scripts/run_scenarios.py
    python scripts/run_scenarios.py --no-inference  # YOLO olmadan
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_feeder.scenarios import SCENARIOS, Scenario  # noqa: E402
from modules.optimization import MaintenanceScheduler  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scenario_runner")

DEFAULT_MODEL = Path("models") / "best.pt"
SCENARIOS_DIR = Path("outputs") / "scenarios"
LAYOUT_FILE = Path("modules") / "gui" / "assets" / "panel_layout.json"

CLASS_TO_HASAR = {0: "hotspot", 1: "mikro_catlak", 2: "tozlanma"}


def synthesize_faults(scenario: Scenario, layout: dict) -> list[dict]:
    """Senaryonun panelleri ve hedef sınıfından sentetik ariza_verileri üretir."""
    panel_lookup = {int(p["panel_id"]): p for p in layout.get("panels", [])}
    hasar = CLASS_TO_HASAR.get(scenario.target_class, "hotspot")
    timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    faults: list[dict] = []
    for pid in scenario.panel_ids:
        panel = panel_lookup.get(pid)
        if panel is None:
            continue
        faults.append(
            {
                "timestamp": timestamp,
                "panel_id": pid,
                "gps": [float(panel["gps"][0]), float(panel["gps"][1])],
                "hasar": hasar,
                "koordinat": [100, 100, 80, 60],
                "guven_skoru": 0.85,
            }
        )
    return faults


def run_with_inference(model_path: Path) -> dict[str, dict]:
    """Tam pipeline (YOLO inference dahil)."""
    from main import run_pipeline  # noqa: E402

    summary: dict[str, dict] = {}
    for scenario in ("A", "B", "C"):
        out_dir = SCENARIOS_DIR / scenario
        logger.info("──────  Senaryo %s (tam pipeline) → %s", scenario, out_dir)
        schedule = run_pipeline(
            model_path=model_path,
            scenario=scenario,
            no_gui=True,
            output_dir=out_dir,
        )
        if schedule is None:
            logger.warning("Senaryo %s sonuç üretmedi.", scenario)
            continue
        summary[scenario] = _summary_row(schedule)
    return summary


def run_without_inference() -> dict[str, dict]:
    """Optimizasyon-only mod: sentetik ariza_verileri.json üret + scheduler."""
    if not LAYOUT_FILE.exists():
        logger.error("panel_layout.json bulunamadı: %s", LAYOUT_FILE)
        sys.exit(1)
    layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

    summary: dict[str, dict] = {}
    for scenario_id, scen in SCENARIOS.items():
        out_dir = SCENARIOS_DIR / scenario_id
        out_dir.mkdir(parents=True, exist_ok=True)
        fault_path = out_dir / "ariza_verileri.json"
        sched_path = out_dir / "gorev_cizelgesi.json"

        faults = synthesize_faults(scen, layout)
        with open(fault_path, "w", encoding="utf-8") as f:
            json.dump(faults, f, ensure_ascii=False, indent=2)
        logger.info(
            "Senaryo %s sentetik ariza_verileri.json yazıldı (%d arıza).",
            scenario_id,
            len(faults),
        )

        scheduler = MaintenanceScheduler(
            fault_file=fault_path, schedule_file=sched_path
        )
        schedule = scheduler.solve_and_generate_schedule()
        if schedule is None:
            logger.warning("Senaryo %s scheduler çalıştırılamadı.", scenario_id)
            continue
        summary[scenario_id] = _summary_row(schedule)
    return summary


def _summary_row(schedule: dict) -> dict:
    return {
        "task_count": len(schedule.get("tasks", [])),
        "total_cost_tl": schedule.get("total_cost_tl", 0.0),
        "total_distance_km": schedule.get("total_distance_km", 0.0),
        "total_service_min": schedule.get("total_service_time_min", 0),
        "note": schedule.get("note"),
    }


def parse_args() -> argparse.Namespace:
    """CLI argümanları."""
    parser = argparse.ArgumentParser(description="3 senaryoyu sırayla koşar.")
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help=f"YOLO26 ağırlık dosyası (varsayılan: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--no-inference",
        action="store_true",
        help="YOLO çıkarımı yapmadan senaryolar için sentetik ariza_verileri üret.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

    if args.no_inference:
        summary = run_without_inference()
    else:
        summary = run_with_inference(args.model)

    logger.info("──────  Senaryo özeti")
    for scenario, data in summary.items():
        logger.info(
            "  Senaryo %s: %d görev | %.0f TL | %.2f km | %d dk%s",
            scenario,
            data["task_count"],
            data["total_cost_tl"],
            data["total_distance_km"],
            data["total_service_min"],
            f" — {data['note']}" if data["note"] else "",
        )
