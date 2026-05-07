"""Veri Akış Modülü (EE Simülasyonu) birim testleri.

Çalıştırma:
    pytest tests/test_data_feeder.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from modules.data_feeder import DataFeeder, SCENARIOS, Scenario, get_scenario


# ── Yardımcılar ──────────────────────────────────────────────────────────────


def _create_synthetic_dataset(root: Path) -> tuple[Path, Path]:
    """Geçici dizine 3 sınıf için minimum veri seti üretir.

    Returns:
        (dataset_dir, layout_path)
    """
    ds = root / "dataset"
    images_dir = ds / "images"
    labels_dir = ds / "labels"
    images_dir.mkdir(parents=True)
    labels_dir.mkdir(parents=True)

    # Her sınıf için 1 görüntü + label
    classes = {"hotspot_img": 0, "crack_img": 1, "dust_img": 2}
    for stem, cls_id in classes.items():
        # Boş 64x64 BGR görüntü
        img = np.full((64, 64, 3), 128, dtype=np.uint8)
        cv2.imwrite(str(images_dir / f"{stem}.jpg"), img)
        # Label: tek bbox ortada
        (labels_dir / f"{stem}.txt").write_text(
            f"{cls_id} 0.5 0.5 0.5 0.5\n", encoding="utf-8"
        )

    # Layout (5 panel)
    layout_dir = root / "layout"
    layout_dir.mkdir()
    layout = {
        "panel_count": 5,
        "origin_gps": [38.4200, 27.1400],
        "panels": [
            {"panel_id": i, "row": 0, "col": i, "gps": [38.42, 27.14 + 0.0003 * i]}
            for i in range(5)
        ],
    }
    layout_path = layout_dir / "panel_layout.json"
    layout_path.write_text(json.dumps(layout), encoding="utf-8")

    return ds, layout_path


@pytest.fixture
def feeder(tmp_path) -> DataFeeder:
    """Sentetik veri seti üzerinde çalışan DataFeeder örneği."""
    ds_dir, layout_path = _create_synthetic_dataset(tmp_path)
    return DataFeeder(dataset_dir=ds_dir, layout_path=layout_path, seed=1)


# ─────────────────────────────────────────────────────────────────────────────
# Senaryo katalogu
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioCatalog:
    """SCENARIOS sözlüğü doğru yapılandırılmış olmalı."""

    def test_three_scenarios_exist(self):
        assert set(SCENARIOS.keys()) == {"A", "B", "C"}

    def test_scenario_target_classes(self):
        assert SCENARIOS["A"].target_class == 2  # tozlanma
        assert SCENARIOS["B"].target_class == 0  # hotspot
        assert SCENARIOS["C"].target_class == 1  # mikro_catlak

    def test_scenario_panel_counts(self):
        assert len(SCENARIOS["A"].panel_ids) == 2   # %5 ≈ 2 panel
        assert len(SCENARIOS["B"].panel_ids) == 2   # 2 uç nokta
        assert len(SCENARIOS["C"].panel_ids) == 10  # dağınık

    def test_get_scenario_case_insensitive(self):
        assert get_scenario("a").name == "A"
        assert get_scenario("B").name == "B"

    def test_get_scenario_none_or_missing(self):
        assert get_scenario(None) is None
        assert get_scenario("Z") is None


# ─────────────────────────────────────────────────────────────────────────────
# DataFeeder — sınıf indeksleme
# ─────────────────────────────────────────────────────────────────────────────


class TestImageIndex:
    """test/labels taranarak doğru sınıf-görüntü eşleştirilmeli."""

    def test_classes_indexed(self, feeder):
        idx = feeder.available_classes()
        assert idx[0] == 1  # hotspot
        assert idx[1] == 1  # mikro_catlak
        assert idx[2] == 1  # tozlanma

    def test_panel_count(self, feeder):
        assert feeder.panel_count() == 5


# ─────────────────────────────────────────────────────────────────────────────
# DataFeeder — senaryo iterasyonu
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioIteration:
    """iter_frames her senaryoyu doğru sayıda + meta veriyle yayınlamalı."""

    def test_scenario_b_yields_two_frames(self, feeder):
        """Senaryo B 2 panel içerir."""
        # Layout'umuzda yalnızca 5 panel var; B'nin 0,29 panellerinden
        # sadece 0 mevcut. Senaryoyu inplace daraltıyoruz:
        scen = Scenario(name="B", target_class=0, panel_ids=[0, 1], description="test")
        frames = list(feeder.iter_frames(scen))
        assert len(frames) == 2
        for frame, meta in frames:
            assert frame.shape == (64, 64, 3)
            assert meta["panel_id"] in {0, 1}
            assert meta["scenario"] == "B"

    def test_scenario_meta_has_required_keys(self, feeder):
        scen = Scenario(name="X", target_class=2, panel_ids=[0], description="test")
        frames = list(feeder.iter_frames(scen))
        assert len(frames) == 1
        _, meta = frames[0]
        for key in ("panel_id", "gps", "timestamp", "flight_altitude", "scenario"):
            assert key in meta
        assert isinstance(meta["gps"], list) and len(meta["gps"]) == 2

    def test_full_run_yields_one_frame_per_panel(self, feeder):
        """scenario=None tüm panelleri sırayla beslemeli (5 panel = 5 kare)."""
        frames = list(feeder.iter_frames(None))
        assert len(frames) == 5
        seen_ids = {meta["panel_id"] for _, meta in frames}
        assert seen_ids == {0, 1, 2, 3, 4}

    def test_missing_class_skips(self, tmp_path):
        """Hedef sınıf veri setinde yoksa yield boş olmalı."""
        ds_dir, layout_path = _create_synthetic_dataset(tmp_path)
        # Hotspot label'larını sil
        for txt in (ds_dir / "labels").glob("hotspot*.txt"):
            txt.unlink()
        feeder = DataFeeder(dataset_dir=ds_dir, layout_path=layout_path)

        scen = Scenario(name="Z", target_class=0, panel_ids=[0, 1], description="test")
        frames = list(feeder.iter_frames(scen))
        assert frames == []
