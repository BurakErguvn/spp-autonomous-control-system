"""OOS filtresi ve yakın-kopya eşikleri için BAĞIMSIZ doğrulama testleri (tester, #3/#6).

Gerçek veri testleri kodun kendi sınıf kümesini kullanmaz: sabit kaynak sınıf ID'leri ve ham
``.txt.orig`` etiketlerinden beklenen OOS kümesi yeniden hesaplanır, manifest/dizinlerle karşılaştırılır.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.audit_and_fix_dataset import dhash_variants, find_near_duplicates, thumbnail

REPO = Path(__file__).resolve().parent.parent
CLEAN = REPO / "data" / "ges_clean"
RAW = REPO / "data" / "SOLAR PANEL DET.v1i.yolo26"
needs_real = pytest.mark.skipif(
    not ((CLEAN / "manifest.csv").exists() and RAW.exists()), reason="data/ges_clean veya ham veri yok")

# Kaynak sınıf ID'leri (data.yaml): hedefe eşlenenler / OOS termal anomali + Electrical Damage
TARGET_IDS = {0, 1, 2, 5, 6, 9, 12}
OOS_IDS = {3, 7, 8, 10, 11, 13, 14}
NON_DEFECTIVE = 4


def _raw_classes(source_split: str, file: str) -> set[int]:
    d = RAW / source_split / "labels"
    p = d / f"{Path(file).stem}.txt.orig"
    if not p.exists():
        p = d / f"{Path(file).stem}.txt"
    return {int(float(ln.split()[0])) for ln in p.read_text().splitlines() if ln.strip()}


def _manifest() -> list[dict]:
    with open(CLEAN / "manifest.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@needs_real
def test_oos_membership_equals_independent_rule_from_raw_labels():
    """(a)(b)(c): OOS <=> hedef sınıf yok ve en az bir OOS sınıfı var (ham etiketlerden)."""
    wrong = []
    for r in _manifest():
        cl = _raw_classes(r["source_split"], r["file"])
        expected = not (cl & TARGET_IDS) and bool(cl & OOS_IDS)
        if (r["placed_in"] == "oos") != expected or (r["oos"] == "1") != expected:
            wrong.append(r["file"])
    assert not wrong, wrong[:5]


@needs_real
def test_retained_backgrounds_are_only_non_defective_or_unlabeled_and_oos_labels_empty():
    """(d)(e): split dizinlerinde hedefsiz kalan görüntüler yalnız Non Defective / etiketsiz; oos etiketleri boş."""
    for r in _manifest():
        if r["placed_in"] not in ("train", "valid", "test"):
            continue
        lbl = CLEAN / r["placed_in"] / "labels" / f"{Path(r['file']).stem}.txt"
        if lbl.read_text().strip():
            continue
        cl = _raw_classes(r["source_split"], r["file"])
        assert cl <= {NON_DEFECTIVE}, (r["file"], cl)
    lbls = list((CLEAN / "oos" / "labels").glob("*.txt"))
    imgs = {p.stem for p in (CLEAN / "oos" / "images").iterdir()}
    assert imgs == {p.stem for p in lbls}
    assert all(not p.read_text().strip() for p in lbls)


@needs_real
def test_groups_and_stems_never_span_eval_splits_by_placed_and_assigned_split():
    man = _manifest()
    for attr in ("placed_in", "split"):
        for key in ("group", "stem"):
            seen: dict[str, set[str]] = defaultdict(set)
            for r in man:
                if r[attr] in ("train", "valid", "test"):
                    seen[r[key]].add(r[attr])
            assert all(len(v) == 1 for v in seen.values()), (attr, key)


@needs_real
def test_split_ratios_and_hotspot_floor_after_filter():
    man = [r for r in _manifest() if r["placed_in"] in ("train", "valid", "test")]
    n = Counter(r["placed_in"] for r in man)
    tot = sum(n.values())
    assert 0.78 < n["train"] / tot < 0.84 and 0.08 < n["valid"] / tot < 0.12 and 0.08 < n["test"] / tot < 0.12
    hot = sum(1 for p in (CLEAN / "test" / "labels").glob("*.txt")
              for x in p.read_text().splitlines() if x.split()[0] == "0")
    assert hot >= 300


def _blurred_noise(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return cv2.resize(cv2.GaussianBlur(rng.integers(0, 255, (48, 48), dtype=np.uint8), (0, 0), 2), (160, 160))


def test_ncc_only_does_not_merge_pairs_below_threshold():
    """Negatif durum: dHash eşiği dışı ve NCC < ncc_only_thr olan çift birleşmemeli."""
    g = [_blurred_noise(i) for i in range(2)]
    hashes = np.stack([dhash_variants(x) for x in g])
    thumbs = np.stack([thumbnail(x) for x in g])
    cross = max(float(thumbs[0].reshape(-1) @ v.reshape(-1))
                for v in (thumbs[1], thumbs[1][:, ::-1], thumbs[1][::-1, :], thumbs[1][::-1, ::-1]))
    assert cross < 0.9  # ilgisiz doku
    assert find_near_duplicates(hashes, thumbs, hash_thr=0, ncc_thr=0.9, ncc_only_thr=0.93) == []
    # aynı çift eşik NCC'nin altına indirilince birleşir (eşik gerçekten kullanılıyor)
    got = find_near_duplicates(hashes, thumbs, hash_thr=0, ncc_thr=0.9, ncc_only_thr=cross - 0.01)
    assert [(i, j) for i, j, *_ in got] == [(0, 1)]


def test_ncc_only_merges_flipped_twin_without_dhash_match():
    """Çevirilmiş ikiz: dHash adayı yok, NCC-only çevirme duyarsız yakalar."""
    a = _blurred_noise(7)
    b = cv2.flip(a, 1)
    hashes = np.stack([dhash_variants(_blurred_noise(1)), dhash_variants(_blurred_noise(2))])  # ilgisiz hash
    thumbs = np.stack([thumbnail(a), thumbnail(b)])
    got = find_near_duplicates(hashes, thumbs, hash_thr=0, ncc_thr=0.9, ncc_only_thr=0.93)
    assert [(i, j) for i, j, *_ in got] == [(0, 1)] and got[0][3] > 0.99
