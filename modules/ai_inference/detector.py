"""YOLO26 tabanlı GES panel arıza tespit motoru.

Bu modül, önceden eğitilmiş YOLO26 ağırlıklarını yükler ve
Veri Akış Modülü'nden gelen görüntü karelerinde arıza tespiti yapar.

Tespit edilen arızalar, arayüz sözleşmesine uygun JSON formatında
JsonWriter aracılığıyla outputs/ariza_verileri.json dosyasına yazılır.

Kapsam dışı:
    - Model eğitimi (bkz. scripts/train_yolo26.py)
    - GUI veya Optimizasyon modülü ile doğrudan iletişim
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Projenin tespit ettiği üç arıza sınıfı (değiştirilemez)
FAULT_CLASSES: dict[int, str] = {
    0: "hotspot",
    1: "mikro_catlak",
    2: "tozlanma",
}

# Varsayılan güven eşiği
DEFAULT_CONFIDENCE: float = 0.5


class GESFaultDetector:
    """YOLO26 tabanlı güneş paneli arıza tespit motoru.

    Veri Akış Modülü'nden alınan her görüntü karesi için inference çalıştırır
    ve tespit edilen arızaları standart JSON şemasına uygun dict listesi olarak döner.

    Args:
        model_path: Eğitilmiş YOLO26 ağırlık dosyasının yolu (.pt).
        confidence_threshold: Minimum kabul edilebilir güven skoru (0.0–1.0).
            Eşiğin altındaki tespitler filtrelenir. Varsayılan 0.5.

    Raises:
        FileNotFoundError: model_path dosyası bulunamazsa.
        ImportError: ultralytics paketi yüklü değilse.

    Example:
        >>> detector = GESFaultDetector("models/best.pt")
        >>> metadata = {"panel_id": 42, "gps": [38.123, 27.456]}
        >>> detections = detector.detect(frame, metadata)
    """

    def __init__(
        self,
        model_path: str | Path,
        confidence_threshold: float = DEFAULT_CONFIDENCE,
    ) -> None:
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self._model: Any = None  # ultralytics.YOLO instance

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model ağırlık dosyası bulunamadı: {self.model_path}\n"
                "Lütfen önce scripts/train_yolo26.py ile eğitim yapın "
                "veya models/ dizinine hazır .pt dosyasını kopyalayın."
            )

        self._load_model()

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray, metadata: dict) -> list[dict]:
        """Tek görüntü karesini analiz eder ve arıza tespitlerini döner.

        Args:
            frame: BGR formatında numpy görüntü dizisi (Veri Akış Modülü'nden).
            metadata: Kareye ait meta veri. Zorunlu anahtarlar:
                - ``panel_id`` (int): Panel kimlik numarası.
                - ``gps`` (list[float]): [lat, lon] koordinatları.
                - ``timestamp`` (str): ISO-8601 zaman damgası.
                - ``flight_altitude`` (float, opsiyonel): Uçuş yüksekliği (m).

        Returns:
            Her tespit için aşağıdaki JSON şemasına uygun dict listesi.
            Arıza tespit edilmezse boş liste döner::

                [
                    {
                        "timestamp": "2026-03-27T10:15:00",
                        "panel_id": 42,
                        "gps": [38.123, 27.456],
                        "hasar": "hotspot",
                        "koordinat": [x, y, w, h],
                        "guven_skoru": 0.94
                    },
                    ...
                ]

        Raises:
            ValueError: frame geçersizse veya metadata eksik anahtarlar içeriyorsa.
        """
        self._validate_inputs(frame, metadata)

        try:
            raw_results = self._run_inference(frame)
            detections = self._parse_results(raw_results, metadata)
            logger.debug(
                "Panel %s: %d tespit (güven ≥ %.2f)",
                metadata.get("panel_id"),
                len(detections),
                self.confidence_threshold,
            )
            return detections

        except Exception as exc:  # pylint: disable=broad-except
            # Modül hatası diğer modülleri çökertmemeli
            logger.error("Tespit hatası (panel_id=%s): %s", metadata.get("panel_id"), exc)
            return []

    def is_ready(self) -> bool:
        """Model yüklenmiş ve kullanıma hazır mı?

        Returns:
            True ise model yüklü, False ise yükleme başarısız.
        """
        return self._model is not None

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """YOLO26 ağırlıklarını belleğe yükler."""
        try:
            from ultralytics import YOLO  # pylint: disable=import-outside-toplevel

            self._model = YOLO(str(self.model_path))
            logger.info("YOLO26 modeli yüklendi: %s", self.model_path)
        except ImportError as exc:
            raise ImportError(
                "ultralytics paketi yüklü değil. "
                "Lütfen 'pip install ultralytics' komutunu çalıştırın."
            ) from exc

    def _run_inference(self, frame: np.ndarray) -> list:
        """Ham YOLO inference sonuçlarını döner.

        Args:
            frame: Ön işlenmiş görüntü dizisi.

        Returns:
            ultralytics Results nesneleri listesi.
        """
        results = self._model.predict(
            source=frame,
            conf=self.confidence_threshold,
            verbose=False,
        )
        return results

    def _parse_results(self, raw_results: list, metadata: dict) -> list[dict]:
        """YOLO çıktısını proje JSON şemasına dönüştürür.

        Args:
            raw_results: ultralytics Results listesi.
            metadata: Kareye ait meta veri (timestamp, panel_id, gps).

        Returns:
            JSON şemasına uygun dict listesi.
        """
        detections: list[dict] = []

        for result in raw_results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls.item())
                fault_name = FAULT_CLASSES.get(class_id)

                if fault_name is None:
                    logger.warning("Bilinmeyen sınıf ID: %d — atlandı.", class_id)
                    continue

                # [x_center, y_center, width, height] → [x, y, w, h] (pixel)
                xywh = box.xywh[0].tolist()
                koordinat = [int(v) for v in xywh]

                detections.append(
                    {
                        "timestamp": metadata["timestamp"],
                        "panel_id": int(metadata["panel_id"]),
                        "gps": metadata["gps"],
                        "hasar": fault_name,
                        "koordinat": koordinat,
                        "guven_skoru": round(float(box.conf.item()), 4),
                    }
                )

        return detections

    @staticmethod
    def _validate_inputs(frame: np.ndarray, metadata: dict) -> None:
        """Giriş parametrelerini doğrular.

        Args:
            frame: Görüntü dizisi.
            metadata: Meta veri dict.

        Raises:
            ValueError: Geçersiz frame veya eksik metadata anahtarı.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("Geçersiz frame: boş veya None.")

        required_keys = {"timestamp", "panel_id", "gps"}
        missing = required_keys - metadata.keys()
        if missing:
            raise ValueError(f"Metadata eksik anahtarlar içeriyor: {missing}")

        if not isinstance(metadata["gps"], (list, tuple)) or len(metadata["gps"]) != 2:
            raise ValueError("metadata['gps'] [lat, lon] çifti olmalıdır.")
