"""GES veri seti denetim ve temizleme scripti.

Kaynak veri setine (Roboflow 'SOLAR PANEL DET.v1i.yolo26') DOKUNMADAN yeni bir
temiz kopya üretir:

1. Poligon satırlarını (5'ten fazla sütun) eksen hizalı bbox'a çevirir; böylece
   hiçbir etiket dosyası bbox + poligon karışık kalmaz.
2. Görüntüleri kaynak gövdesi (``.rf.`` öncesi) + algısal hash (dHash, çevirme
   duyarsız) ile gruplar; dHash adayları 32x32 küçük resim korelasyonu (NCC) ile
   doğrulanır. Ardından grup bazlı, sınıf tabakalı yeni train/valid/test bölmesi
   yapar — hiçbir grup birden fazla bölmeye düşmez.
3. Modaliteyi (gri/termal ↔ renkli/RGB) tespit eder; sınıf × modalite × bölme
   tablolarını JSON ve Markdown rapora yazar.
4. Sınıf eşleştirmesi yapılandırılabilir (varsayılan: train_yolo26.CLASS_REMAP).
5. Kapsam dışı (OOS) termal anomali içeren, hedef sınıf kutusu olmayan görüntüleri
   (Diode/ByPassed/StringOpenCircuit/ReversedPolarity + Electrical Damage) eğitimden çıkarır. Bölme
   TÜM görüntülerle yapılır, filtre bölmeden SONRA uygulanır (aynı sahnenin anomali
   ve hedef kareleri aynı gruba düşer; bkz. ``OOS_DEFAULT_CLASSES``).
   Çıkarılanlar ``--oos-mode`` ile ``oos/`` kümesine yazılır / atılır / valid-test'te korunur.
6. Temiz veri seti için yeni data YAML yazar ve (varsa) Ultralytics
   ``verify_image_label`` ile her görüntü/etiket çiftini doğrular.

Kaynak etiketler: ``labels/*.txt.orig`` varsa o (orijinal 15 sınıf) okunur,
yoksa ``labels/*.txt``. İki durumda da sınıf ID'leri ORİJİNAL kabul edilir.

Bölme taksonomiden bağımsızdır: tabakalama orijinal 15 sınıf + modalite
üzerinden yapılır, bu yüzden farklı bir --remap-config ile tekrar çalıştırmak
aynı bölmeyi üretir (aynı seed ile).

Kullanım:
    python scripts/audit_and_fix_dataset.py
    python scripts/audit_and_fix_dataset.py --out data/ges_clean --overwrite
    python scripts/audit_and_fix_dataset.py --remap-config my_remap.yaml
    python scripts/audit_and_fix_dataset.py --keep-original-classes
    python scripts/audit_and_fix_dataset.py --hash-thr 8 --ncc-thr 0.90 --ncc-only-thr 0.93
    python scripts/audit_and_fix_dataset.py --oos-mode keep      # valid/test'te koru

--remap-config YAML biçimi:
    names: [hotspot, mikro_catlak, tozlanma]
    remap:            # orijinal ID → yeni ID; null/eksik = kaldır
      9: 0
      12: 0
      1: 1
      ...

Çıktı:
    data/ges_clean/{train,valid,test}/{images,labels}
    data/ges_clean/oos/{images,labels}   — çıkarılan kapsam dışı arka planlar (--oos-mode separate)
    data/ges_clean/manifest.csv          — görüntü → grup/bölme/yerleşim/modalite/OOS kaynak sınıfları
    data/ges_clean.yaml                  — Ultralytics data YAML
    outputs/reports/dataset_audit.json   — denetim raporu
    outputs/reports/dataset_audit.md     — rapor özeti
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import shutil
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_yolo26 import CLASS_NAMES, CLASS_REMAP  # noqa: E402

logger = logging.getLogger("audit_dataset")

SRC_DIR = Path("data") / "SOLAR PANEL DET.v1i.yolo26"
OUT_DIR = Path("data") / "ges_clean"
REPORTS_DIR = Path("outputs") / "reports"
SPLITS = ("train", "valid", "test")
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Kaynak data.yaml okunamazsa kullanılacak orijinal sınıf adları
SOURCE_NAMES_FALLBACK = [
    "Bird Drop", "Defective", "Dusty", "Electrical Damage", "Non Defective",
    "Physical Damage", "Snow", "MultiByPassed", "MultiDiode", "MultiHotSpot",
    "SingleByPassed", "SingleDiode", "SingleHotSpot", "StringOpenCircuit",
    "StringReversedPolarity",
]

# Kapsam dışı (OOS) termal anomali sınıfları (kaynak sınıf adları): remap sonrası hedef kutusu
# kalmayan ve bunlardan en az birini içeren görüntüler eğitim/değerlendirme arka planından çıkarılır.
# Electrical Damage kullanıcı kararıyla (#6) listeye alındı: hedef kutusu kalmayan ve bu sınıfı
# içeren görüntüler (Electrical Damage + Non Defective dahil) OOS'a gider.
# Non Defective listede YOK: tek başına gerçek "sağlam" arka plandır, korunur.
OOS_DEFAULT_CLASSES = (
    "MultiByPassed", "MultiDiode", "SingleByPassed", "SingleDiode",
    "StringOpenCircuit", "StringReversedPolarity", "Electrical Damage",
)
OOS_MODES = ("separate", "keep", "drop")
OOS_DIR = "oos"
# Bölmeler arası küçük-resim NCC sızıntı ölçümü
EVAL_THUMB_SIZE = 24
NCC_LEAK_THRESHOLDS = (0.90, 0.95, 0.97)
# Bbox kenarı bundan küçükse (normalize) dejenere kabul edilir
MIN_BOX_SIZE = 1e-4
# Bayt başına bit sayısı — Hamming mesafesi için
_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


# ── Etiket ayrıştırma ────────────────────────────────────────────────────────


class LabelRow(NamedTuple):
    """Tek bir YOLO bbox satırı (normalize xywh)."""

    cls: int
    cx: float
    cy: float
    w: float
    h: float
    from_polygon: bool


def _clip_box(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float, float] | None:
    """xyxy kutuyu [0,1]'e kırpar ve xywh döndürür; dejenere ise None."""
    x1, x2 = max(0.0, min(x1, x2)), min(1.0, max(x1, x2))
    y1, y2 = max(0.0, min(y1, y2)), min(1.0, max(y1, y2))
    w, h = x2 - x1, y2 - y1
    if w < MIN_BOX_SIZE or h < MIN_BOX_SIZE:
        return None
    return (x1 + w / 2, y1 + h / 2, w, h)


def polygon_to_bbox(coords: list[float]) -> tuple[float, float, float, float] | None:
    """Poligon noktalarını (x1 y1 x2 y2 ...) eksen hizalı xywh kutuya çevirir.

    Args:
        coords: Normalize edilmiş, çift sayıda koordinat.

    Returns:
        (cx, cy, w, h) ya da kutu dejenere ise None.
    """
    xs, ys = coords[0::2], coords[1::2]
    return _clip_box(min(xs), min(ys), max(xs), max(ys))


def parse_label_text(text: str) -> tuple[list[LabelRow], Counter]:
    """YOLO etiket metnini ayrıştırır; poligonları bbox'a çevirir.

    Returns:
        (satırlar, istatistik) — istatistik anahtarları: bbox, polygon,
        malformed, degenerate, duplicate.
    """
    rows: list[LabelRow] = []
    stats: Counter = Counter()
    seen: set[tuple] = set()
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            cls = int(float(parts[0]))
            vals = [float(v) for v in parts[1:]]
        except ValueError:
            stats["malformed"] += 1
            continue

        if len(vals) == 4:
            cx, cy, w, h = vals
            box = _clip_box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            is_poly = False
        elif len(vals) >= 6 and len(vals) % 2 == 0:
            box = polygon_to_bbox(vals)
            is_poly = True
        else:
            stats["malformed"] += 1
            continue

        stats["polygon" if is_poly else "bbox"] += 1
        if box is None:
            stats["degenerate"] += 1
            continue
        key = (cls, *(round(v, 6) for v in box))
        if key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(key)
        rows.append(LabelRow(cls, *box, from_polygon=is_poly))
    return rows, stats


def format_label_rows(rows: list[LabelRow]) -> str:
    """Satırları 5 sütunlu YOLO detect biçiminde yazar."""
    return "\n".join(f"{r.cls} {r.cx:.6f} {r.cy:.6f} {r.w:.6f} {r.h:.6f}" for r in rows)


def apply_remap(rows: list[LabelRow], remap: dict[int, int | None]) -> list[LabelRow]:
    """Sınıf ID'lerini eşler; eşlemesi None/eksik olanları kaldırır.

    Birleşen sınıflarda (ör. Defective + Physical Damage → mikro_catlak) aynı
    kutu iki kez kalabileceği için yazılan biçimde yinelenenler de atılır.
    """
    out = []
    seen: set[str] = set()
    for r in rows:
        new_id = remap.get(r.cls)
        if new_id is None:
            continue
        row = r._replace(cls=new_id)
        key = format_label_rows([row])
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


# ── Görüntü özellikleri ──────────────────────────────────────────────────────


def source_stem(filename: str) -> str:
    """Roboflow dosya adından kaynak gövdesini çıkarır ('0266_jpg.rf.<hash>.jpg' → '0266_jpg')."""
    return filename.split(".rf.")[0] if ".rf." in filename else Path(filename).stem


def dhash_variants(gray: np.ndarray) -> np.ndarray:
    """64 bit dHash'i 4 çevirme varyantıyla döndürür: (4, 8) uint8.

    Sıra: orijinal, yatay çevirme, dikey çevirme, ikisi birden.
    """
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    variants = (small, small[:, ::-1], small[::-1, :], small[::-1, ::-1])
    return np.stack([np.packbits((v[:, 1:] > v[:, :-1]).flatten()) for v in variants])


def thumbnail(gray: np.ndarray, size: int = 32) -> np.ndarray:
    """Sıfır ortalamalı, birim normlu küçük resim (NCC için)."""
    t = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    t -= t.mean()
    return t / (np.linalg.norm(t) + 1e-9)


def chroma_score(bgr: np.ndarray) -> float:
    """Kanallar arası ortalama mutlak fark; gri görüntüde ~0."""
    s = cv2.resize(bgr, (64, 64), interpolation=cv2.INTER_AREA).astype(np.int16)
    b, g, r = s[..., 0], s[..., 1], s[..., 2]
    return float((np.abs(b - g).mean() + np.abs(g - r).mean() + np.abs(b - r).mean()) / 3)


def image_features(path: Path) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """(chroma, dhash_variants, thumbnail32, eval_thumbnail24) döndürür.

    İlk üçü gruplama içindir; 24x24 küçük resim yalnız bağımsız sızıntı ölçümünde kullanılır.
    """
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Görüntü okunamadı: {path}")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return chroma_score(bgr), dhash_variants(gray), thumbnail(gray), thumbnail(gray, EVAL_THUMB_SIZE)


# ── Gruplama ─────────────────────────────────────────────────────────────────


class UnionFind:
    """Basit ayrık küme yapısı."""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def find_near_duplicates(
    hashes: np.ndarray,
    thumbs: np.ndarray,
    hash_thr: int,
    ncc_thr: float,
    block: int = 256,
    ncc_only_thr: float | None = None,
) -> list[tuple[int, int, int, float]]:
    """dHash (çevirme duyarsız) + NCC ile yakın kopya çiftlerini bulur.

    Args:
        hashes: (N, 4, 8) dHash varyantları.
        thumbs: (N, S, S) normalize küçük resimler.
        hash_thr: Maksimum Hamming mesafesi (aday eşiği).
        ncc_thr: Adayı kabul etmek için minimum korelasyon. ``<= -1`` ise
            doğrulama yapılmaz (salt dHash).
        ncc_only_thr: Verilirse dHash'e bakmadan NCC'si (4 çevirme, en iyisi) bu
            değerin üstündeki çiftler de eklenir (dHash'in kaçırdığı ardışık kareler).

    Returns:
        (i, j, hamming, ncc) listesi, i < j.
    """
    n = len(hashes)
    base = hashes[:, 0, :]  # (N, 8)
    flat_thumbs = thumbs.reshape(n, -1)
    flipped = [
        thumbs,
        thumbs[:, :, ::-1],
        thumbs[:, ::-1, :],
        thumbs[:, ::-1, ::-1],
    ]
    pairs: list[tuple[int, int, int, float]] = []
    for start in range(0, n, block):
        stop = min(start + block, n)
        # (B, N, 4) — i'nin orijinali ile j'nin her çevirme varyantı arası mesafe
        xor = base[start:stop, None, None, :] ^ hashes[None, :, :, :]
        dist = _POPCOUNT[xor].sum(-1, dtype=np.int16)
        best_flip = dist.argmin(-1)
        best = dist.min(-1)
        accepted: set[tuple[int, int]] = set()
        for bi, j in zip(*np.nonzero(best <= hash_thr)):
            i = start + int(bi)
            if j <= i:
                continue
            f = int(best_flip[bi, j])
            ncc = float(flat_thumbs[i] @ flipped[f][j].reshape(-1))
            if ncc >= ncc_thr:
                pairs.append((i, int(j), int(best[bi, j]), ncc))
                accepted.add((i, int(j)))
        if ncc_only_thr is not None:
            ncc_best = np.max(
                [flat_thumbs[start:stop] @ ft.reshape(n, -1).T for ft in flipped], axis=0)
            for bi, j in zip(*np.nonzero(ncc_best >= ncc_only_thr)):
                i = start + int(bi)
                if j <= i or (i, int(j)) in accepted:
                    continue
                pairs.append((i, int(j), int(best[bi, j]), float(ncc_best[bi, j])))
    return pairs


def build_groups(stems: list[str], pairs: list[tuple[int, int, int, float]]) -> list[int]:
    """Aynı kaynak gövdesi ve yakın kopyaları birleştirir; her görüntü için grup ID döndürür."""
    uf = UnionFind(len(stems))
    first: dict[str, int] = {}
    for i, s in enumerate(stems):
        if s in first:
            uf.union(i, first[s])
        else:
            first[s] = i
    for i, j, *_ in pairs:
        uf.union(i, j)
    roots = [uf.find(i) for i in range(len(stems))]
    # Kompakt 0..G-1 ID'leri
    remap: dict[int, int] = {}
    return [remap.setdefault(r, len(remap)) for r in roots]


# ── Bölme ────────────────────────────────────────────────────────────────────


def stratified_group_split(
    group_features: np.ndarray,
    ratios: tuple[float, ...],
    seed: int,
) -> list[int]:
    """Grupları, özellik toplamları hedef oranlara en yakın kalacak şekilde böler.

    Açgözlü yöntem: gruplar büyükten küçüğe (eşitlikte seed'li rastgele sıra)
    işlenir; her grup, normalize karesel sapmayı en az artıran bölmeye atanır.

    Args:
        group_features: (G, F) negatif olmayan sayımlar (ilk sütun: görüntü sayısı).
        ratios: Bölme oranları (toplamı 1'e normalize edilir).
        seed: Rastgelelik tohumu.

    Returns:
        Her grup için bölme indeksi.
    """
    feats = np.asarray(group_features, dtype=np.float64)
    r = np.asarray(ratios, dtype=np.float64)
    r = r / r.sum()
    totals = feats.sum(0)
    scale = np.where(totals > 0, totals, 1.0) ** 2
    targets = r[:, None] * totals[None, :]  # (S, F)
    current = np.zeros_like(targets)

    rng = random.Random(seed)
    order = list(range(len(feats)))
    rng.shuffle(order)
    order.sort(key=lambda g: -feats[g, 0])  # stabil sıralama: büyük gruplar önce

    assignment = [0] * len(feats)
    for g in order:
        v = feats[g]
        # (cur + v - T)^2 - (cur - T)^2 = v * (2 (cur - T) + v)
        delta = ((v * (2 * (current - targets) + v)) / scale).sum(1)
        s = int(np.argmin(delta))
        assignment[g] = s
        current[s] += v
    return assignment


# ── Veri yapıları ────────────────────────────────────────────────────────────


@dataclass
class ImageRecord:
    """Kaynak veri setindeki tek görüntü."""

    image: Path
    source_split: str
    stem: str
    rows: list[LabelRow]
    label_stats: Counter
    label_source: str
    modality: str = ""
    chroma: float = 0.0
    group: int = -1
    split: str = ""
    out_rows: list[LabelRow] = field(default_factory=list)
    oos_classes: tuple[str, ...] = ()   # çıkarma kümesindeki kaynak sınıf adları (varsa)
    is_oos: bool = False                # hedef kutusu yok + OOS sınıfı var
    placed_in: str = ""                 # train/valid/test/oos/(boş = yazılmadı)


def load_source_names(src: Path) -> list[str]:
    """Kaynak data.yaml'daki sınıf adlarını okur."""
    yml = src / "data.yaml"
    try:
        names = yaml.safe_load(yml.read_text(encoding="utf-8"))["names"]
        return list(names.values()) if isinstance(names, dict) else list(names)
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        logger.warning("%s okunamadı, varsayılan sınıf adları kullanılıyor.", yml)
        return list(SOURCE_NAMES_FALLBACK)


def load_remap_config(
    path: Path | None, keep_original: bool, source_names: list[str]
) -> tuple[list[str], dict[int, int | None]]:
    """Hedef sınıf adlarını ve eşleştirme tablosunu döndürür."""
    if keep_original:
        return list(source_names), {i: i for i in range(len(source_names))}
    if path is None:
        names, remap = list(CLASS_NAMES), dict(CLASS_REMAP)
    else:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        names = list(cfg["names"])
        remap = {int(k): (None if v is None else int(v)) for k, v in cfg["remap"].items()}
    bad = {v for v in remap.values() if v is not None and not 0 <= v < len(names)}
    if bad:
        raise ValueError(f"Eşleştirmede geçersiz hedef ID'ler: {sorted(bad)} (nc={len(names)})")
    return names, remap


def scan_source(src: Path) -> list[ImageRecord]:
    """Kaynak bölmelerdeki görüntü + etiketleri okur."""
    records: list[ImageRecord] = []
    for split in SPLITS:
        img_dir = src / split / "images"
        lbl_dir = src / split / "labels"
        if not img_dir.exists():
            logger.warning("Görüntü dizini bulunamadı: %s", img_dir)
            continue
        for img in sorted(p for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXTS):
            orig = lbl_dir / f"{img.stem}.txt.orig"
            txt = lbl_dir / f"{img.stem}.txt"
            lbl = orig if orig.exists() else txt
            text = lbl.read_text(encoding="utf-8") if lbl.exists() else ""
            rows, stats = parse_label_text(text)
            if not lbl.exists():
                stats["missing_label_file"] += 1
            records.append(ImageRecord(
                image=img, source_split=split, stem=source_stem(img.name),
                rows=rows, label_stats=stats,
                label_source=("txt.orig" if lbl == orig else "txt") if lbl.exists() else "none",
            ))
    return records


# ── Rapor yardımcıları ───────────────────────────────────────────────────────


def leakage_stats(records: list[ImageRecord], split_attr: str,
                  pairs: list[tuple[int, int, int, float]]) -> dict:
    """Bölmeler arası gövde / grup / yakın kopya sızıntısını ölçer."""
    split_of = [getattr(r, split_attr) for r in records]
    stem_splits: dict[str, set[str]] = defaultdict(set)
    group_splits: dict[int, set[str]] = defaultdict(set)
    for r, s in zip(records, split_of):
        stem_splits[r.stem].add(s)
        group_splits[r.group].add(s)

    def shared(sets: dict, a: str, b: str) -> int:
        return sum(1 for v in sets.values() if a in v and b in v)

    combos = [("train", "valid"), ("train", "test"), ("valid", "test")]
    cross_pairs = Counter(
        "-".join(sorted((split_of[i], split_of[j]))) for i, j, *_ in pairs
        if split_of[i] != split_of[j]
    )
    # Test görüntülerinden kaçının train'de aynı gruptan bir eşi var
    train_groups = {r.group for r, s in zip(records, split_of) if s == "train"}
    test_with_train_twin = sum(
        1 for r, s in zip(records, split_of) if s == "test" and r.group in train_groups
    )
    return {
        "stems_shared": {f"{a}-{b}": shared(stem_splits, a, b) for a, b in combos},
        "groups_shared": {f"{a}-{b}": shared(group_splits, a, b) for a, b in combos},
        "groups_spanning_multiple_splits": sum(len(v) > 1 for v in group_splits.values()),
        "near_duplicate_pairs_across_splits": dict(sorted(cross_pairs.items())),
        "test_images_with_train_twin": test_with_train_twin,
        "test_images": sum(1 for s in split_of if s == "test"),
    }


def class_tables(records: list[ImageRecord], names: list[str], rows_attr: str,
                 split_attr: str) -> dict:
    """{sınıf: {modalite: {bölme: instance}}} ve görüntü-varlık sayımları."""
    inst: dict = {n: {m: dict.fromkeys(SPLITS, 0) for m in ("gray", "rgb")} for n in names}
    imgs: dict = {n: {m: dict.fromkeys(SPLITS, 0) for m in ("gray", "rgb")} for n in names}
    for r in records:
        s = getattr(r, split_attr)
        rows = getattr(r, rows_attr)
        for c, k in Counter(row.cls for row in rows).items():
            name = names[c] if 0 <= c < len(names) else f"cls_{c}"
            inst.setdefault(name, {m: dict.fromkeys(SPLITS, 0) for m in ("gray", "rgb")})
            imgs.setdefault(name, {m: dict.fromkeys(SPLITS, 0) for m in ("gray", "rgb")})
            inst[name][r.modality][s] += k
            imgs[name][r.modality][s] += 1
    return {"instances": inst, "images": imgs}


def image_tables(records: list[ImageRecord], split_attr: str, rows_attr: str) -> dict:
    """Bölme × modalite görüntü sayıları ve arka plan (etiketsiz) görüntüler."""
    out = {m: dict.fromkeys(SPLITS, 0) for m in ("gray", "rgb")}
    bg = {m: dict.fromkeys(SPLITS, 0) for m in ("gray", "rgb")}
    for r in records:
        s = getattr(r, split_attr)
        out[r.modality][s] += 1
        if not getattr(r, rows_attr):
            bg[r.modality][s] += 1
    return {"images": out, "background_images": bg}


def mixed_file_stats(records: list[ImageRecord], remap: dict[int, int | None],
                     names: list[str]) -> dict:
    """Mevcut düzende (yalnız remap, dönüşüm yok) bbox+poligon karışık kalan dosyalar.

    Ultralytics bir dosyada >6 sütunlu satır görünce TÜM satırları poligon sayar;
    5 sütunlu bbox satırları (cx,cy),(w,h) noktaları olarak okunup bozulur
    (eski sürümlerde dosya tamamen düşürülür).
    """
    out: dict = {}
    for split in SPLITS:
        files_raw = files_remapped = 0
        bbox_rows_affected: Counter = Counter()
        for r in (x for x in records if x.source_split == split):
            kinds = {row.from_polygon for row in r.rows}
            if len(kinds) == 2:
                files_raw += 1
            # train_yolo26.remap_labels gibi: yalnız ID eşle, yineleneni atma
            kept = [row._replace(cls=remap[row.cls]) for row in r.rows
                    if remap.get(row.cls) is not None]
            if len({row.from_polygon for row in kept}) == 2:
                files_remapped += 1
                for row in kept:
                    bbox_rows_affected[names[row.cls]] += 1
        out[split] = {
            "mixed_files_original_classes": files_raw,
            "mixed_files_after_remap": files_remapped,
            "instances_in_mixed_files_after_remap": dict(bbox_rows_affected),
        }
    return out


def ncc_leakage(thumbs: np.ndarray, split_of: list[str],
                thresholds: tuple[float, ...] = NCC_LEAK_THRESHOLDS) -> dict:
    """Bölmeler arası küçük-resim NCC sızıntısı (gruplamadan bağımsız ölçüt).

    Her (a, b) bölme çifti için a'daki her görüntünün b'deki en benzer görüntüyle
    (4 çevirme üzerinden) max-NCC değeri hesaplanır; eşiği aşan a-görüntüleri sayılır.
    Gruplamada 32x32 küçük resim kullanıldığı için bu ölçüt (24x24) ondan bağımsızdır.

    Args:
        thumbs: (N, S, S) sıfır ortalamalı birim normlu küçük resimler.
        split_of: Her görüntünün bölmesi; ``""`` olanlar (yazılmayanlar) hariç tutulur.
        thresholds: Sayılacak NCC eşikleri.

    Returns:
        {"test-train": {"images": n_test, "ge_0.90": k, ...}, ...}
    """
    n = len(thumbs)
    flat = thumbs.reshape(n, -1)
    variants = [flat] + [
        t.reshape(n, -1) for t in (thumbs[:, :, ::-1], thumbs[:, ::-1, :], thumbs[:, ::-1, ::-1])
    ]
    split_arr = np.asarray(split_of)
    out: dict = {}
    for a, b in (("test", "train"), ("valid", "train"), ("test", "valid")):
        ia, ib = np.where(split_arr == a)[0], np.where(split_arr == b)[0]
        best = np.full(len(ia), -1.0)
        if len(ia) and len(ib):
            for v in variants:
                best = np.maximum(best, (flat[ia] @ v[ib].T).max(1))
        out[f"{a}-{b}"] = {"images": int(len(ia)),
                           **{f"ge_{t:.2f}": int((best >= t).sum()) for t in thresholds}}
    return out


def resolve_oos_classes(items: list[str], source_names: list[str]) -> set[int]:
    """Kaynak sınıf adları (ya da sayısal ID'ler) → kaynak sınıf ID kümesi."""
    by_name = {n.lower(): i for i, n in enumerate(source_names)}
    ids: set[int] = set()
    for it in items:
        if it.lstrip("-").isdigit():
            ids.add(int(it))
        elif it.lower() in by_name:
            ids.add(by_name[it.lower()])
        else:
            raise ValueError(f"--oos-classes: bilinmeyen kaynak sınıf '{it}' (kaynak: {source_names})")
    return ids


def mark_oos(records: list[ImageRecord], oos_ids: set[int], source_names: list[str]) -> None:
    """Hedef kutusu kalmayan ve OOS sınıfı içeren görüntüleri işaretler.

    Gerçek arka planlar (etiketsiz / yalnız Non Defective vb.) ve hedef kutusu
    olan karma görüntüler işaretlenmez.
    """
    for r in records:
        found = sorted({source_names[row.cls] if row.cls < len(source_names) else str(row.cls)
                        for row in r.rows if row.cls in oos_ids})
        r.oos_classes = tuple(found)
        r.is_oos = bool(found) and not r.out_rows


def place_records(records: list[ImageRecord], oos_mode: str) -> None:
    """Her kaydın yazılacağı yeri belirler (train/valid/test/oos ya da '' = yazılmaz).

    separate: OOS görüntüler (tüm atanmış bölmelerden) ``oos/`` kümesine gider.
    drop:     OOS görüntüler hiçbir yere yazılmaz.
    keep:     valid/test'teki OOS görüntüler yerinde kalır, train'dekiler çıkarılır (yazılmaz).
    """
    if oos_mode not in OOS_MODES:
        raise ValueError(f"oos_mode {oos_mode!r} geçersiz; seçenekler: {OOS_MODES}")
    for r in records:
        if not r.is_oos:
            r.placed_in = r.split
        elif oos_mode == "separate":
            r.placed_in = OOS_DIR
        elif oos_mode == "keep" and r.split != "train":
            r.placed_in = r.split
        else:
            r.placed_in = ""


def oos_report(records: list[ImageRecord], remap: dict[int, int | None],
               source_names: list[str], oos_ids: set[int], oos_mode: str) -> dict:
    """Çıkarılan / korunan arka planlar ve karma görüntüler için sayılar."""
    mods = ("gray", "rgb")
    removed = {s: dict.fromkeys(mods, 0) for s in SPLITS}
    by_class: dict = {}
    for r in records:
        if r.is_oos:
            removed[r.split][r.modality] += 1
            for c in r.oos_classes:
                by_class.setdefault(c, {s: dict.fromkeys(mods, 0) for s in SPLITS})
                by_class[c][r.split][r.modality] += 1
    # Hedef kutusu olmayan ama çıkarılmayan görüntüler (kaynak sınıf kümesine göre)
    retained: dict = {}
    # Hedef kutusu OLAN ama kapsam dışı (eşlemesi None) kutu da taşıyan karma görüntüler
    mixed = {s: {"images_with_oos_boxes": 0, "images_with_any_unmapped_boxes": 0} for s in SPLITS}
    for r in records:
        unmapped = {row.cls for row in r.rows if remap.get(row.cls) is None}
        if r.out_rows:
            if unmapped & oos_ids:
                mixed[r.split]["images_with_oos_boxes"] += 1
            if unmapped:
                mixed[r.split]["images_with_any_unmapped_boxes"] += 1
        elif not r.is_oos:
            key = "+".join(sorted(source_names[c] for c in {row.cls for row in r.rows})) or "(etiketsiz)"
            retained.setdefault(key, {s: dict.fromkeys(mods, 0) for s in SPLITS})
            retained[key][r.split][r.modality] += 1
    return {
        "mode": oos_mode,
        "classes": sorted(source_names[i] for i in oos_ids),
        "removed_images": removed,
        "removed_total": {s: sum(v.values()) for s, v in removed.items()},
        "removed_by_source_class": by_class,
        "retained_empty_background": retained,
        "mixed_images": mixed,
    }


# ── Doğrulama ────────────────────────────────────────────────────────────────


def verify_with_ultralytics(out_dir: Path, yaml_path: Path, nc: int, workers: int) -> dict:
    """Ultralytics verify_image_label + check_det_dataset ile çıktıyı doğrular."""
    try:
        import ultralytics  # pylint: disable=import-outside-toplevel
        from ultralytics.data.utils import (  # pylint: disable=import-outside-toplevel
            check_det_dataset, verify_image_label,
        )
    except ImportError:
        logger.warning("ultralytics yüklü değil; doğrulama atlandı.")
        return {"available": False}

    result: dict = {"available": True, "ultralytics_version": ultralytics.__version__, "splits": {}}
    for split in SPLITS:
        imgs = sorted((out_dir / split / "images").glob("*"))
        args = [
            (str(p), str(out_dir / split / "labels" / f"{p.stem}.txt"), "", False, nc, 0, 0, False)
            for p in imgs
        ]
        with ThreadPoolExecutor(workers) as ex:
            res = list(ex.map(verify_image_label, args))
        # Dönüş: im_file, lb, shape, segments, keypoints, nm, nf, ne, nc, msg
        result["splits"][split] = {
            "images": len(res),
            "missing": int(sum(x[5] for x in res)),
            "found": int(sum(x[6] for x in res)),
            "empty": int(sum(x[7] for x in res)),
            "corrupt": int(sum(x[8] for x in res)),
            "with_segments": int(sum(1 for x in res if x[3])),
            "instances": int(sum(len(x[1]) for x in res if x[1] is not None)),
            "messages": [x[9] for x in res if x[9]][:20],
        }
    try:
        info = check_det_dataset(str(yaml_path), autodownload=False)
        result["check_det_dataset"] = {"ok": True, "nc": info["nc"], "names": list(info["names"].values())}
    except Exception as exc:  # pylint: disable=broad-except
        result["check_det_dataset"] = {"ok": False, "error": str(exc)}
    result["total_corrupt"] = sum(s["corrupt"] for s in result["splits"].values())
    return result


# ── Ana akış ─────────────────────────────────────────────────────────────────


def parse_min_test(items: list[str]) -> dict[str, int]:
    """'hotspot=300' biçimli argümanları sözlüğe çevirir."""
    out = {}
    for it in items:
        name, _, val = it.partition("=")
        out[name] = int(val)
    return out


def _rel(path: Path) -> str:
    """Çalışma dizinine göreli yol (Ultralytics göreli yolu buna göre çözer), aksi halde mutlak."""
    p = path.resolve()
    try:
        return str(p.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(p)


def run(args: argparse.Namespace) -> dict:
    """Denetim + temizleme + yeni bölmeyi çalıştırır, rapor sözlüğünü döndürür."""
    src: Path = args.src
    out: Path = args.out
    if not src.exists():
        raise FileNotFoundError(f"Kaynak veri seti bulunamadı: {src}")
    if out.resolve() == src.resolve() or src.resolve() in out.resolve().parents:
        raise ValueError("Çıktı dizini kaynak veri setinin içinde olamaz.")
    if out.exists() and any(out.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"{out} boş değil; --overwrite ile üzerine yazın.")
        if not (out / "manifest.csv").exists():
            raise FileExistsError(f"{out} bu scriptin çıktısı gibi görünmüyor (manifest.csv yok).")
        shutil.rmtree(out)

    source_names = load_source_names(src)
    names, remap = load_remap_config(args.remap_config, args.keep_original_classes, source_names)
    min_test = parse_min_test(args.min_test)
    for unknown in sorted(set(min_test) - set(names)):
        logger.warning("--min-test: '%s' hedef taksonomide yok, atlanıyor.", unknown)
        del min_test[unknown]

    # 1) Tara + etiketleri ayrıştır
    records = scan_source(src)
    if not records:
        raise RuntimeError(f"{src} altında görüntü bulunamadı.")
    dup_names = [k for k, v in Counter(r.image.name for r in records).items() if v > 1]
    if dup_names:
        raise RuntimeError(f"Bölmeler arasında aynı dosya adı var: {dup_names[:5]}")
    logger.info("%d görüntü tarandı.", len(records))

    # 2) Görüntü özellikleri
    with ThreadPoolExecutor(args.workers) as ex:
        feats = list(ex.map(image_features, [r.image for r in records]))
    hashes = np.stack([f[1] for f in feats])
    thumbs = np.stack([f[2] for f in feats])
    eval_thumbs = np.stack([f[3] for f in feats])
    for r, (chroma, *_) in zip(records, feats):
        r.chroma = chroma
        r.modality = "gray" if chroma < args.gray_thr else "rgb"

    # 3) Gruplama
    pairs = find_near_duplicates(hashes, thumbs, args.hash_thr, args.ncc_thr,
                                 ncc_only_thr=args.ncc_only_thr if (args.ncc_only_thr or 2) <= 1 else None)
    for r, g in zip(records, build_groups([r.stem for r in records], pairs)):
        r.group = g
    n_groups = max(r.group for r in records) + 1
    logger.info("%d yakın kopya çifti, %d grup.", len(pairs), n_groups)

    # 4) Grup bazlı tabakalı bölme (orijinal sınıflar + modalite → taksonomiden bağımsız)
    n_src = max(len(source_names), 1 + max((row.cls for r in records for row in r.rows), default=0))
    gfeat = np.zeros((n_groups, 3 + n_src))
    for r in records:
        gfeat[r.group, 0] += 1
        gfeat[r.group, 1 if r.modality == "gray" else 2] += 1
        for row in r.rows:
            gfeat[r.group, 3 + row.cls] += 1
    assign = stratified_group_split(gfeat, tuple(args.ratios), args.seed)
    for r in records:
        r.split = SPLITS[assign[r.group]]
        r.out_rows = apply_remap(r.rows, remap)

    # 4b) Kapsam dışı termal anomali arka planları: bölmeden SONRA filtrele
    oos_ids = resolve_oos_classes(list(args.oos_classes), source_names)
    mark_oos(records, oos_ids, source_names)
    place_records(records, args.oos_mode)
    placed = [r for r in records if r.placed_in in SPLITS]

    test_counts = Counter(names[row.cls] for r in records if r.split == "test" for row in r.out_rows)
    min_test_check = {
        n: {"required": k, "actual": test_counts.get(n, 0), "ok": test_counts.get(n, 0) >= k}
        for n, k in min_test.items()
    }
    failed = [n for n, v in min_test_check.items() if not v["ok"]]
    if failed:
        raise RuntimeError(
            f"Test bölmesinde yetersiz instance: {[(n, min_test_check[n]) for n in failed]}. "
            "--ratios ile test oranını artırın."
        )

    # 5) Yaz
    dests = list(SPLITS) + ([OOS_DIR] if any(r.placed_in == OOS_DIR for r in records) else [])
    for dest in dests:
        (out / dest / "images").mkdir(parents=True, exist_ok=True)
        (out / dest / "labels").mkdir(parents=True, exist_ok=True)

    def _write(r: ImageRecord) -> None:
        if not r.placed_in:
            return
        # Kopya (bağlantı değil): Ultralytics bozuk JPEG'i yerinde onarabilir, kaynak korunmalı
        shutil.copy2(r.image, out / r.placed_in / "images" / r.image.name)
        (out / r.placed_in / "labels" / f"{r.image.stem}.txt").write_text(
            format_label_rows(r.out_rows), encoding="utf-8"
        )

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(_write, records))

    with open(out / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "file", "source_split", "stem", "group", "modality", "chroma",
                    "n_rows_source", "n_rows_from_polygon", "n_rows_out",
                    "placed_in", "oos", "oos_source_classes"])
        for r in sorted(records, key=lambda x: (x.split, x.image.name)):
            w.writerow([r.split, r.image.name, r.source_split, r.stem, r.group, r.modality,
                        f"{r.chroma:.3f}", len(r.rows), sum(x.from_polygon for x in r.rows),
                        len(r.out_rows), r.placed_in or "dropped", int(r.is_oos),
                        "|".join(r.oos_classes)])

    yaml_path = out.parent / f"{out.name}.yaml"
    remap_lines = "\n".join(
        f"#   {i:>2} {source_names[i] if i < len(source_names) else '?':<24} → "
        f"{names[v] if v is not None else '(kaldırıldı)'}"
        for i, v in sorted(remap.items())
    )
    yaml_path.write_text(
        "# Otomatik üretildi: scripts/audit_and_fix_dataset.py\n"
        f"# Kaynak: {_rel(src)}\n"
        "# Poligonlar bbox'a çevrildi; bölme kaynak gövdesi + dHash grubu bazlı.\n"
        f"# Kapsam dışı termal anomali arka planları train/valid/test dışında: oos/ (mod: {args.oos_mode}).\n"
        "# Sınıf eşleştirmesi:\n"
        f"{remap_lines}\n\n"
        + yaml.safe_dump(
            {"path": _rel(out), "train": "train/images", "val": "valid/images",
             "test": "test/images", "nc": len(names), "names": names},
            allow_unicode=True, sort_keys=False,
        ),
        encoding="utf-8",
    )

    # 6) Rapor
    label_totals: dict = {}
    for split in SPLITS:
        c: Counter = Counter()
        for r in records:
            if r.source_split == split:
                c.update(r.label_stats)
                kept = sum(1 for row in r.rows if remap.get(row.cls) is not None)
                c["duplicate_after_remap"] += kept - len(r.out_rows)
        label_totals[split] = dict(c)

    sizes = Counter(Counter(r.group for r in records).values())
    biggest = Counter(r.group for r in records).most_common(5)
    split_sizes = Counter(r.placed_in for r in records)
    report = {
        "source": _rel(src),
        "output": _rel(out),
        "data_yaml": _rel(yaml_path),
        "params": {
            "ratios": list(args.ratios), "seed": args.seed, "hash_thr": args.hash_thr,
            "ncc_thr": args.ncc_thr, "ncc_only_thr": args.ncc_only_thr,
            "gray_thr": args.gray_thr, "oos_mode": args.oos_mode,
            "oos_classes": list(args.oos_classes), "keep_original_classes": args.keep_original_classes,
        },
        "taxonomy": {
            "names": names,
            "remap": {source_names[k] if k < len(source_names) else str(k):
                      (names[v] if v is not None else None) for k, v in sorted(remap.items())},
        },
        "label_conversion": label_totals,
        "label_sources": dict(Counter(r.label_source for r in records)),
        "mixed_files_before": mixed_file_stats(records, remap, names),
        "grouping": {
            "images": len(records),
            "source_stems": len({r.stem for r in records}),
            "near_duplicate_pairs": len(pairs),
            "near_duplicate_pairs_cross_stem": sum(
                1 for i, j, *_ in pairs if records[i].stem != records[j].stem),
            "groups": n_groups,
            "group_size_hist": {str(k): v for k, v in sorted(sizes.items())},
            "largest_groups": [
                {"size": k, "stems": sorted({r.stem for r in records if r.group == g})[:10]}
                for g, k in biggest
            ],
        },
        "leakage_before": leakage_stats(records, "source_split", pairs),
        "leakage_after": leakage_stats(records, "split", pairs),
        "ncc_leakage_before": ncc_leakage(eval_thumbs, [r.source_split for r in records]),
        "ncc_leakage_after": ncc_leakage(eval_thumbs, [r.placed_in for r in records]),
        # OOS filtresinden bağımsız: tüm görüntüler atanmış bölmeleriyle (eşik karşılaştırması için)
        "ncc_leakage_assigned": ncc_leakage(eval_thumbs, [r.split for r in records]),
        "split_sizes": {**{s: split_sizes.get(s, 0) for s in (*SPLITS, OOS_DIR)},
                       "dropped": split_sizes.get("", 0)},
        "oos": oos_report(records, remap, source_names, oos_ids, args.oos_mode),
        "images_before": image_tables(records, "source_split", "rows"),
        "images_after": image_tables(placed, "split", "out_rows"),
        "classes_before_target": class_tables(
            [_with_rows(r, apply_remap(r.rows, remap)) for r in records],
            names, "out_rows", "source_split"),
        "classes_after_target": class_tables(placed, names, "out_rows", "split"),
        "classes_after_source": class_tables(placed, source_names, "rows", "split"),
        "min_test_check": min_test_check,
    }
    if not args.skip_verify:
        logger.info("Ultralytics doğrulaması çalışıyor…")
        report["ultralytics_verify"] = verify_with_ultralytics(out, yaml_path, len(names), args.workers)
    return report


def _with_rows(r: ImageRecord, rows: list[LabelRow]) -> ImageRecord:
    """Kaydın out_rows'u değiştirilmiş sığ kopyası (rapor için)."""
    c = ImageRecord(**{**r.__dict__})
    c.out_rows = rows
    return c


def _table_md(tbl: dict, title: str) -> list[str]:
    """{sınıf: {modalite: {bölme: n}}} → Markdown tablo."""
    hdr = [f"**{title}**", "",
           "| Sınıf | " + " | ".join(f"{s} gri" for s in SPLITS) + " | "
           + " | ".join(f"{s} RGB" for s in SPLITS) + " | Toplam |",
           "|---|" + "---:|" * (2 * len(SPLITS) + 1)]
    lines = []
    for name, mods in tbl.items():
        vals = [mods["gray"][s] for s in SPLITS] + [mods["rgb"][s] for s in SPLITS]
        lines.append(f"| {name} | " + " | ".join(str(v) for v in vals) + f" | {sum(vals)} |")
    return hdr + lines + [""]


def write_oos_md(oos: dict, sizes: dict) -> list[str]:
    """Kapsam dışı (OOS) bölümü Markdown satırları."""
    md = [
        "## 4b. Kapsam dışı termal anomali arka planları (OOS)", "",
        f"- Mod: `{oos['mode']}` — bölme tüm görüntülerle yapıldı, filtre bölmeden SONRA uygulandı",
        f"- Çıkarma kümesi (kaynak sınıflar): {', '.join(oos['classes']) or '(boş)'}",
        "- Kural: remap sonrası hedef kutusu kalmayan ve bu sınıflardan birini içeren görüntü. "
        "Etiketsiz / yalnız Non Defective arka planları ve hedef kutusu olan karma görüntüler korunur; "
        "Electrical Damage (+ Non Defective) görüntüleri OOS'a gider.",
        f"- Yazılan: oos={sizes.get('oos', 0)}, atılan (yazılmayan)={sizes.get('dropped', 0)}", "",
        "| Atanmış bölme | gri | RGB | Toplam |", "|---|---:|---:|---:|",
    ]
    for s in SPLITS:
        r = oos["removed_images"][s]
        md.append(f"| {s} | {r['gray']} | {r['rgb']} | {oos['removed_total'][s]} |")
    md += ["", "Kaynak sınıfa göre (bir görüntü içerdiği her sınıfta sayılır):", "",
           "| Kaynak sınıf | " + " | ".join(f"{s} gri | {s} RGB" for s in SPLITS) + " |",
           "|---|" + "---:|" * (2 * len(SPLITS))]
    for c, v in oos["removed_by_source_class"].items():
        md.append(f"| {c} | " + " | ".join(f"{v[s]['gray']} | {v[s]['rgb']}" for s in SPLITS) + " |")
    md += ["", "Çıkarılmayan, hedef kutusu olmayan arka planlar (kaynak sınıf kümesine göre; "
           "gri+RGB toplamı):", "", "| Kaynak sınıf kümesi | " + " | ".join(SPLITS) + " |",
           "|---|" + "---:|" * len(SPLITS)]
    for c, v in sorted(oos["retained_empty_background"].items()):
        md.append(f"| {c} | " + " | ".join(str(v[s]["gray"] + v[s]["rgb"]) for s in SPLITS) + " |")
    md += ["", "Karma görüntüler (hedef kutusu + kapsam dışı kutu; remap sonrası anomali bölgesi "
           "etiketsiz kalır, bu işte DEĞİŞTİRİLMEDİ):", "",
           "| Bölme | OOS-sınıf kutusu içeren | Herhangi eşlenmemiş kutu içeren |", "|---|---:|---:|"]
    for s in SPLITS:
        m = oos["mixed_images"][s]
        md.append(f"| {s} | {m['images_with_oos_boxes']} | {m['images_with_any_unmapped_boxes']} |")
    return md + [""]


def write_markdown(report: dict, path: Path) -> None:
    """Rapor özetini Markdown olarak yazar."""
    lb, la = report["leakage_before"], report["leakage_after"]
    g = report["grouping"]
    md = [
        "# Veri Seti Denetim Raporu",
        "",
        f"Kaynak: `{report['source']}` → Çıktı: `{report['output']}` (YAML: `{report['data_yaml']}`)",
        "",
        "Otomatik üretildi: `scripts/audit_and_fix_dataset.py`. "
        f"Parametreler: `{json.dumps(report['params'])}`",
        "",
        "## 1. Etiket dönüşümü (poligon → bbox)",
        "",
        "| Kaynak bölme | bbox satırı | poligon satırı (çevrildi) | dejenere | yinelenen | "
        "yinelenen (remap sonrası) | hatalı | karışık dosya (15 sınıf) | karışık dosya (remap sonrası) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in SPLITS:
        c, m = report["label_conversion"].get(s, {}), report["mixed_files_before"][s]
        md.append(
            f"| {s} | {c.get('bbox', 0)} | {c.get('polygon', 0)} | {c.get('degenerate', 0)} | "
            f"{c.get('duplicate', 0)} | {c.get('duplicate_after_remap', 0)} | {c.get('malformed', 0)} | "
            f"{m['mixed_files_original_classes']} | {m['mixed_files_after_remap']} |"
        )
    md += [
        "",
        "Karışık dosyalarda Ultralytics tüm satırları poligon sayar: 8.4.x'te 5 sütunlu bbox "
        "satırları iki nokta olarak okunup bozuk kutuya dönüşür, eski sürümlerde dosya düşürülür. "
        "Temiz veri setinde tüm satırlar 5 sütunludur.",
        "",
        "## 2. Gruplama ve sızıntı",
        "",
        f"- {g['images']} görüntü, {g['source_stems']} kaynak gövdesi, {g['groups']} grup",
        f"- {g['near_duplicate_pairs']} yakın kopya çifti (dHash ≤ {report['params']['hash_thr']}, "
        f"çevirme duyarsız, NCC ≥ {report['params']['ncc_thr']}"
        + (f"; ek NCC-tabanlı aday ≥ {report['params']['ncc_only_thr']}"
           if (report["params"].get("ncc_only_thr") or 2) <= 1 else "")
        + f"); {g['near_duplicate_pairs_cross_stem']} tanesi farklı gövdeler arasında",
        f"- En büyük grup: {g['largest_groups'][0]['size']} görüntü" if g["largest_groups"] else "",
        "",
        "| Ölçüt | Önce (Roboflow bölmesi) | Sonra (yeni bölme) |",
        "|---|---:|---:|",
    ]
    for k in lb["stems_shared"]:
        md.append(f"| Ortak gövde {k} | {lb['stems_shared'][k]} | {la['stems_shared'][k]} |")
    for k in lb["groups_shared"]:
        md.append(f"| Ortak grup {k} | {lb['groups_shared'][k]} | {la['groups_shared'][k]} |")
    md += [
        f"| Bölmeler arası yakın kopya çifti | {sum(lb['near_duplicate_pairs_across_splits'].values())} "
        f"| {sum(la['near_duplicate_pairs_across_splits'].values())} |",
        f"| Train'de eşi olan test görüntüsü | {lb['test_images_with_train_twin']} / {lb['test_images']} "
        f"| {la['test_images_with_train_twin']} / {la['test_images']} |",
        "",
        f"Bağımsız ölçüt: {EVAL_THUMB_SIZE}x{EVAL_THUMB_SIZE} küçük resim max-NCC (4 çevirme); "
        "ilk bölmedeki görüntülerden, ikincideki en benzeriyle NCC eşiğini aşanların sayısı "
        "(gruplama 32x32 kullandığı için bağımsızdır; yazılan görüntüler üzerinden).",
        "",
        "| Bölme çifti | " + " | ".join(f"≥{t:.2f} önce | ≥{t:.2f} sonra" for t in NCC_LEAK_THRESHOLDS) + " |",
        "|---|" + "---:|" * (2 * len(NCC_LEAK_THRESHOLDS)),
    ]
    nb, na = report["ncc_leakage_before"], report["ncc_leakage_after"]
    for k in na:
        cells = " | ".join(
            f"{nb[k][f'ge_{t:.2f}']}/{nb[k]['images']} | {na[k][f'ge_{t:.2f}']}/{na[k]['images']}"
            for t in NCC_LEAK_THRESHOLDS)
        md.append(f"| {k} | {cells} |")
    md += [
        "",
        "## 3. Bölme boyutları ve modalite",
        "",
        "| Bölme | Önce gri | Önce RGB | Sonra gri | Sonra RGB | Sonra arka plan |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    ib, ia = report["images_before"], report["images_after"]
    for s in SPLITS:
        bg = ia["background_images"]["gray"][s] + ia["background_images"]["rgb"][s]
        md.append(f"| {s} | {ib['images']['gray'][s]} | {ib['images']['rgb'][s]} | "
                  f"{ia['images']['gray'][s]} | {ia['images']['rgb'][s]} | {bg} |")
    md += ["", "## 4. Sınıf × modalite × bölme (instance)", ""]
    md += _table_md(report["classes_before_target"]["instances"], "Hedef sınıflar — önce (Roboflow bölmesi)")
    md += _table_md(report["classes_after_target"]["instances"], "Hedef sınıflar — sonra (yeni bölme)")
    md += _table_md(report["classes_after_source"]["instances"], "Orijinal 15 sınıf — yeni bölme")
    md += write_oos_md(report["oos"], report["split_sizes"])
    md += ["## 5. Kontroller", ""]
    for n, v in report["min_test_check"].items():
        md.append(f"- Test `{n}` ≥ {v['required']}: {v['actual']} {'✓' if v['ok'] else '✗'}")
    uv = report.get("ultralytics_verify")
    if uv and uv.get("available"):
        md.append(f"- Ultralytics {uv['ultralytics_version']} `verify_image_label`: "
                  f"toplam bozuk = **{uv['total_corrupt']}**")
        for s, v in uv["splits"].items():
            md.append(f"  - {s}: {v['images']} görüntü, {v['corrupt']} bozuk, {v['empty']} boş, "
                      f"{v['with_segments']} segment içeren, {v['instances']} instance")
        cd = uv.get("check_det_dataset", {})
        md.append(f"- `check_det_dataset`: {'✓' if cd.get('ok') else '✗ ' + cd.get('error', '')}")
    elif uv is not None:
        md.append("- Ultralytics yüklü değil; doğrulama atlandı.")
    path.write_text("\n".join(md) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Komut satırı argümanlarını ayrıştırır."""
    p = argparse.ArgumentParser(description="GES veri seti denetimi ve temizliği")
    p.add_argument("--src", type=Path, default=SRC_DIR, help="Kaynak veri seti kökü")
    p.add_argument("--out", type=Path, default=OUT_DIR, help="Temiz veri seti çıktı dizini")
    p.add_argument("--report-dir", type=Path, default=REPORTS_DIR, help="Rapor dizini")
    p.add_argument("--remap-config", type=Path, default=None,
                   help="names + remap içeren YAML (varsayılan: train_yolo26.CLASS_REMAP)")
    p.add_argument("--keep-original-classes", action="store_true",
                   help="Eşleştirme yapma, orijinal sınıfları koru")
    p.add_argument("--ratios", type=float, nargs=3, default=(0.8, 0.1, 0.1),
                   metavar=("TRAIN", "VALID", "TEST"), help="Bölme oranları")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--hash-thr", type=int, default=8, help="dHash Hamming eşiği (aday)")
    p.add_argument("--ncc-thr", type=float, default=0.90,
                   help="Aday çifti kabul için min. küçük resim korelasyonu (-1 = kapalı)")
    p.add_argument("--ncc-only-thr", type=float, default=0.93,
                   help="dHash'ten bağımsız ek aday: 32x32 NCC bu değeri aşan çiftler de birleşir "
                        "(varsayılan: 0.93; kapatmak için 1'den büyük bir değer, ör. 2, verin)")
    p.add_argument("--oos-classes", nargs="*", default=list(OOS_DEFAULT_CLASSES),
                   help="Kapsam dışı termal anomali kaynak sınıfları (ad ya da ID); hedef kutusu "
                        "kalmayan ve bunları içeren görüntüler çıkarılır. Boş liste = kapalı")
    p.add_argument("--oos-mode", choices=OOS_MODES, default="separate",
                   help="separate: çıkarılanları oos/ kümesine yaz (varsayılan); drop: hiç yazma; "
                        "keep: valid/test'te yerinde bırak (train'dekiler yine çıkarılır)")
    p.add_argument("--gray-thr", type=float, default=1.0,
                   help="Bu değerin altındaki kanal farkı → gri/termal")
    p.add_argument("--min-test", nargs="*", default=["hotspot=300"],
                   help="Test bölmesi için min. instance (ör. hotspot=300)")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--overwrite", action="store_true", help="Var olan çıktıyı sil ve yeniden yaz")
    p.add_argument("--skip-verify", action="store_true", help="Ultralytics doğrulamasını atla")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Giriş noktası; Ultralytics bozuk görüntü bulursa 1 döndürür."""
    args = parse_args(argv)
    report = run(args)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / "dataset_audit.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, args.report_dir / "dataset_audit.md")
    logger.info("Rapor yazıldı: %s", json_path)

    la = report["leakage_after"]
    logger.info("Yeni bölme: %s | bölmeler arası ortak grup: %d",
                report["split_sizes"], la["groups_spanning_multiple_splits"])
    uv = report.get("ultralytics_verify", {})
    if uv.get("available"):
        logger.info("Ultralytics doğrulaması: %d bozuk görüntü/etiket.", uv["total_corrupt"])
        if uv["total_corrupt"] or not uv.get("check_det_dataset", {}).get("ok"):
            return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    sys.exit(main())
