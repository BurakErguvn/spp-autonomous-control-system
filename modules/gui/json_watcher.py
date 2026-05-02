"""outputs/ klasörünü izleyen arka plan thread'i.

JsonWatcher; ariza_verileri.json veya gorev_cizelgesi.json
güncellendiğinde ilgili PyQt6 sinyalini tetikler. GUI bileşenleri
bu sinyallere bağlanarak bağımsız şekilde güncellenir.

YZ ve Optimizasyon modüllerinin çıktıları birbirini beklemez.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs")
FAULT_FILE = OUTPUTS_DIR / "ariza_verileri.json"
SCHEDULE_FILE = OUTPUTS_DIR / "gorev_cizelgesi.json"
POLL_INTERVAL_S = 1.0  # saniye cinsinden dosya kontrol aralığı


class JsonWatcher(QThread):
    """outputs/ klasörünü periyodik olarak izler ve değişiklikleri sinyal ile bildirir.

    Signals:
        fault_detected (list): ariza_verileri.json güncellendiğinde,
            yeni tespit listesi iletilir.
        schedule_updated (dict): gorev_cizelgesi.json güncellendiğinde,
            görev çizelgesi dict'i iletilir.
        watch_error (str): Dosya okuma hatası oluştuğunda hata mesajı iletilir.

    Example:
        >>> watcher = JsonWatcher()
        >>> watcher.fault_detected.connect(map_widget.on_fault)
        >>> watcher.schedule_updated.connect(maintenance_panel.on_schedule)
        >>> watcher.start()
    """

    fault_detected: pyqtSignal = pyqtSignal(list)
    schedule_updated: pyqtSignal = pyqtSignal(dict)
    watch_error: pyqtSignal = pyqtSignal(str)

    def __init__(
        self,
        poll_interval: float = POLL_INTERVAL_S,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._poll_interval = poll_interval
        self._running = False

        # Son bilinen mtime değerleri (değişiklik tespiti için)
        self._last_fault_mtime: float = 0.0
        self._last_schedule_mtime: float = 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # QThread override
    # ──────────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Thread gövdesi: dosyaları periyodik olarak kontrol eder."""
        self._running = True
        logger.info("JsonWatcher başlatıldı. İzlenen dizin: %s", OUTPUTS_DIR)

        while self._running:
            try:
                self._check_fault_file()
                self._check_schedule_file()
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("JsonWatcher hata: %s", exc)
                self.watch_error.emit(str(exc))

            time.sleep(self._poll_interval)

    def stop(self) -> None:
        """İzlemeyi durdurur ve thread'in bitmesini bekler."""
        self._running = False
        self.wait()
        logger.info("JsonWatcher durduruldu.")

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _check_fault_file(self) -> None:
        """ariza_verileri.json değişmişse fault_detected sinyali yayar."""
        if not FAULT_FILE.exists():
            return

        mtime = FAULT_FILE.stat().st_mtime
        if mtime <= self._last_fault_mtime:
            return

        self._last_fault_mtime = mtime
        data = self._safe_load_json(FAULT_FILE)
        if data is not None:
            detections = data if isinstance(data, list) else []
            self.fault_detected.emit(detections)
            logger.debug("fault_detected sinyali yayıldı: %d tespit", len(detections))

    def _check_schedule_file(self) -> None:
        """gorev_cizelgesi.json değişmişse schedule_updated sinyali yayar."""
        if not SCHEDULE_FILE.exists():
            return

        mtime = SCHEDULE_FILE.stat().st_mtime
        if mtime <= self._last_schedule_mtime:
            return

        self._last_schedule_mtime = mtime
        data = self._safe_load_json(SCHEDULE_FILE)
        if data is not None and isinstance(data, dict):
            self.schedule_updated.emit(data)
            logger.debug("schedule_updated sinyali yayıldı.")

    @staticmethod
    def _safe_load_json(path: Path) -> object | None:
        """JSON dosyasını güvenli şekilde okur.

        Args:
            path: Okunacak dosya yolu.

        Returns:
            Ayrıştırılmış Python nesnesi; hata durumunda None.
        """
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("JSON okunamadı (%s): %s", path.name, exc)
            return None
