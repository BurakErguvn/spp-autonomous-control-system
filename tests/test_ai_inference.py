"""ai_inference modülü birim testleri.

Çalıştırma:
    pytest tests/test_ai_inference.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from modules.ai_inference.json_writer import (
    DETECTION_JSON_SCHEMA,
    JsonWriter,
    ValidationError,
    make_timestamp,
)
from modules.ai_inference.preprocessor import Preprocessor

# ── Sabit test verisi ─────────────────────────────────────────────────────────

VALID_DETECTION = {
    "timestamp": "2026-03-27T10:15:00+00:00",
    "panel_id": 42,
    "gps": [38.123, 27.456],
    "hasar": "hotspot",
    "koordinat": [100, 150, 80, 60],
    "guven_skoru": 0.94,
}


# ─────────────────────────────────────────────────────────────────────────────
# JSON Şema Testleri
# ─────────────────────────────────────────────────────────────────────────────


class TestJsonSchema:
    """JsonWriter şema doğrulama testleri."""

    def test_valid_detection_passes(self):
        """Geçerli tespit dict'i şema doğrulamasından geçmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JsonWriter(output_path=Path(tmpdir) / "test.json")
            writer.validate_one(VALID_DETECTION)  # exception fırlatmamalı

    def test_missing_required_field_raises(self):
        """Zorunlu alan eksikse ValidationError fırlatılmalı."""
        invalid = VALID_DETECTION.copy()
        del invalid["hasar"]
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JsonWriter(output_path=Path(tmpdir) / "test.json")
            with pytest.raises(ValidationError):
                writer.validate_one(invalid)

    def test_invalid_hasar_value_raises(self):
        """Tanımsız arıza sınıfı ValidationError fırlatmalı."""
        invalid = {**VALID_DETECTION, "hasar": "unknown_fault"}
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JsonWriter(output_path=Path(tmpdir) / "test.json")
            with pytest.raises(ValidationError):
                writer.validate_one(invalid)

    def test_confidence_out_of_range_raises(self):
        """Güven skoru [0, 1] dışındaysa ValidationError fırlatmalı."""
        invalid = {**VALID_DETECTION, "guven_skoru": 1.5}
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JsonWriter(output_path=Path(tmpdir) / "test.json")
            with pytest.raises(ValidationError):
                writer.validate_one(invalid)

    def test_gps_wrong_length_raises(self):
        """GPS [lat, lon, extra] 3 elemanlıysa ValidationError fırlatmalı."""
        invalid = {**VALID_DETECTION, "gps": [38.0, 27.0, 100.0]}
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JsonWriter(output_path=Path(tmpdir) / "test.json")
            with pytest.raises(ValidationError):
                writer.validate_one(invalid)

    def test_all_three_fault_classes_valid(self):
        """Üç geçerli arıza sınıfının tamamı şemadan geçmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JsonWriter(output_path=Path(tmpdir) / "test.json")
            for fault in ["hotspot", "mikro_catlak", "tozlanma"]:
                det = {**VALID_DETECTION, "hasar": fault}
                writer.validate_one(det)  # exception fırlatmamalı


# ─────────────────────────────────────────────────────────────────────────────
# JsonWriter Yazma Testleri
# ─────────────────────────────────────────────────────────────────────────────


class TestJsonWriter:
    """JsonWriter dosya yazma testleri."""

    def test_write_single_detection(self):
        """Tek tespit JSON dosyasına doğru yazılmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)
            count = writer.write_detections([VALID_DETECTION])

            assert count == 1
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data) == 1
            assert data[0]["panel_id"] == 42

    def test_write_appends_to_existing(self):
        """İkinci yazma mevcut tespitlere eklenmeli (üzerine yazmamalı)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)
            writer.write_detections([VALID_DETECTION])
            writer.write_detections([{**VALID_DETECTION, "panel_id": 99}])

            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data) == 2

    def test_empty_list_writes_nothing(self):
        """Boş liste gönderildiğinde dosya oluşturulmamalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)
            count = writer.write_detections([])
            assert count == 0
            assert not path.exists()

    def test_invalid_detection_skipped(self):
        """Geçersiz tespit atlanmalı, pipeline durmamalı."""
        invalid = {**VALID_DETECTION, "hasar": "invalid_class"}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)
            count = writer.write_detections([invalid])
            assert count == 0

    def test_reset_clears_file(self):
        """reset() çağrısı dosyayı boş liste ile sıfırlamalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)
            writer.write_detections([VALID_DETECTION])
            writer.reset()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data == []


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessor Testleri
# ─────────────────────────────────────────────────────────────────────────────


class TestPreprocessor:
    """Preprocessor görüntü ön işleme testleri."""

    def test_process_rgb_frame(self):
        """RGB görüntü normalize edilmiş [0,1] dizisine dönüşmeli."""
        prep = Preprocessor(input_size=(640, 640))
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = prep.process(frame)
        assert result.shape == (640, 640, 3)
        assert result.dtype == np.float32
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_process_grayscale_converts_to_bgr(self):
        """Gri tonlamalı görüntü 3 kanala dönüştürülmeli."""
        prep = Preprocessor()
        frame = np.random.randint(0, 255, (480, 640), dtype=np.uint8)
        result = prep.process(frame)
        assert result.shape[2] == 3

    def test_empty_frame_raises(self):
        """Boş frame ValueError fırlatmalı."""
        prep = Preprocessor()
        with pytest.raises(ValueError):
            prep.process(np.array([]))

    def test_normalize_thermal(self):
        """Termal normalize [0, 255] aralığında uint8 döndürmeli."""
        prep = Preprocessor()
        frame = np.array([[100, 200], [150, 300]], dtype=np.float32)
        result = prep.normalize_thermal(frame)
        assert result.dtype == np.uint8
        assert result.min() >= 0
        assert result.max() <= 255


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Döngü Testleri (Senaryo)
# ─────────────────────────────────────────────────────────────────────────────


class TestPipelineNoFault:
    """Arıza olmayan karelerde pipeline döngüsünün devam ettiğini doğrular."""

    def test_empty_detections_does_not_write(self):
        """Tespit yoksa JSON dosyasına hiçbir şey eklenmemeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)
            # Boş tespit listesi simülasyonu (güven eşiği altında tespitler filtrelendi)
            for _ in range(5):
                writer.write_detections([])
            assert not path.exists()

    def test_mixed_frames_accumulate(self):
        """Arızalı ve arızasız kareler doğru şekilde biriktirilmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ariza.json"
            writer = JsonWriter(output_path=path)

            # 3 arızasız kare
            for _ in range(3):
                writer.write_detections([])

            # 2 arızalı kare
            det_a = {**VALID_DETECTION, "panel_id": 1}
            det_b = {**VALID_DETECTION, "panel_id": 2, "hasar": "mikro_catlak"}
            writer.write_detections([det_a])
            writer.write_detections([det_b])

            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı fonksiyon testleri
# ─────────────────────────────────────────────────────────────────────────────


def test_make_timestamp_format():
    """make_timestamp() ISO-8601 formatında string döndürmeli."""
    ts = make_timestamp()
    assert isinstance(ts, str)
    assert "T" in ts  # ISO-8601 tarih-zaman ayracı
    assert len(ts) >= 19
