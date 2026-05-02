"""YOLO26 model eğitim scripti.

Bu script modül DIŞINDA tutulur; ai_inference modülü yalnızca
eğitilmiş ağırlıkları yükler (inference only).

Kullanım:
    python scripts/train_yolo26.py
    python scripts/train_yolo26.py --epochs 100 --batch 16 --device cuda:0

Çıktı:
    models/best.pt  — en iyi doğrulama mAP'ine sahip ağırlık
    outputs/reports/train_metrics.json — eğitim metrikleri
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("train")

DATA_YAML = Path("data") / "ges_project.yaml"
MODELS_DIR = Path("models")
REPORTS_DIR = Path("outputs") / "reports"

# Sınıf eşleştirme tablosu: orijinal veri seti ID → proje sınıf ID
# Orijinal: 15 sınıf | Proje: 3 sınıf
CLASS_REMAP: dict[int, int | None] = {
    0: 2,    # Bird Drop      → tozlanma
    1: 1,    # Defective      → mikro_catlak
    2: 2,    # Dusty          → tozlanma
    3: None, # Electrical Damage → kapsam dışı
    4: None, # Non Defective  → kapsam dışı
    5: 1,    # Physical Damage → mikro_catlak
    6: 2,    # Snow           → tozlanma
    7: None, # MultiByPassed  → kapsam dışı
    8: None, # MultiDiode     → kapsam dışı
    9: 0,    # MultiHotSpot   → hotspot
    10: None,# SingleByPassed → kapsam dışı
    11: None,# SingleDiode    → kapsam dışı
    12: 0,   # SingleHotSpot  → hotspot
    13: None,# StringOpenCircuit → kapsam dışı
    14: None,# StringReversedPolarity → kapsam dışı
}


def remap_labels(dataset_dir: Path) -> None:
    """Veri setindeki etiket dosyalarını 3 sınıfa dönüştürür.

    Kapsam dışı sınıfları kaldırır, kalan sınıfları yeni ID'lerle yeniden
    yazar. Orijinal dosyalar .orig uzantısıyla yedeklenir.

    Args:
        dataset_dir: 'train', 'valid', 'test' alt dizinlerini içeren kök dizin.
    """
    for split in ["train", "valid", "test"]:
        labels_dir = dataset_dir / split / "labels"
        if not labels_dir.exists():
            logger.warning("Etiket dizini bulunamadı: %s", labels_dir)
            continue

        remapped_count = 0
        removed_count = 0

        for label_file in labels_dir.glob("*.txt"):
            backup = label_file.with_suffix(".txt.orig")
            # Eğer yedek yoksa oluştur
            if not backup.exists():
                import shutil
                shutil.copy2(label_file, backup)
            
            # Veriyi HER ZAMAN orijinal (backup) dosyasından oku
            lines = backup.read_text(encoding="utf-8").strip().splitlines()
            new_lines: list[str] = []

            for line in lines:
                parts = line.split()
                if not parts:
                    continue
                original_id = int(parts[0])
                new_id = CLASS_REMAP.get(original_id)

                if new_id is None:
                    removed_count += 1
                    continue  # kapsam dışı sınıf — kaldır

                new_lines.append(f"{new_id} " + " ".join(parts[1:]))
                remapped_count += 1

            # Dönüştürülmüş veriyi tekrar .txt olarak üzerine yaz
            label_file.write_text("\n".join(new_lines), encoding="utf-8")

        logger.info(
            "[%s] %d etiket yeniden eşlendi, %d etiket kaldırıldı.",
            split, remapped_count, removed_count,
        )


def train(epochs: int, batch: int, device: str, imgsz: int) -> None:
    """YOLO26 modelini eğitir ve ağırlıkları models/ dizinine kaydeder.

    Args:
        epochs: Eğitim dönem sayısı.
        batch: Mini-batch boyutu.
        device: Hesaplama cihazı ('cuda:0', 'cuda', 'cpu').
        imgsz: Giriş görüntü boyutu (piksel).
    """
    try:
        from ultralytics import YOLO  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise ImportError(
            "ultralytics paketi yüklü değil. 'pip install ultralytics' çalıştırın."
        ) from exc

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_YAML.exists():
        raise FileNotFoundError(f"Veri seti YAML bulunamadı: {DATA_YAML}")

    # Önce etiketleri 3 sınıfa dönüştür
    dataset_dir = Path("data") / "SOLAR PANEL DET.v1i.yolo26"
    logger.info("Etiket dönüşümü başlatılıyor…")
    remap_labels(dataset_dir)

    logger.info(
        "Eğitim başlatılıyor: epochs=%d, batch=%d, device=%s, imgsz=%d",
        epochs, batch, device, imgsz,
    )

    model = YOLO("yolo26s.pt")  # Proje zorunluluğu: YOLO26 mimarisi kullanılmalı

    results = model.train(
        data=str(DATA_YAML),
        epochs=epochs,
        batch=batch,
        device=device,
        imgsz=imgsz,
        project=str(MODELS_DIR),
        name="ges_yolo26",
        exist_ok=True,
        verbose=True,
        degrees=5.0,      # Döndürme azaltıldı (±5 derece)
        hsv_h=0.0,        # Termal görüntüde renk tonu bozmak zararlı olabilir, kapatıldı
        hsv_s=0.2,        # Doygunluk değişimi hafifletildi
        hsv_v=0.2,        # Parlaklık değişimi hafifletildi
        fliplr=0.5,       # Yatay çevirme (İHA'nın sağdan sola geçişi - Doğal)
        flipud=0.0,       # Dikey çevirme kapatıldı (paneller genelde hep aynı yönlüdür)
        scale=0.1,        # Boyutlandırma çok aza indirildi (%10)
        translate=0.1,    # Hafif öteleme (kamere titremesi için yeterli)
        perspective=0.0,  # Perspektif bozma tamamen kapatıldı
        mosaic=0.5,       # Mozaik ihtimali yarıya düşürüldü
        workers=8,        # Veri yükleme işlemci çekirdeği sayısı
        patience=20,      # 20 epoch boyunca iyileşme olmazsa eğitimi erken bitir
    )

    # En iyi ağırlığı models/best.pt'ye kopyala
    best_src = MODELS_DIR / "ges_yolo26" / "weights" / "best.pt"
    best_dst = MODELS_DIR / "best.pt"
    if best_src.exists():
        import shutil  # pylint: disable=import-outside-toplevel
        shutil.copy2(best_src, best_dst)
        logger.info("En iyi ağırlık kopyalandı: %s", best_dst)

    # Eğitim metriklerini JSON'a kaydet
    metrics = {
        "mAP50": float(results.results_dict.get("metrics/mAP50(B)", 0)),
        "mAP50-95": float(results.results_dict.get("metrics/mAP50-95(B)", 0)),
        "precision": float(results.results_dict.get("metrics/precision(B)", 0)),
        "recall": float(results.results_dict.get("metrics/recall(B)", 0)),
        "epochs": epochs,
        "best_model": str(best_dst),
    }
    metrics_path = REPORTS_DIR / "train_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    logger.info("Eğitim metrikleri kaydedildi: %s", metrics_path)
    logger.info("mAP@0.5 = %.4f (Başarı kriteri: 0.60 - 0.70 arası)", metrics["mAP50"])
    logger.info("mAP@0.5:0.95 = %.4f (Başarı kriteri: 0.35 - 0.55 arası)", metrics["mAP50-95"])

    if metrics["mAP50"] >= 0.60 and metrics["mAP50-95"] >= 0.35:
        logger.info("✓ Model endüstri standartlarına göre BAŞARILI kabul edilmiştir!")
    else:
        logger.warning(
            "⚠ Model doğruluk hedefleri tam olarak karşılanmadı. "
            "Ancak simülasyon ve entegrasyon (MILP/VRP) süreçleri için kullanılabilir."
        )


def parse_args() -> argparse.Namespace:
    """Komut satırı argümanlarını ayrıştırır."""
    parser = argparse.ArgumentParser(description="YOLO26 GES Model Eğitimi")
    parser.add_argument("--epochs", type=int, default=70, help="Epoch sayısı")
    parser.add_argument("--batch", type=int, default=16, help="Batch boyutu")
    parser.add_argument("--device", type=str, default="cuda", help="Hesaplama cihazı")
    parser.add_argument("--imgsz", type=int, default=640, help="Görüntü boyutu")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(args.epochs, args.batch, args.device, args.imgsz)
