"""Veri seti denetim scripti için ek bağımsız doğrulama testleri (tester).

- polygon/bbox kenar durumları, çevirme duyarsız yakın kopya tespiti,
  aynı seed → aynı çıktı (determinizm), kaynak/çıktı güvenlik korumaları;
- gerçek ``data/ges_clean`` varsa (git dışı) sızıntı/etiket/sınıf invariantları.

Çalıştırma:
    pytest tests/test_audit_dataset_extra.py -v
"""

from __future__ import annotations

import csv
import filecmp
import os
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.audit_and_fix_dataset import (
    dhash_variants,
    find_near_duplicates,
    main,
    parse_label_text,
    polygon_to_bbox,
    thumbnail,
)

REPO = Path(__file__).resolve().parent.parent


# ── Etiket kenar durumları ───────────────────────────────────────────────────


def test_polygon_degenerate_collinear_returns_none():
    assert polygon_to_bbox([0.1, 0.3, 0.2, 0.3, 0.4, 0.3]) is None  # yükseklik 0


def test_polygon_fully_outside_returns_none():
    assert polygon_to_bbox([1.2, 0.1, 1.5, 0.1, 1.5, 0.4]) is None  # kırpma sonrası genişlik 0


def test_polygon_order_independent_and_concave():
    pts = [0.2, 0.2, 0.6, 0.3, 0.4, 0.5, 0.7, 0.8, 0.1, 0.6]
    shuffled = [0.7, 0.8, 0.2, 0.2, 0.1, 0.6, 0.6, 0.3, 0.4, 0.5]
    assert polygon_to_bbox(pts) == pytest.approx(polygon_to_bbox(shuffled))
    cx, cy, w, h = polygon_to_bbox(pts)
    assert (cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2) == pytest.approx((0.1, 0.7, 0.2, 0.8))


def test_parse_label_malformed_and_degenerate_counts():
    text = (
        "1 0.5 0.5 0.2\n"                 # 3 değer -> hatalı
        "1 0.5 0.5 0.2 0.2 0.3\n"          # 5 değer -> hatalı (tek sayılı poligon)
        "1 0.5 0.5 0.0 0.2\n"              # sıfır genişlik -> dejenere
        "x 0.5 0.5 0.2 0.2\n"              # sınıf ayrıştırılamaz -> hatalı
        "3 0.1 0.1 0.3 0.1 0.2 0.1\n"      # çizgi poligon -> dejenere
        "0 0.5 0.5 0.2 0.2\n"
    )
    rows, stats = parse_label_text(text)
    assert [r.cls for r in rows] == [0]
    assert stats["malformed"] == 3 and stats["degenerate"] == 2


def test_bbox_row_clipped_to_unit_square():
    rows, _ = parse_label_text("0 0.95 0.5 0.2 0.2")  # x2 = 1.05 -> 1.0
    r = rows[0]
    assert r.cx + r.w / 2 == pytest.approx(1.0)
    assert 0 <= r.cx - r.w / 2 and r.w == pytest.approx(0.15)


# ── Yakın kopya tespiti ──────────────────────────────────────────────────────


def _synthetic(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 255, (48, 48), dtype=np.uint8)
    return cv2.resize(cv2.GaussianBlur(img, (0, 0), 2), (160, 160))


def _feat(g: np.ndarray):
    return dhash_variants(g), thumbnail(g)


@pytest.mark.parametrize("flip", [1, 0, -1])
def test_near_duplicate_detected_under_flips(flip):
    a = _synthetic(0)
    items = [_feat(a), _feat(cv2.flip(a, flip)), _feat(_synthetic(1)), _feat(_synthetic(2))]
    hashes = np.stack([x[0] for x in items])
    thumbs = np.stack([x[1] for x in items])
    pairs = find_near_duplicates(hashes, thumbs, hash_thr=4, ncc_thr=0.85)
    assert [(i, j) for i, j, *_ in pairs] == [(0, 1)]


def test_ncc_gate_rejects_hash_only_match():
    a = _synthetic(0)
    hashes = np.stack([dhash_variants(a)] * 2)  # özdeş hash
    other = thumbnail(_synthetic(5))
    thumbs = np.stack([thumbnail(a), other])
    assert find_near_duplicates(hashes, thumbs, 4, 0.85) == []
    assert len(find_near_duplicates(hashes, thumbs, 4, -1.0)) == 1  # NCC kapalı → kabul


# ── Determinizm + güvenlik korumaları ────────────────────────────────────────


@pytest.fixture()
def mini_src(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    rng = np.random.default_rng(7)
    for i in range(30):
        split = ["train", "valid", "test"][i % 3]
        g = cv2.resize(cv2.GaussianBlur(rng.integers(0, 255, (48, 48), dtype=np.uint8), (0, 0), 2), (96, 96))
        d = src / split
        (d / "images").mkdir(parents=True, exist_ok=True)
        (d / "labels").mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d / "images" / f"s{i}_jpg.rf.{i}.jpg"), cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
        cls = [9, 12, 1, 2, 4][i % 5]
        (d / "labels" / f"s{i}_jpg.rf.{i}.txt").write_text(f"{cls} 0.5 0.5 0.2 0.2\n")
    return src


def _run(src: Path, out: Path, reports: Path, *extra: str) -> int:
    return main(["--src", str(src), "--out", str(out), "--report-dir", str(reports),
                 "--min-test", "hotspot=0", "--workers", "2", "--skip-verify", *extra])


def test_same_seed_is_deterministic_and_seed_matters(mini_src: Path, tmp_path: Path):
    for tag, seed in (("a", 42), ("b", 42), ("c", 7)):
        assert _run(mini_src, tmp_path / tag, tmp_path / f"r{tag}", "--seed", str(seed)) == 0
    assert (tmp_path / "a" / "manifest.csv").read_bytes() == (tmp_path / "b" / "manifest.csv").read_bytes()
    cmp = filecmp.dircmp(tmp_path / "a" / "train" / "labels", tmp_path / "b" / "train" / "labels")
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only

    def split_map(tag):
        with open(tmp_path / tag / "manifest.csv", encoding="utf-8") as f:
            return {r["file"]: r["split"] for r in csv.DictReader(f)}
    assert split_map("a") != split_map("c")  # farklı seed farklı bölme (ince tuz kontrolü)


def test_out_inside_source_rejected(mini_src: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        _run(mini_src, mini_src / "clean", tmp_path / "r")


def test_overwrite_refuses_foreign_directory(mini_src: Path, tmp_path: Path):
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "important.txt").write_text("x")
    with pytest.raises(FileExistsError):
        _run(mini_src, foreign, tmp_path / "r", "--overwrite")
    assert (foreign / "important.txt").exists()


# ── Gerçek veri invariantları (data/ git dışıdır; yoksa atlanır) ─────────────

CLEAN = REPO / "data" / "ges_clean"
RAW = REPO / "data" / "SOLAR PANEL DET.v1i.yolo26"
needs_data = pytest.mark.skipif(not (CLEAN / "manifest.csv").exists(), reason="data/ges_clean yok")


@needs_data
def test_real_clean_no_stem_or_group_leak_across_splits():
    with open(CLEAN / "manifest.csv", encoding="utf-8") as f:
        man = list(csv.DictReader(f))
    for key in ("stem", "group"):
        seen = defaultdict(set)
        for r in man:
            seen[r[key]].add(r["split"])
        assert all(len(v) == 1 for v in seen.values()), key
    # Dosya sistemiyle manifest tutarlı; split başına görüntü = etiket dosyası
    for sp in ("train", "valid", "test"):
        ims = {p.stem for p in (CLEAN / sp / "images").iterdir()}
        lbs = {p.stem for p in (CLEAN / sp / "labels").glob("*.txt")}
        assert ims == lbs
        assert len(ims) == sum(1 for r in man if r["split"] == sp)
    stems_by_split = {sp: {r["stem"] for r in man if r["split"] == sp} for sp in ("train", "valid", "test")}
    assert not stems_by_split["train"] & stems_by_split["test"]
    assert not stems_by_split["train"] & stems_by_split["valid"]
    assert not stems_by_split["valid"] & stems_by_split["test"]


@needs_data
def test_real_clean_labels_are_five_column_unit_range_three_classes():
    counts: Counter = Counter()
    for lbl in CLEAN.glob("*/labels/*.txt"):
        for line in lbl.read_text().splitlines():
            p = line.split()
            assert len(p) == 5, lbl
            c, *v = int(p[0]), *map(float, p[1:])
            assert 0 <= c < 3 and all(0 <= x <= 1 for x in v) and v[2] > 0 and v[3] > 0
            counts[(lbl.parent.parent.name, c)] += 1
    assert counts[("test", 0)] >= 300  # hotspot (#3 kabul kriteri)


@needs_data
@pytest.mark.skipif(not RAW.exists(), reason="ham veri yok")
def test_real_clean_images_are_byte_identical_copies_of_raw():
    with open(CLEAN / "manifest.csv", encoding="utf-8") as f:
        man = list(csv.DictReader(f))
    for r in man[::37]:  # örneklem
        a = RAW / r["source_split"] / "images" / r["file"]
        b = CLEAN / r["split"] / "images" / r["file"]
        assert a.read_bytes() == b.read_bytes()
