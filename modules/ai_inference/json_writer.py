"""Arıza tespitlerini JSON şemasına göre doğrular ve dışa yazar.

Bu modül; GESFaultDetector'dan gelen tespit listelerini projenin
zorunlu JSON arayüz sözleşmesine uygunluk açısından doğrular ve
outputs/ariza_verileri.json dosyasına atomik olarak yazar.

Kapsam:
    - JSON şema doğrulama (jsonschema)
    - Mevcut dosyaya ekleme (append) modu
    - Geçersiz tespitleri loglama ve atlama (pipeline'ı durdurmaz)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# JSON Arayüz Sözleşmesi (proje kuralları §2.2 — değiştirilemez)
# ──────────────────────────────────────────────────────────────────────────────
DETECTION_JSON_SCHEMA: dict = {
    "type": "object",
    "required": ["timestamp", "panel_id", "gps", "hasar", "koordinat", "guven_skoru"],
    "properties": {
        "timestamp": {
            "type": "string",
            "description": "ISO-8601 zaman damgası",
        },
        "panel_id": {
            "type": "integer",
            "minimum": 0,
        },
        "gps": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 2,
            "maxItems": 2,
            "description": "[lat, lon] koordinat çifti",
        },
        "hasar": {
            "type": "string",
            "enum": ["hotspot", "mikro_catlak", "tozlanma"],
        },
        "koordinat": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 4,
            "maxItems": 4,
            "description": "[x, y, w, h] piksel koordinatları",
        },
        "guven_skoru": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
    },
    "additionalProperties": False,
}


class ValidationError(Exception):
    """Tespit dict'i JSON şema sözleşmesini ihlal ettiğinde fırlatılır."""


class JsonWriter:
    """Arıza tespitlerini doğrulayıp outputs/ariza_verileri.json'a yazar.

    Her yazma işlemi atomiktir: önce geçici dosyaya yazılır, ardından
    hedef dosyayla değiştirilir. Böylece GUI tarafında yarım okunmuş
    dosya riski ortadan kalkar.

    Args:
        output_path: JSON çıktı dosyasının yolu.
            Varsayılan: outputs/ariza_verileri.json

    Example:
        >>> writer = JsonWriter()
        >>> writer.write_detections(detections)
    """

    DEFAULT_OUTPUT: Path = Path("outputs") / "ariza_verileri.json"

    def __init__(self, output_path: str | Path | None = None) -> None:
        self.output_path = Path(output_path) if output_path else self.DEFAULT_OUTPUT
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def write_detections(self, detections: list[dict]) -> int:
        """Tespit listesini doğrulayıp JSON dosyasına ekler.

        Args:
            detections: GESFaultDetector.detect() çıktısı; her öğe
                DETECTION_JSON_SCHEMA'ya uygun dict olmalıdır.

        Returns:
            Başarıyla yazılan tespit sayısı.

        Note:
            Şema doğrulamasından geçemeyen tespitler loglanır ve atlanır;
            pipeline durdurulmaz.
        """
        if not detections:
            return 0

        valid_detections = self._validate_all(detections)
        if not valid_detections:
            logger.warning("Geçerli tespit yok — dosyaya yazılmadı.")
            return 0

        existing = self._load_existing()
        existing.extend(valid_detections)
        self._atomic_write(existing)

        logger.info("%d tespit yazıldı → %s", len(valid_detections), self.output_path)
        return len(valid_detections)

    def validate_one(self, detection: dict) -> None:
        """Tek bir tespit dict'ini şemaya göre doğrular.

        Args:
            detection: Doğrulanacak tespit dict'i.

        Raises:
            ValidationError: Şema ihlali tespit edilirse.
        """
        try:
            jsonschema.validate(instance=detection, schema=DETECTION_JSON_SCHEMA)
        except jsonschema.ValidationError as exc:
            raise ValidationError(
                f"JSON şema ihlali (panel_id={detection.get('panel_id')}): {exc.message}"
            ) from exc

    def reset(self) -> None:
        """Çıktı dosyasını sıfırlar (boş liste yazar).

        Yeni bir simülasyon çalıştırması başlatılmadan önce çağrılmalıdır.
        """
        self._atomic_write([])
        logger.info("ariza_verileri.json sıfırlandı.")

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _validate_all(self, detections: list[dict]) -> list[dict]:
        """Listedeki her tespiti doğrular; geçersizleri atar.

        Args:
            detections: Doğrulanacak tespit listesi.

        Returns:
            Yalnızca geçerli tespitleri içeren liste.
        """
        valid: list[dict] = []
        for det in detections:
            try:
                self.validate_one(det)
                valid.append(det)
            except ValidationError as exc:
                logger.error("Geçersiz tespit atlandı: %s", exc)
        return valid

    def _load_existing(self) -> list[dict]:
        """Mevcut JSON dosyasındaki tespitleri yükler.

        Returns:
            Mevcut tespit listesi. Dosya yoksa boş liste.
        """
        if not self.output_path.exists():
            return []
        try:
            with open(self.output_path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Mevcut JSON okunamadı, sıfırdan başlanıyor: %s", exc)
            return []

    def _atomic_write(self, data: list[dict]) -> None:
        """Veriyi atomik olarak dosyaya yazar.

        Önce aynı dizinde geçici dosya oluşturur, ardından os.replace()
        ile hedef dosyayla değiştirir. Bu sayede yarım yazma riski yoktur.

        Args:
            data: Yazılacak tespit listesi.
        """
        dir_path = self.output_path.parent
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.output_path)
        except OSError:
            os.unlink(tmp_path)
            raise


def make_timestamp() -> str:
    """Şu anki zamanı ISO-8601 formatında döner (UTC).

    Returns:
        Örnek: "2026-03-27T10:15:00+00:00"
    """
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
