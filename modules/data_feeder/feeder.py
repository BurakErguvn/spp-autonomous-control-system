"""EE Simülasyonu — Veri Akış Modülü.

Gerçek bir İHA uçuşu yapılmadığı için bu modül; önceden toplanmış termal/RGB
veri setini sanki anlık otopilot beslemesi gibi sıralı şekilde sisteme verir.
Her kareyi `panel_id`, `gps`, `timestamp`, `flight_altitude` meta verileriyle
birlikte yayınlar (kural §2.1: katman, ham görüntü + meta veriden öteye karar
vermez).

Senaryo modunda; `data/SOLAR PANEL DET.v1i.yolo26/test/labels/` içindeki
3-sınıfa remap edilmiş etiketler taranır ve hedef sınıfı içeren görüntüler
ilgili panel ID'lerine eşlenir. Tam koşum modunda 30 panelin tamamı sırayla
beslenir ve her birine veri setinden rastgele bir görüntü atanır.
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .scenarios import Scenario, get as get_scenario

logger = logging.getLogger(__name__)

DEFAULT_DATASET_DIR = Path("data") / "SOLAR PANEL DET.v1i.yolo26" / "test"
DEFAULT_LAYOUT_PATH = Path("modules") / "gui" / "assets" / "panel_layout.json"
DEFAULT_FLIGHT_ALTITUDE_M = 30.0


class DataFeeder:
    """Veri seti üzerinden senaryo bazlı görüntü besleyicisi.

    Args:
        dataset_dir: 'images/' ve 'labels/' alt dizinlerini içeren kök
            (örn. ``data/SOLAR PANEL DET.v1i.yolo26/test``).
        layout_path: 30 panelin GPS ve ızgara konumunu içeren JSON.
        seed: Tekrarlanabilirlik için RNG tohumu. Tam koşumda görüntü
            seçimini ve senaryo modunda hedef sınıf görüntüleri sıralamasını
            etkiler.
    """

    def __init__(
        self,
        dataset_dir: Path | None = None,
        layout_path: Path | None = None,
        seed: int = 42,
    ) -> None:
        self.dataset_dir = Path(dataset_dir or DEFAULT_DATASET_DIR)
        self.layout_path = Path(layout_path or DEFAULT_LAYOUT_PATH)
        self._rng = random.Random(seed)
        self._panels: list[dict] = self._load_panels()
        self._class_to_images: dict[int, list[Path]] = self._index_images_by_class()

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def iter_frames(
        self, scenario: str | Scenario | None = None
    ) -> Iterator[tuple[np.ndarray, dict[str, Any]]]:
        """Senaryoya göre (frame, meta) çiftlerini sırayla yield eder.

        Args:
            scenario: "A" / "B" / "C" (string), :class:`Scenario` nesnesi
                veya None (tam koşum).

        Yields:
            (frame, meta) — frame BGR ndarray, meta `panel_id`, `gps`,
            `timestamp` (boş string, çağıran tarafından doldurulmalı),
            `flight_altitude` ve `scenario` anahtarlarını içerir.
        """
        scen: Scenario | None = (
            scenario if isinstance(scenario, Scenario) else get_scenario(scenario)
        )

        if scen is None:
            yield from self._iter_full_run()
        else:
            yield from self._iter_scenario(scen)

    def panel_count(self) -> int:
        """Toplam panel sayısı (tam koşum kare sayısı)."""
        return len(self._panels)

    def available_classes(self) -> dict[int, int]:
        """{class_id: image_count} — veri setinde her sınıf için kaç görüntü var."""
        return {c: len(v) for c, v in self._class_to_images.items()}

    # ──────────────────────────────────────────────────────────────────────────
    # Private — senaryo iterasyonu
    # ──────────────────────────────────────────────────────────────────────────

    def _iter_scenario(
        self, scen: Scenario
    ) -> Iterator[tuple[np.ndarray, dict[str, Any]]]:
        candidates = self._class_to_images.get(scen.target_class, [])
        if not candidates:
            logger.warning(
                "Senaryo %s: hedef sınıf %d için veri setinde görüntü bulunamadı.",
                scen.name,
                scen.target_class,
            )
            return

        # Tekrarlanabilirlik için kopyala-karıştır
        pool = candidates.copy()
        self._rng.shuffle(pool)

        for idx, panel_id in enumerate(scen.panel_ids):
            img_path = pool[idx % len(pool)]
            frame = self._read_image(img_path)
            if frame is None:
                continue
            meta = self._build_meta(panel_id, scenario_name=scen.name)
            meta["image_path"] = str(img_path)
            meta["gercek_durum"] = {0: "hotspot", 1: "mikro_catlak", 2: "tozlanma"}.get(scen.target_class, "sağlam")
            yield frame, meta

    def _iter_full_run(self) -> Iterator[tuple[np.ndarray, dict[str, Any]]]:
        all_images = self._all_images()
        if not all_images:
            logger.error("Veri setinde görüntü bulunamadı: %s", self.dataset_dir)
            return

        for panel in self._panels:
            img_path = self._rng.choice(all_images)
            frame = self._read_image(img_path)
            if frame is None:
                continue
            meta = self._build_meta(int(panel["panel_id"]), scenario_name=None)
            meta["image_path"] = str(img_path)
            
            # Label dosyasını okuyarak gerçek durumunu belirle
            label_file = self.dataset_dir / "labels" / (img_path.stem + ".txt")
            classes = self._classes_in_label(label_file)
            if classes:
                sorted_classes = sorted(list(classes))
                meta["gercek_durum"] = {0: "hotspot", 1: "mikro_catlak", 2: "tozlanma"}.get(sorted_classes[0], "sağlam")
            else:
                meta["gercek_durum"] = "sağlam"
            
            yield frame, meta

    # ──────────────────────────────────────────────────────────────────────────
    # Private — yardımcılar
    # ──────────────────────────────────────────────────────────────────────────

    def _build_meta(
        self, panel_id: int, scenario_name: str | None
    ) -> dict[str, Any]:
        gps = self._panel_gps(panel_id)
        return {
            "panel_id": panel_id,
            "gps": list(gps),
            "timestamp": "",  # ana pipeline tarafından doldurulur
            "flight_altitude": DEFAULT_FLIGHT_ALTITUDE_M,
            "scenario": scenario_name,
        }

    def _panel_gps(self, panel_id: int) -> tuple[float, float]:
        for p in self._panels:
            if int(p["panel_id"]) == int(panel_id):
                return (float(p["gps"][0]), float(p["gps"][1]))
        # Bulunamazsa origin
        return (38.4200, 27.1400)

    def _load_panels(self) -> list[dict]:
        if not self.layout_path.exists():
            logger.error("panel_layout.json bulunamadı: %s", self.layout_path)
            return []
        with open(self.layout_path, encoding="utf-8") as f:
            layout = json.load(f)
        return list(layout.get("panels", []))

    def _index_images_by_class(self) -> dict[int, list[Path]]:
        """test/labels/*.txt dosyalarını tarayarak her görüntünün hangi sınıfı
        içerdiğini indeksler. Bir görüntü birden fazla sınıf içerebilir."""
        labels_dir = self.dataset_dir / "labels"
        images_dir = self.dataset_dir / "images"
        index: dict[int, list[Path]] = {0: [], 1: [], 2: []}

        if not labels_dir.exists() or not images_dir.exists():
            logger.warning(
                "Veri seti dizinleri eksik (labels=%s, images=%s)",
                labels_dir,
                images_dir,
            )
            return index

        for label_file in labels_dir.glob("*.txt"):
            if label_file.suffix == ".orig" or label_file.name.endswith(".txt.orig"):
                continue
            classes = self._classes_in_label(label_file)
            if not classes:
                continue
            img_path = self._image_for_label(label_file, images_dir)
            if img_path is None:
                continue
            for c in classes:
                if c in index:
                    index[c].append(img_path)

        # Tekrarlananları kaldır
        for c in index:
            index[c] = sorted(set(index[c]))

        logger.info(
            "Veri seti indekslendi: hotspot=%d, mikro_catlak=%d, tozlanma=%d",
            len(index.get(0, [])),
            len(index.get(1, [])),
            len(index.get(2, [])),
        )
        return index

    @staticmethod
    def _classes_in_label(label_file: Path) -> set[int]:
        try:
            text = label_file.read_text(encoding="utf-8")
        except OSError:
            return set()
        classes: set[int] = set()
        for line in text.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            try:
                classes.add(int(parts[0]))
            except ValueError:
                continue
        return classes

    @staticmethod
    def _image_for_label(label_file: Path, images_dir: Path) -> Path | None:
        for ext in (".jpg", ".jpeg", ".png"):
            candidate = images_dir / (label_file.stem + ext)
            if candidate.exists():
                return candidate
        return None

    def _all_images(self) -> list[Path]:
        images_dir = self.dataset_dir / "images"
        if not images_dir.exists():
            return []
        return sorted(
            list(images_dir.glob("*.jpg"))
            + list(images_dir.glob("*.jpeg"))
            + list(images_dir.glob("*.png"))
        )

    @staticmethod
    def _read_image(path: Path) -> np.ndarray | None:
        frame = cv2.imread(str(path))
        if frame is None:
            logger.warning("Görüntü okunamadı: %s", path)
        return frame
