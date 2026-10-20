"""Veri seti denetim/temizleme scripti birim testleri.

Çalıştırma:
    pytest tests/test_audit_dataset.py -v
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.audit_and_fix_dataset import (
    apply_remap,
    build_groups,
    main,
    parse_label_text,
    polygon_to_bbox,
    source_stem,
    stratified_group_split,
)


# ── Poligon → bbox ───────────────────────────────────────────────────────────


def test_polygon_to_bbox_axis_aligned():
    box = polygon_to_bbox([0.1, 0.2, 0.5, 0.2, 0.5, 0.6, 0.1, 0.6])
    assert box == pytest.approx((0.3, 0.4, 0.4, 0.4))


def test_polygon_to_bbox_clips_out_of_range():
    box = polygon_to_bbox([-0.2, 0.5, 0.4, 0.1, 0.4, 1.3])
    assert box == pytest.approx((0.2, 0.55, 0.4, 0.9))


def test_parse_mixed_file_yields_only_bboxes():
    text = (
        "1 0.5 0.5 0.2 0.2\n"
        "5 0.1 0.1 0.3 0.1 0.3 0.4 0.1 0.4\n"
        "2 0.5 0.5\n"  # hatalı satır
        "1 0.5 0.5 0.2 0.2\n"  # yinelenen
    )
    rows, stats = parse_label_text(text)
    assert [r.cls for r in rows] == [1, 5]
    assert rows[1].from_polygon and not rows[0].from_polygon
    assert (rows[1].cx, rows[1].cy, rows[1].w, rows[1].h) == pytest.approx((0.2, 0.25, 0.2, 0.3))
    assert stats["bbox"] == 2 and stats["polygon"] == 1
    assert stats["malformed"] == 1 and stats["duplicate"] == 1


def test_remap_drops_and_dedupes_merged_classes():
    rows, _ = parse_label_text("1 0.5 0.5 0.2 0.2\n5 0.5 0.5 0.2 0.2\n4 0.3 0.3 0.1 0.1")
    out = apply_remap(rows, {1: 1, 5: 1, 4: None})
    assert [(r.cls, r.cx) for r in out] == [(1, 0.5)]


def test_source_stem():
    assert source_stem("0266_jpg.rf.00e3e6cd.jpg") == "0266_jpg"
    assert source_stem("plain.jpg") == "plain"


# ── Gruplama + bölme ─────────────────────────────────────────────────────────


def test_groups_merge_stems_and_pairs():
    stems = ["a", "a", "b", "c", "d"]
    groups = build_groups(stems, [(2, 3, 0, 1.0)])
    assert groups[0] == groups[1]
    assert groups[2] == groups[3]
    assert len({groups[0], groups[2], groups[4]}) == 3


def test_split_keeps_groups_together_and_follows_ratios():
    rng = np.random.default_rng(0)
    stems = [f"s{i // 3}" for i in range(300)]  # 100 kaynak × 3 augmentasyon
    groups = build_groups(stems, [])
    n_groups = max(groups) + 1
    feats = np.zeros((n_groups, 3))
    for g in groups:
        feats[g, 0] += 1
        feats[g, 1 + rng.integers(2)] += 1
    assign = stratified_group_split(feats, (0.8, 0.1, 0.1), seed=1)

    split_of_image = [assign[g] for g in groups]
    per_stem = defaultdict(set)
    for s, sp in zip(stems, split_of_image):
        per_stem[s].add(sp)
    assert all(len(v) == 1 for v in per_stem.values())

    counts = np.bincount(split_of_image, minlength=3)
    assert counts.tolist() == pytest.approx([240, 30, 30], abs=6)
    assert assign == stratified_group_split(feats, (0.8, 0.1, 0.1), seed=1)


# ── Uçtan uca küçük fixture ──────────────────────────────────────────────────


def _write_img(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])


def _write_lbl(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def tiny_dataset(tmp_path: Path) -> Path:
    """Gri (termal) + renkli görüntüler, karışık etiketler ve sızıntılı bölmeler."""
    src = tmp_path / "src"
    rng = np.random.default_rng(42)
    poly = "12 0.1 0.1 0.4 0.1 0.4 0.4 0.1 0.4"
    box = "9 0.6 0.6 0.2 0.2"
    for i in range(12):
        split = ["train", "valid", "test"][i % 3]
        gray = cv2.GaussianBlur(rng.integers(0, 255, (64, 64), dtype=np.uint8), (0, 0), 3)
        gray = cv2.resize(gray, (128, 128))
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        name = f"therm{i}_jpg.rf.{i:04x}"
        _write_img(src / split / "images" / f"{name}.jpg", img)
        # .txt.orig önceliklidir; .txt (zaten remap edilmiş) yok sayılmalı
        _write_lbl(src / split / "labels" / f"{name}.txt.orig", f"{box}\n{poly}\n")
        _write_lbl(src / split / "labels" / f"{name}.txt", "0 0.5 0.5 0.1 0.1")
        if i < 4:  # aynı kaynak gövdesi farklı bölmede (augmentasyon sızıntısı)
            other = ["valid", "test", "train"][i % 3]
            _write_img(src / other / "images" / f"therm{i}_jpg.rf.dup{i}.jpg", cv2.flip(img, 1))
            _write_lbl(src / other / "labels" / f"therm{i}_jpg.rf.dup{i}.txt", box)
    # Farklı gövde ama yakın kopya (parlaklık +3)
    base = cv2.imread(str(src / "train" / "images" / "therm0_jpg.rf.0000.jpg"))
    _write_img(src / "test" / "images" / "renamed_jpg.rf.x.jpg", cv2.add(base, 3))
    _write_lbl(src / "test" / "labels" / "renamed_jpg.rf.x.txt", box)
    # Renkli (RGB) görüntüler
    for i in range(4):
        img = rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)
        _write_img(src / "train" / "images" / f"rgb{i}_jpg.rf.{i}.jpg", img)
        _write_lbl(src / "train" / "labels" / f"rgb{i}_jpg.rf.{i}.txt",
                   "2 0.5 0.5 0.3 0.3\n1 0.2 0.2 0.5 0.2 0.5 0.5 0.2 0.5")
    return src


def _run(tiny_dataset: Path, tmp_path: Path, *extra: str) -> tuple[Path, Path, int]:
    out = tmp_path / "clean"
    reports = tmp_path / "reports"
    code = main([
        "--src", str(tiny_dataset), "--out", str(out), "--report-dir", str(reports),
        "--ratios", "0.6", "0.2", "0.2", "--min-test", "hotspot=0", "--workers", "2",
        *extra,
    ])
    return out, reports, code


def test_end_to_end_fixture(tiny_dataset: Path, tmp_path: Path):
    src_snapshot = {p: p.read_bytes() for p in tiny_dataset.rglob("*") if p.is_file()}
    out, reports, code = _run(tiny_dataset, tmp_path, "--skip-verify")
    assert code == 0

    # Kaynak değişmedi
    assert {p: p.read_bytes() for p in tiny_dataset.rglob("*") if p.is_file()} == src_snapshot

    # Tüm etiketler 5 sütunlu, sınıflar 0..2
    for lbl in out.rglob("labels/*.txt"):
        for line in lbl.read_text().splitlines():
            parts = line.split()
            assert len(parts) == 5
            assert 0 <= int(parts[0]) < 3

    with open(out / "manifest.csv", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    assert len(manifest) == 12 + 4 + 1 + 4

    # Grup (ve gövde) tek bölmede
    for key in ("group", "stem"):
        splits = defaultdict(set)
        for row in manifest:
            splits[row[key]].add(row["split"])
        assert all(len(v) == 1 for v in splits.values()), key

    by_file = {row["file"]: row for row in manifest}
    assert by_file["renamed_jpg.rf.x.jpg"]["group"] == by_file["therm0_jpg.rf.0000.jpg"]["group"]
    assert by_file["therm1_jpg.rf.dup1.jpg"]["group"] == by_file["therm1_jpg.rf.0001.jpg"]["group"]
    assert {by_file[f"rgb{i}_jpg.rf.{i}.jpg"]["modality"] for i in range(4)} == {"rgb"}
    assert by_file["therm5_jpg.rf.0005.jpg"]["modality"] == "gray"
    # .txt.orig okundu: 1 bbox + 1 poligon → hotspot (9, 12 → 0)
    assert by_file["therm5_jpg.rf.0005.jpg"]["n_rows_from_polygon"] == "1"
    assert by_file["therm5_jpg.rf.0005.jpg"]["n_rows_out"] == "2"

    report = json.loads((reports / "dataset_audit.json").read_text(encoding="utf-8"))
    assert report["leakage_before"]["groups_spanning_multiple_splits"] > 0
    assert report["leakage_after"]["groups_spanning_multiple_splits"] == 0
    assert report["label_sources"] == {"txt.orig": 12, "txt": 9}
    assert report["mixed_files_before"]["train"]["mixed_files_after_remap"] > 0
    assert (reports / "dataset_audit.md").exists()
    assert (tmp_path / "clean.yaml").exists()

    # Üzerine yazma koruması
    with pytest.raises(FileExistsError):
        _run(tiny_dataset, tmp_path, "--skip-verify")


def test_remap_config_and_ultralytics_verify(tiny_dataset: Path, tmp_path: Path):
    pytest.importorskip("ultralytics")
    cfg = tmp_path / "remap.yaml"
    cfg.write_text("names: [termal_ariza, diger]\nremap: {9: 0, 12: 0, 1: 1, 2: 1}\n")
    out, reports, code = _run(tiny_dataset, tmp_path, "--remap-config", str(cfg))
    assert code == 0
    report = json.loads((reports / "dataset_audit.json").read_text(encoding="utf-8"))
    uv = report["ultralytics_verify"]
    assert uv["total_corrupt"] == 0
    assert all(s["with_segments"] == 0 for s in uv["splits"].values())
    assert uv["check_det_dataset"]["names"] == ["termal_ariza", "diger"]
