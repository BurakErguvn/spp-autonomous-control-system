"""Model performans metrikleri hesaplayıcı.

İP 4 zorunlu metrikleri: Accuracy, Precision, Recall, F1-Score,
mAP (Mean Average Precision) ve Confusion Matrix.

Kullanım:
    Doğrulama seti üzerinde çalıştırılır; sonuçlar hem terminale
    yazdırılır hem de outputs/reports/ dizinine kaydedilir.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)

CLASS_NAMES: list[str] = ["hotspot", "mikro_catlak", "tozlanma"]
REPORTS_DIR: Path = Path("outputs") / "reports"


class MetricsEvaluator:
    """Model performans metriklerini hesaplar ve raporlar.

    Args:
        class_names: Değerlendirmeye dahil edilecek sınıf isimleri.
            Varsayılan: ["hotspot", "mikro_catlak", "tozlanma"]
        reports_dir: Rapor çıktı dizini. Varsayılan: outputs/reports/

    Example:
        >>> evaluator = MetricsEvaluator()
        >>> report = evaluator.evaluate(y_true, y_pred)
        >>> evaluator.save_report(report)
    """

    def __init__(
        self,
        class_names: list[str] | None = None,
        reports_dir: str | Path = REPORTS_DIR,
    ) -> None:
        self.class_names = class_names or CLASS_NAMES
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate(
        self,
        y_true: list[int],
        y_pred: list[int],
        map_score: float | None = None,
    ) -> dict:
        """Tüm zorunlu metrikleri hesaplar.

        Args:
            y_true: Gerçek sınıf etiketleri (integer).
            y_pred: Modelin tahmin ettiği sınıf etiketleri (integer).
            map_score: YOLO tarafından hesaplanan mAP@0.5 değeri.
                Sağlanmazsa None olarak kaydedilir.

        Returns:
            Tüm metrikleri içeren dict::

                {
                    "accuracy": 0.91,
                    "precision": 0.89,
                    "recall": 0.87,
                    "f1_score": 0.88,
                    "mAP": 0.86,
                    "confusion_matrix": [[...], ...],
                    "class_report": {...}
                }
        """
        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)

        accuracy = accuracy_score(y_true_arr, y_pred_arr)
        precision = precision_score(y_true_arr, y_pred_arr, average="macro", zero_division=0)
        recall = recall_score(y_true_arr, y_pred_arr, average="macro", zero_division=0)
        f1 = f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0)
        cm = confusion_matrix(y_true_arr, y_pred_arr)
        class_report = classification_report(
            y_true_arr,
            y_pred_arr,
            target_names=self.class_names,
            output_dict=True,
            zero_division=0,
        )

        report = {
            "accuracy": round(float(accuracy), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "mAP": round(float(map_score), 4) if map_score is not None else None,
            "confusion_matrix": cm.tolist(),
            "class_report": class_report,
        }

        self._log_summary(report)
        return report

    def evaluate_from_yolo(self, yolo_results) -> dict:
        """ultralytics YOLO val() çıktısından metrikleri çıkarır.

        Args:
            yolo_results: model.val() tarafından dönen Results nesnesi.

        Returns:
            evaluate() ile aynı formatta metrik dict'i.
        """
        map50 = float(yolo_results.box.map50)
        precision = float(yolo_results.box.mp)
        recall = float(yolo_results.box.mr)
        f1 = 2 * (precision * recall) / (precision + recall + 1e-9)

        report = {
            "accuracy": None,          # YOLO detection'da accuracy doğrudan hesaplanamaz
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "mAP": round(map50, 4),
            "confusion_matrix": None,   # Ayrıca hesaplanmalı
            "class_report": None,
        }

        self._log_summary(report)
        return report

    def save_report(self, report: dict, tag: str = "") -> None:
        """Metrik raporunu JSON ve PNG olarak kaydeder.

        Args:
            report: evaluate() veya evaluate_from_yolo() çıktısı.
            tag: Dosya adına eklenecek ek etiket (ör. "scenario_A").
        """
        suffix = f"_{tag}" if tag else ""

        # JSON raporu
        json_path = self.reports_dir / f"metrics{suffix}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Metrik raporu kaydedildi: %s", json_path)

        # Confusion Matrix grafiği
        if report.get("confusion_matrix"):
            cm_path = self.reports_dir / f"confusion_matrix{suffix}.png"
            self._plot_confusion_matrix(
                np.array(report["confusion_matrix"]),
                cm_path,
            )
            logger.info("Confusion Matrix kaydedildi: %s", cm_path)

    def check_map_target(self, report: dict, target: float = 0.85) -> bool:
        """mAP değerinin proje hedefini (≥ 0.85) karşılayıp karşılamadığını kontrol eder.

        Args:
            report: evaluate() çıktısı.
            target: Minimum mAP hedefi. Varsayılan 0.85.

        Returns:
            True: hedef karşılanıyor, False: karşılanmıyor.
        """
        map_val = report.get("mAP")
        if map_val is None:
            logger.warning("mAP değeri raporlanmamış — hedef kontrolü yapılamadı.")
            return False

        if map_val >= target:
            logger.info("✓ mAP hedefi karşılandı: %.4f ≥ %.2f", map_val, target)
            return True

        logger.warning("✗ mAP hedefi KARŞILANMADI: %.4f < %.2f", map_val, target)
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _log_summary(self, report: dict) -> None:
        """Metrik özetini log'a yazar.

        Args:
            report: Metrik dict'i.
        """
        lines = ["\n══ YZ Modül Performans Raporu ══"]
        for key in ("accuracy", "precision", "recall", "f1_score", "mAP"):
            val = report.get(key)
            display = f"{val:.4f}" if val is not None else "N/A"
            lines.append(f"  {key:<12}: {display}")
        logger.info("\n".join(lines))

    def _plot_confusion_matrix(self, cm: np.ndarray, save_path: Path) -> None:
        """Confusion Matrix grafiğini PNG olarak kaydeder.

        Args:
            cm: Karmaşıklık matrisi dizisi.
            save_path: PNG çıktı yolu.
        """
        fig, ax = plt.subplots(figsize=(7, 6))
        disp = ConfusionMatrixDisplay(
            confusion_matrix=cm,
            display_labels=self.class_names,
        )
        disp.plot(ax=ax, colorbar=True, cmap="Blues")
        ax.set_title("Confusion Matrix — GES Arıza Tespiti")
        plt.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
