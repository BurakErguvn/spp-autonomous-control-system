"""GES Otonom Termal Denetim & Bakım Optimizasyon Sistemi — Ana Pipeline Başlatıcı.

Modül sırası (proje kuralları §2 — katman atlama yasaktır):

    [Veri Akış Modülü] → Görüntü Matrisi/Frame →
      [YZ Modülü] → outputs/ariza_verileri.json →
        [Optimizasyon Modülü] → outputs/gorev_cizelgesi.json →
          [GUI Modülü] → Yönetici

Kullanım:
    python main.py                         # GUI ile tam pipeline
    python main.py --no-gui                # GUI olmadan (headless) pipeline
    python main.py --scenario A            # Senaryo A simülasyonu
    python main.py --scenario B
    python main.py --scenario C
    python main.py --reset                 # outputs/ temizle, sıfırdan başla
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

# Proje kök dizinini Python yoluna ekle
sys.path.insert(0, str(Path(__file__).parent))

from modules.ai_inference import GESFaultDetector, JsonWriter
from modules.ai_inference.json_writer import make_timestamp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ── Yapılandırma sabitleri ────────────────────────────────────────────────────
DEFAULT_MODEL_PATH = Path("models") / "best.pt"
OUTPUTS_DIR = Path("outputs")
FRAME_INTERVAL_S = 0.5  # Her kare arasındaki simülasyon gecikmesi (saniye)

# Senaryo simülasyonunda kullanılacak sahte meta veri şablonları
SCENARIO_META: dict[str, list[dict]] = {
    "A": [
        {
            "panel_id": i,
            "gps": [38.4200 - i * 0.0003, 27.1400 + i * 0.0003],
            "timestamp": "",
            "flight_altitude": 30.0,
        }
        for i in range(30)  # Tesisin tamamı — %5 kirlenme beklenir
    ],
    "B": [
        {
            "panel_id": pid,
            "gps": [38.4200 - pid * 0.0003, 27.1400],
            "timestamp": "",
            "flight_altitude": 30.0,
        }
        for pid in [0, 29]  # 2 uç nokta — kritik hotspot beklenir
    ],
    "C": [
        {
            "panel_id": i,
            "gps": [38.4200 - i * 0.0003, 27.1400 + i * 0.0003],
            "timestamp": "",
            "flight_altitude": 30.0,
        }
        for i in range(0, 30, 3)  # Dağınık paneller — mikro çatlak beklenir
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────


def run_pipeline(
    model_path: Path,
    scenario: str | None,
    no_gui: bool,
) -> None:
    """Ana simülasyon döngüsünü çalıştırır.

    Args:
        model_path: YOLO26 ağırlık dosyası yolu.
        scenario: "A", "B" veya "C"; None ise tüm veri seti kullanılır.
        no_gui: True ise GUI başlatılmaz (headless mod).
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── YZ Modülü kurulumu ────────────────────────────────────────────────────
    writer = JsonWriter()
    writer.reset()  # Önceki çalıştırma çıktısını temizle

    if not model_path.exists():
        logger.error(
            "Model ağırlıkları bulunamadı: %s\n"
            "Lütfen 'python scripts/train_yolo26.py' ile eğitimi tamamlayın.",
            model_path,
        )
        sys.exit(1)

    detector = GESFaultDetector(model_path=model_path)

    # ── GUI (opsiyonel) ───────────────────────────────────────────────────────
    if not no_gui:
        _start_gui_thread()

    # ── Simülasyon kareleri ───────────────────────────────────────────────────
    meta_list = SCENARIO_META.get(scenario, []) if scenario else _load_all_meta()

    logger.info(
        "Pipeline başlatıldı. Senaryo: %s | Kare sayısı: %d",
        scenario or "Tümü",
        len(meta_list),
    )

    total_detections = 0
    for meta in meta_list:
        frame = _load_frame(meta)
        if frame is None:
            continue

        meta["timestamp"] = make_timestamp()
        detections = detector.detect(frame, meta)
        written = writer.write_detections(detections)
        total_detections += written

        time.sleep(FRAME_INTERVAL_S)

    logger.info(
        "Pipeline tamamlandı. Toplam %d arıza tespiti → %s",
        total_detections,
        writer.output_path,
    )
    logger.info(
        "Not: Optimizasyon modülü (IE) %s dosyasını okuyarak "
        "çizelge oluşturmalıdır.",
        writer.output_path,
    )


def _start_gui_thread() -> None:
    """GUI'yi ayrı bir thread'de başlatır.

    PyQt6 uygulaması ana thread'de çalışmalıdır; bu fonksiyon
    pipeline'ın doğrudan çağrılması durumunda alternatif bir düzen sağlar.
    Tam çalışma için GUI'yi ana thread'de başlatın (bkz. __main__ bloğu).
    """
    try:
        from modules.gui import run_gui  # pylint: disable=import-outside-toplevel
        gui_thread = threading.Thread(target=run_gui, daemon=True, name="GUIThread")
        gui_thread.start()
        time.sleep(1.0)  # GUI'nin başlamasını bekle
    except ImportError as exc:
        logger.warning("GUI başlatılamadı (PyQt6 yüklü değil?): %s", exc)


def _load_frame(meta: dict):
    """Veri setinden tek kare yükler.

    Gerçek kullanımda Veri Akış Modülü (EE) bu fonksiyonun yerini alır.
    Burada veri setinden rastgele bir görüntü yüklenir (simülasyon).

    Args:
        meta: Panel meta verisi.

    Returns:
        numpy görüntü dizisi veya None (dosya bulunamazsa).
    """
    import random  # pylint: disable=import-outside-toplevel
    import cv2     # pylint: disable=import-outside-toplevel

    dataset_dir = Path("data") / "SOLAR PANEL DET.v1i.yolo26" / "test" / "images"
    images = list(dataset_dir.glob("*.jpg")) + list(dataset_dir.glob("*.png"))

    if not images:
        logger.warning("Veri seti görüntüsü bulunamadı: %s", dataset_dir)
        return None

    img_path = random.choice(images)
    frame = cv2.imread(str(img_path))
    if frame is None:
        logger.warning("Görüntü okunamadı: %s", img_path)
    return frame


def _load_all_meta() -> list[dict]:
    """Tüm paneller için meta veri listesi oluşturur.

    Returns:
        30 panelin her biri için meta veri dict listesi.
    """
    import json  # pylint: disable=import-outside-toplevel

    layout_path = Path("modules") / "gui" / "assets" / "panel_layout.json"
    if not layout_path.exists():
        logger.warning("panel_layout.json bulunamadı — boş meta listesi döndürülüyor.")
        return []

    with open(layout_path, encoding="utf-8") as f:
        layout = json.load(f)

    return [
        {
            "panel_id": p["panel_id"],
            "gps": p["gps"],
            "timestamp": "",
            "flight_altitude": 30.0,
        }
        for p in layout.get("panels", [])
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


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
        help="outputs/ dizinini temizle ve çık.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.reset:
        writer = JsonWriter()
        writer.reset()
        logger.info("outputs/ sıfırlandı.")
        sys.exit(0)

    if not args.no_gui:
        # GUI ana thread'de çalışmalı — pipeline ayrı thread'de başlatılır
        import threading  # pylint: disable=import-outside-toplevel
        from modules.gui import run_gui  # pylint: disable=import-outside-toplevel

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(args.model, args.scenario, True),  # no_gui=True (GUI zaten ana thread'de)
            name="PipelineThread",
            daemon=True,
        )
        pipeline_thread.start()
        run_gui()  # Bloklayan çağrı — PyQt6 event loop ana thread'de
    else:
        run_pipeline(args.model, args.scenario, no_gui=True)
