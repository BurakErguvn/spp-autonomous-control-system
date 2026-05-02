"""GUI modülü birim testleri.

PyQt6 bileşenlerini pytest-qt ile test eder.

Çalıştırma:
    pytest tests/test_gui.py -v
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

# PyQt6 yoksa testleri atla
pytest.importorskip("PyQt6", reason="PyQt6 yüklü değil — GUI testleri atlandı.")

from PyQt6.QtWidgets import QApplication
from modules.gui.json_watcher import JsonWatcher
from modules.gui.map_widget import MapWidget
from modules.gui.maintenance_panel import MaintenancePanel

# ── Sabit test verisi ─────────────────────────────────────────────────────────

SAMPLE_DETECTIONS = [
    {
        "timestamp": "2026-03-27T10:15:00+00:00",
        "panel_id": 5,
        "gps": [38.4197, 27.1412],
        "hasar": "hotspot",
        "koordinat": [100, 150, 80, 60],
        "guven_skoru": 0.91,
    },
    {
        "timestamp": "2026-03-27T10:15:01+00:00",
        "panel_id": 12,
        "gps": [38.4194, 27.1406],
        "hasar": "tozlanma",
        "koordinat": [200, 100, 70, 50],
        "guven_skoru": 0.73,
    },
]

SAMPLE_SCHEDULE = {
    "generated_at": "2026-03-27T10:16:00+00:00",
    "total_cost": 3200.0,
    "tasks": [
        {
            "panel_id": 5,
            "hasar": "hotspot",
            "priority": "kritik",
            "estimated_cost": 1500.0,
            "scheduled_date": "2026-03-28",
        },
        {
            "panel_id": 12,
            "hasar": "tozlanma",
            "priority": "düşük",
            "estimated_cost": 300.0,
            "scheduled_date": "2026-04-05",
        },
    ],
    "route": [0, 5, 12, 29],
}


# ─────────────────────────────────────────────────────────────────────────────
# MapWidget Testleri
# ─────────────────────────────────────────────────────────────────────────────


class TestMapWidget:
    """MapWidget bileşen testleri."""

    def test_map_loads_without_detections(self, qtbot):
        """MapWidget, tespit olmadan hatasız açılmalı."""
        widget = MapWidget()
        qtbot.addWidget(widget)
        assert widget is not None

    def test_on_fault_detected_updates_panels(self, qtbot):
        """Tespit listesi geldiğinde panel renkleri güncellenebilmeli."""
        widget = MapWidget()
        qtbot.addWidget(widget)
        # Hata fırlatmamalı
        widget.on_fault_detected(SAMPLE_DETECTIONS)

    def test_on_fault_detected_empty_list(self, qtbot):
        """Boş tespit listesi panelleri sıfırlamalı — hata fırlatmamalı."""
        widget = MapWidget()
        qtbot.addWidget(widget)
        widget.on_fault_detected(SAMPLE_DETECTIONS)  # önce arıza işaretle
        widget.on_fault_detected([])                  # sonra temizle

    def test_unknown_panel_id_does_not_crash(self, qtbot):
        """Haritada olmayan panel_id gelirse hata fırlatmamalı."""
        widget = MapWidget()
        qtbot.addWidget(widget)
        widget.on_fault_detected(
            [{**SAMPLE_DETECTIONS[0], "panel_id": 9999}]
        )  # geçersiz ID


# ─────────────────────────────────────────────────────────────────────────────
# MaintenancePanel Testleri
# ─────────────────────────────────────────────────────────────────────────────


class TestMaintenancePanel:
    """MaintenancePanel bileşen testleri."""

    def test_panel_loads_in_empty_state(self, qtbot):
        """MaintenancePanel, çizelge olmadan hatasız açılmalı."""
        panel = MaintenancePanel()
        qtbot.addWidget(panel)
        assert panel is not None

    def test_on_schedule_updated_populates_table(self, qtbot):
        """Çizelge geldiğinde tablo satırları doldurulmalı."""
        panel = MaintenancePanel()
        qtbot.addWidget(panel)
        panel.on_schedule_updated(SAMPLE_SCHEDULE)
        assert panel._table.rowCount() == len(SAMPLE_SCHEDULE["tasks"])

    def test_on_schedule_updated_populates_route(self, qtbot):
        """Çizelge geldiğinde rota listesi doldurulmalı."""
        panel = MaintenancePanel()
        qtbot.addWidget(panel)
        panel.on_schedule_updated(SAMPLE_SCHEDULE)
        assert panel._route_list.count() == len(SAMPLE_SCHEDULE["route"])

    def test_empty_schedule_does_not_crash(self, qtbot):
        """Boş çizelge hata fırlatmamalı."""
        panel = MaintenancePanel()
        qtbot.addWidget(panel)
        panel.on_schedule_updated({"tasks": [], "route": [], "total_cost": 0})


# ─────────────────────────────────────────────────────────────────────────────
# JsonWatcher Testleri
# ─────────────────────────────────────────────────────────────────────────────


class TestJsonWatcher:
    """JsonWatcher sinyal testleri."""

    def test_fault_signal_emitted_on_file_change(self, qtbot):
        """ariza_verileri.json değişince fault_detected sinyali yayılmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fault_path = Path(tmpdir) / "ariza_verileri.json"

            # Patch: watcher'ın izlediği dosya yolunu geçici dizine yönlendir
            import modules.gui.json_watcher as watcher_mod  # noqa
            original_fault = watcher_mod.FAULT_FILE
            original_schedule = watcher_mod.SCHEDULE_FILE
            watcher_mod.FAULT_FILE = fault_path
            watcher_mod.SCHEDULE_FILE = Path(tmpdir) / "gorev_cizelgesi.json"

            try:
                watcher = JsonWatcher(poll_interval=0.1)
                received: list[list] = []
                watcher.fault_detected.connect(received.append)
                watcher.start()

                # Dosyayı yaz
                fault_path.write_text(
                    json.dumps(SAMPLE_DETECTIONS), encoding="utf-8"
                )

                # Sinyalin gelmesini bekle
                qtbot.waitSignal(watcher.fault_detected, timeout=3000)
                watcher.stop()

                assert len(received) >= 1
                assert received[0] == SAMPLE_DETECTIONS
            finally:
                watcher_mod.FAULT_FILE = original_fault
                watcher_mod.SCHEDULE_FILE = original_schedule

    def test_watcher_stops_cleanly(self, qtbot):
        """JsonWatcher stop() çağrısında temiz bitiş yapmalı."""
        watcher = JsonWatcher(poll_interval=0.1)
        watcher.start()
        time.sleep(0.2)
        watcher.stop()
        assert not watcher.isRunning()
