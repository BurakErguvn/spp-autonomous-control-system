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
        assert len(ims) == sum(1 for r in man if r["placed_in"] == sp)
    stems_by_split = {sp: {r["stem"] for r in man if r["placed_in"] == sp} for sp in ("train", "valid", "test")}
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
        if r["placed_in"] == "dropped":
            continue
        b = CLEAN / r["placed_in"] / "images" / r["file"]
        assert a.read_bytes() == b.read_bytes()


# ── Kapsam dışı (OOS) filtresi + eşik parametreleri (#3, #6) ─────────────────

from scripts.audit_and_fix_dataset import (  # noqa: E402
    OOS_DEFAULT_CLASSES,
    ImageRecord,
    LabelRow,
    mark_oos,
    ncc_leakage,
    parse_args,
    place_records,
    resolve_oos_classes,
)
from scripts.train_yolo26 import CLASS_REMAP  # noqa: E402

SRC_NAMES = [
    "Bird Drop", "Defective", "Dusty", "Electrical Damage", "Non Defective",
    "Physical Damage", "Snow", "MultiByPassed", "MultiDiode", "MultiHotSpot",
    "SingleByPassed", "SingleDiode", "SingleHotSpot", "StringOpenCircuit",
    "StringReversedPolarity",
]


def test_default_thresholds_are_8_090_and_ncc_only_093():
    args = parse_args([])
    assert (args.hash_thr, args.ncc_thr, args.ncc_only_thr) == (8, 0.90, 0.93)
    assert args.oos_mode == "separate"
    assert tuple(args.oos_classes) == OOS_DEFAULT_CLASSES
    assert "Non Defective" not in OOS_DEFAULT_CLASSES
    assert "Electrical Damage" in OOS_DEFAULT_CLASSES  # kullanıcı kararı (#6)


def test_resolve_oos_classes_names_ids_and_unknown():
    assert resolve_oos_classes(["multidiode", "13"], SRC_NAMES) == {8, 13}
    with pytest.raises(ValueError):
        resolve_oos_classes(["Nope"], SRC_NAMES)


def _rec(split: str, classes: list[int]) -> ImageRecord:
    rows = [LabelRow(c, 0.5, 0.5, 0.2, 0.2, False) for c in classes]
    rec = ImageRecord(image=Path(f"x{split}{classes}.jpg"), source_split=split, stem="s", rows=rows,
                      label_stats=Counter(), label_source="txt.orig")
    rec.split = split
    rec.out_rows = [r._replace(cls=CLASS_REMAP[r.cls]) for r in rows if CLASS_REMAP[r.cls] is not None]
    return rec


def test_mark_oos_keeps_non_defective_unlabeled_mixed():
    oos_ids = resolve_oos_classes(list(OOS_DEFAULT_CLASSES), SRC_NAMES)
    cases = {
        "diode": _rec("train", [8, 11]),            # yalnız termal anomali → OOS
        "nondef": _rec("train", [4]),               # gerçek arka plan → kalır
        "unlabeled": _rec("train", []),             # etiketsiz → kalır
        "elec": _rec("train", [3]),                 # Electrical Damage → OOS (kullanıcı kararı)
        "elec_nondef": _rec("train", [3, 4]),       # Electrical Damage + Non Defective → OOS
        "elec_hot": _rec("train", [3, 12]),         # hedef kutusu var → kalır
        "mixed": _rec("train", [12, 8]),            # hotspot + MultiDiode → kalır
        "diode_nondef": _rec("train", [8, 4]),      # anomali + Non Defective → OOS
    }
    mark_oos(list(cases.values()), oos_ids, SRC_NAMES)
    flags = {k: v.is_oos for k, v in cases.items()}
    assert flags == {"diode": True, "nondef": False, "unlabeled": False, "elec": True,
                     "elec_nondef": True, "elec_hot": False, "mixed": False, "diode_nondef": True}
    assert cases["diode"].oos_classes == ("MultiDiode", "SingleDiode")
    # Karma görüntüde anomali sınıfı kayıtlı kalır ama is_oos değil
    assert cases["mixed"].oos_classes == ("MultiDiode",)


def test_place_records_modes():
    oos_ids = resolve_oos_classes(list(OOS_DEFAULT_CLASSES), SRC_NAMES)

    def placed(mode: str) -> dict[str, str]:
        recs = [_rec("train", [8]), _rec("valid", [8]), _rec("test", [4]), _rec("test", [8])]
        mark_oos(recs, oos_ids, SRC_NAMES)
        place_records(recs, mode)
        return {f"{r.split}{int(r.is_oos)}": r.placed_in for r in recs}

    assert placed("separate") == {"train1": "oos", "valid1": "oos", "test0": "test", "test1": "oos"}
    assert placed("drop") == {"train1": "", "valid1": "", "test0": "test", "test1": ""}
    assert placed("keep") == {"train1": "", "valid1": "valid", "test0": "test", "test1": "test"}
    with pytest.raises(ValueError):
        place_records([], "bogus")


def test_ncc_only_candidates_catch_what_dhash_misses():
    a = thumbnail(_synthetic(0))
    hashes = np.stack([dhash_variants(_synthetic(1)), dhash_variants(_synthetic(2))])  # alakasız hash
    thumbs = np.stack([a, a])
    assert find_near_duplicates(hashes, thumbs, hash_thr=4, ncc_thr=0.9) == []
    got = find_near_duplicates(hashes, thumbs, hash_thr=4, ncc_thr=0.9, ncc_only_thr=0.95)
    assert [(i, j) for i, j, *_ in got] == [(0, 1)] and got[0][3] == pytest.approx(1.0, abs=1e-4)


def test_ncc_leakage_counts_flipped_twin_and_ignores_unplaced():
    g = [_synthetic(i) for i in range(4)]
    thumbs = np.stack([thumbnail(g[0], 24), thumbnail(cv2.flip(g[0], 1), 24),
                       thumbnail(g[1], 24), thumbnail(g[2], 24), thumbnail(g[0], 24)])
    out = ncc_leakage(thumbs, ["train", "test", "test", "valid", ""])
    assert out["test-train"]["images"] == 2
    assert out["test-train"]["ge_0.90"] == 1 and out["test-train"]["ge_0.97"] == 1
    assert out["valid-train"]["ge_0.90"] == 0
    assert out["test-valid"]["images"] == 2


@pytest.fixture()
def oos_src(tmp_path: Path) -> Path:
    """Hotspot, MultiDiode ve Electrical Damage (OOS), Non Defective, karma ve etiketsiz görüntüler."""
    src = tmp_path / "oos_src"
    rng = np.random.default_rng(3)
    cycle = ["9 0.5 0.5 0.2 0.2", "8 0.5 0.5 0.2 0.2", "4 0.5 0.5 0.2 0.2", "3 0.5 0.5 0.2 0.2",
             "9 0.3 0.3 0.2 0.2\n8 0.7 0.7 0.2 0.2", "", "1 0.5 0.5 0.2 0.2"]
    for i in range(70):
        split = ["train", "valid", "test"][i % 3]
        g = cv2.resize(cv2.GaussianBlur(rng.integers(0, 255, (48, 48), dtype=np.uint8), (0, 0), 2), (96, 96))
        d = src / split
        (d / "images").mkdir(parents=True, exist_ok=True)
        (d / "labels").mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d / "images" / f"o{i}_jpg.rf.{i}.jpg"), cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
        (d / "labels" / f"o{i}_jpg.rf.{i}.txt").write_text(cycle[i % len(cycle)] + "\n")
    return src


def _manifest(out: Path) -> list[dict]:
    with open(out / "manifest.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _run_oos(src: Path, out: Path, reports: Path, *extra: str) -> int:
    return _run(src, out, reports, "--ratios", "0.5", "0.25", "0.25", *extra)


def test_oos_separate_default_writes_oos_set_and_keeps_split_assignment(oos_src: Path, tmp_path: Path):
    out = tmp_path / "sep"
    assert _run_oos(oos_src, out, tmp_path / "rs") == 0
    man = _manifest(out)
    oos_rows = [r for r in man if r["oos"] == "1"]
    assert oos_rows and {r["oos_source_classes"] for r in oos_rows} == {"MultiDiode", "Electrical Damage"}
    assert all(r["placed_in"] == "oos" for r in oos_rows)
    # Atanmış bölme korunur (train grubundan gelenler ayırt edilebilir)
    assert {r["split"] for r in oos_rows} == {"train", "valid", "test"}
    # Non Defective, karma, etiketsiz kalır; Electrical Damage OOS'a gider
    kept_files = {p.name for sp in ("train", "valid", "test") for p in (out / sp / "images").iterdir()}
    for r in man:
        label_cls = [int(x.split()[0]) for x in
                     (out / r["placed_in"] / "labels" / f"{Path(r['file']).stem}.txt").read_text().splitlines()
                     ] if r["placed_in"] != "dropped" else []
        if r["oos"] == "1":
            assert r["file"] not in kept_files and label_cls == []
        else:
            assert r["file"] in kept_files
    nondef = [r for r in man if r["placed_in"] in ("train", "valid", "test") and r["n_rows_source"] == "1"
              and r["n_rows_out"] == "0"]
    assert nondef, "Non Defective / etiketsiz arka planlar korunmalı"
    n_oos_files = len(list((out / "oos" / "images").iterdir()))
    assert n_oos_files == len(oos_rows)
    # Grup bütünlüğü atanmış bölmeler üzerinden
    g = defaultdict(set)
    for r in man:
        g[r["group"]].add(r["split"])
    assert all(len(v) == 1 for v in g.values())


def test_oos_modes_do_not_change_split_assignment(oos_src: Path, tmp_path: Path):
    maps = {}
    for mode in ("separate", "keep", "drop"):
        out = tmp_path / mode
        assert _run_oos(oos_src, out, tmp_path / f"r{mode}", "--oos-mode", mode) == 0
        maps[mode] = {r["file"]: (r["group"], r["split"], r["placed_in"]) for r in _manifest(out)}
    base = {f: v[:2] for f, v in maps["separate"].items()}
    assert all({f: v[:2] for f, v in m.items()} == base for m in maps.values())
    oos = {f for f, v in maps["separate"].items() if v[2] == "oos"}
    assert oos and all(maps["drop"][f][2] == "dropped" for f in oos)
    assert not (tmp_path / "drop" / "oos").exists()
    for f in oos:
        sp = maps["keep"][f][2]
        assert sp == ("dropped" if maps["keep"][f][1] == "train" else maps["keep"][f][1])
    # Hiçbir modda oos dışı görüntünün yeri değişmez
    for f, v in maps["separate"].items():
        if v[2] != "oos":
            assert maps["keep"][f][2] == maps["drop"][f][2] == v[2]


def test_oos_classes_empty_disables_filter(oos_src: Path, tmp_path: Path):
    out = tmp_path / "noflt"
    assert main(["--src", str(oos_src), "--out", str(out), "--report-dir", str(tmp_path / "rn"),
                 "--min-test", "hotspot=0", "--workers", "2", "--skip-verify",
                 "--ratios", "0.5", "0.25", "0.25", "--oos-classes"]) == 0
    assert all(r["oos"] == "0" and r["placed_in"] == r["split"] for r in _manifest(out))
    assert not (out / "oos").exists()


def test_keep_original_classes_gives_same_split_as_three_class(oos_src: Path, tmp_path: Path):
    assert _run_oos(oos_src, tmp_path / "c3", tmp_path / "r3") == 0
    assert _run_oos(oos_src, tmp_path / "c15", tmp_path / "r15", "--keep-original-classes") == 0
    a = {r["file"]: (r["group"], r["split"]) for r in _manifest(tmp_path / "c3")}
    b = {r["file"]: (r["group"], r["split"]) for r in _manifest(tmp_path / "c15")}
    assert a == b
    # 15 sınıflı modda hedef kutusu eşlemesi kalkmaz: OOS işaretlenmez
    assert all(r["oos"] == "0" for r in _manifest(tmp_path / "c15"))


@needs_data
def test_real_clean_oos_set_is_separated_and_consistent():
    man = _manifest(CLEAN)
    oos = [r for r in man if r["oos"] == "1"]
    if not oos:
        pytest.skip("data/ges_clean OOS filtresiz üretilmiş")
    assert all(r["placed_in"] in ("oos", "dropped") or r["split"] != "train" for r in oos)
    in_splits = {p.name for sp in ("train", "valid", "test") for p in (CLEAN / sp / "images").iterdir()}
    oos_dir = CLEAN / "oos"
    if oos_dir.exists():
        oos_files = {p.name for p in (oos_dir / "images").iterdir()}
        assert oos_files == {r["file"] for r in oos if r["placed_in"] == "oos"}
        assert not oos_files & in_splits
        assert all((p.read_text() == "") for p in (oos_dir / "labels").glob("*.txt"))
    # OOS yalnız termal anomali sınıfı taşır; Non Defective / Electrical Damage tek başına OOS değil
    allowed = set(OOS_DEFAULT_CLASSES)
    for r in oos:
        assert set(r["oos_source_classes"].split("|")) <= allowed
        assert r["n_rows_out"] == "0"
    # Her OOS görüntüsü, atanmış bölmesinin grubuyla tutarlı (grup tek bölmede)
    groups = defaultdict(set)
    for r in man:
        groups[r["group"]].add(r["split"])
    assert all(len(v) == 1 for v in groups.values())


@pytest.mark.skipif(not (REPO / "outputs" / "reports" / "dataset_audit.json").exists(), reason="rapor yok")
def test_committed_report_records_thresholds_and_zero_corrupt():
    import json
    rep = json.loads((REPO / "outputs" / "reports" / "dataset_audit.json").read_text(encoding="utf-8"))
    p = rep["params"]
    assert (p["hash_thr"], p["ncc_thr"], p["ncc_only_thr"]) == (8, 0.90, 0.93)
    assert "Electrical Damage" in p["oos_classes"]
    assert rep["leakage_after"]["groups_spanning_multiple_splits"] == 0
    assert rep["ultralytics_verify"]["total_corrupt"] == 0
    assert rep["oos"]["removed_total"]["train"] > 0
