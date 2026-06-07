"""GES Otonom Termal Denetim & Bakım Optimizasyon Sistemi — Ana Pipeline.

Modül sırası (kural §2 — katman atlama yasaktır; modüller arası iletişim
yalnızca JSON dosyaları üzerindendir):

    [Veri Akış Modülü] → frame + meta →
      [YZ Modülü] → outputs/ariza_verileri.json →
        [Optimizasyon Modülü] → outputs/gorev_cizelgesi.json →
          [GUI Modülü] → Yönetici

main.py orchestrator olarak her modülü sırayla tetikler.

Kullanım:
    python main.py                         # GUI ile tam pipeline
    python main.py --no-gui                # Headless pipeline
    python main.py --scenario A            # A/B/C senaryosu
    python main.py --reset                 # outputs/ temizle ve çık
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.ai_inference import GESFaultDetector, JsonWriter
from modules.ai_inference.json_writer import make_timestamp
from modules.data_feeder import DataFeeder
from modules.optimization import MaintenanceScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

DEFAULT_MODEL_PATH = Path("models") / "best.pt"
OUTPUTS_DIR = Path("outputs")
FRAME_INTERVAL_S = 0.5  # Karelerin arasındaki simülasyon gecikmesi


def run_pipeline(
    model_path: Path,
    scenario: str | None,
    no_gui: bool,
    output_dir: Path | None = None,
) -> dict | None:
    """Tam pipeline'ı çalıştırır: Veri Akış → YZ → Optimizasyon.

    Args:
        model_path: YOLO26 ağırlık dosyası yolu.
        scenario: "A", "B", "C" veya None (tam koşum).
        no_gui: True ise yalnızca pipeline; GUI thread'i başlatılmaz.
        output_dir: Çıktıların kaydedileceği dizin. None ise varsayılan
            ``outputs/``. Senaryo karşılaştırması için kullanılır.

    Returns:
        Optimizasyon çıktısı (gorev_cizelgesi içeriği) veya None.
    """
    out_dir = Path(output_dir) if output_dir else OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    fault_file = out_dir / "ariza_verileri.json"
    schedule_file = out_dir / "gorev_cizelgesi.json"

    if not model_path.exists():
        logger.error(
            "Model ağırlıkları bulunamadı: %s\n"
            "Önce 'python scripts/train_yolo26.py' ile eğitimi tamamlayın.",
            model_path,
        )
        sys.exit(1)

    # ── 1. Veri Akış Modülü
    feeder = DataFeeder()

    # ── 2. YZ Modülü
    detector = GESFaultDetector(model_path=model_path)
    writer = JsonWriter(output_path=fault_file)
    writer.reset()

    # GUI opsiyonel
    if not no_gui:
        _start_gui_thread()

    # ── Inference döngüsü
    logger.info("Pipeline başlatıldı. Senaryo: %s", scenario or "Tümü")
    total_detections = 0
    frame_count = 0
    for frame, meta in feeder.iter_frames(scenario):
        frame_count += 1
        meta["timestamp"] = make_timestamp()
        detections = detector.detect(frame, meta)
        if not detections:
            detections = [{
                "timestamp": meta["timestamp"],
                "panel_id": int(meta["panel_id"]),
                "gps": meta["gps"],
                "hasar": "sağlam",
                "koordinat": [0, 0, 0, 0],
                "guven_skoru": 1.0,
                "image_path": meta.get("image_path"),
                "gercek_durum": meta.get("gercek_durum", "sağlam"),
            }]
        total_detections += writer.write_detections(detections)
        time.sleep(FRAME_INTERVAL_S)

    logger.info(
        "YZ döngüsü tamamlandı: %d kare işlendi, %d arıza tespiti → %s",
        frame_count,
        total_detections,
        writer.output_path,
    )

    # ── 3. Optimizasyon Modülü (JSON → JSON, katman atlanmıyor)
    scheduler = MaintenanceScheduler(
        fault_file=fault_file,
        schedule_file=schedule_file,
    )
    schedule = scheduler.solve_and_generate_schedule()
    if schedule and schedule.get("tasks"):
        logger.info(
            "Çizelge: %d görev | %.0f TL | %d ekip | %.2f km",
            len(schedule["tasks"]),
            schedule["total_cost_tl"],
            schedule["team_count"],
            schedule["total_distance_km"],
        )
    elif schedule:
        logger.info(
            "Çizelge: görev yok — %s",
            schedule.get("note", "boş çizelge"),
        )
    return schedule


def _start_gui_thread() -> None:
    """GUI'yi ayrı bir thread'de başlatır (alternatif kullanım için).

    Tam çalışma için PyQt6 ana thread'de tutulmalıdır; bkz. __main__ bloğu.
    """
    try:
        from modules.gui import run_gui  # pylint: disable=import-outside-toplevel

        gui_thread = threading.Thread(target=run_gui, daemon=True, name="GUIThread")
        gui_thread.start()
        time.sleep(1.0)
    except ImportError as exc:
        logger.warning("GUI başlatılamadı (PyQt6 yüklü değil?): %s", exc)


def parse_args() -> argparse.Namespace:
    """Komut satırı argümanlarını ayrıştırır."""
    parser = argparse.ArgumentParser(
        description="GES Otonom Termal Denetim & Bakım Optimizasyon Sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"YOLO26 ağırlık dosyası yolu (varsayılan: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--scenario",
        choices=["A", "B", "C"],
        default=None,
        help="Çalıştırılacak test senaryosu (A/B/C). Belirtilmezse tüm paneller.",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="GUI olmadan (headless) çalıştır.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="outputs/ariza_verileri.json ve gorev_cizelgesi.json sıfırla, çık.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.reset:
        JsonWriter().reset()
        sched_file = OUTPUTS_DIR / "gorev_cizelgesi.json"
        if sched_file.exists():
            sched_file.unlink()
        logger.info("outputs/ sıfırlandı.")
        sys.exit(0)

    if not args.no_gui:
        # GUI ana thread'de çalışmalı — pipeline ayrı thread'de başlatılır
        from modules.gui import run_gui  # pylint: disable=import-outside-toplevel

        def run_thread(scenario):
            # Yeniden başlatmada önceki çıktıları temizle
            fault_file = OUTPUTS_DIR / "ariza_verileri.json"
            schedule_file = OUTPUTS_DIR / "gorev_cizelgesi.json"
            if fault_file.exists():
                try:
                    fault_file.unlink()
                except Exception:
                    pass
            if schedule_file.exists():
                try:
                    schedule_file.unlink()
                except Exception:
                    pass
            run_pipeline(args.model, scenario, no_gui=True)

        pipeline_thread = threading.Thread(
            target=run_thread,
            args=(args.scenario,),
            name="PipelineThread",
            daemon=True,
        )
        pipeline_thread.start()
        run_gui(run_pipeline_callback=run_thread, initial_scenario=args.scenario)
    else:
        run_pipeline(args.model, args.scenario, no_gui=True)
