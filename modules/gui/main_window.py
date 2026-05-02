"""Ana pencere — tüm GUI bileşenlerini birleştirir.

MapWidget ve MaintenancePanel'i sekme düzeninde sunar;
JsonWatcher'ı başlatarak her iki bileşeni bağımsız günceller.
"""

from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .json_watcher import JsonWatcher
from .map_widget import MapWidget
from .maintenance_panel import MaintenancePanel

logger = logging.getLogger(__name__)

APP_TITLE = "GES Otonom Termal Denetim & Bakım Optimizasyon Sistemi"
APP_VERSION = "1.0.0"
WINDOW_MIN_W = 1200
WINDOW_MIN_H = 700


class MainWindow(QMainWindow):
    """Uygulama ana penceresi.

    Harita (sol) ve Bakım Paneli (sağ) olmak üzere iki bölüme ayrılmış
    splitter düzeni kullanır. JsonWatcher arka planda outputs/ dizinini
    izler ve değişiklikleri ilgili bileşenlere sinyal olarak iletir.

    Example:
        >>> app = QApplication(sys.argv)
        >>> window = MainWindow()
        >>> window.show()
        >>> sys.exit(app.exec())
    """

    def __init__(self) -> None:
        super().__init__()
        self._setup_window()
        self._setup_palette()
        self._setup_ui()
        self._setup_watcher()

    # ──────────────────────────────────────────────────────────────────────────
    # Kurulum
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        """Pencere başlığı, boyutu ve font ayarları."""
        self.setWindowTitle(f"{APP_TITLE} — v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        font = QFont("Inter", 10)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        QApplication.setFont(font)

    def _setup_palette(self) -> None:
        """Koyu tema renk paleti."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1A1A1A"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#E0E0E0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#1E1E1E"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#262626"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#E0E0E0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#2D2D2D"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E0E0E0"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#1565C0"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(palette)

    def _setup_ui(self) -> None:
        """Ana bileşenleri düzenler."""
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Üst başlık şeridi
        header = self._build_header()
        root_layout.addWidget(header)

        # Sol: harita | Sağ: bakım paneli
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background: #333; }")

        self._map_widget = MapWidget()
        self._maintenance_panel = MaintenancePanel()

        splitter.addWidget(self._map_widget)
        splitter.addWidget(self._maintenance_panel)
        splitter.setSizes([600, 600])

        root_layout.addWidget(splitter)

        # Durum çubuğu
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "QStatusBar { background: #111; color: #9E9E9E; font-size: 11px; }"
        )
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Sistem hazır — Simülasyon bekleniyor.")

    def _build_header(self) -> QWidget:
        """Üst başlık şeridini oluşturur."""
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("background: #0D1117; border-bottom: 1px solid #333;")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        title_label = QLabel(APP_TITLE)
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_label.setStyleSheet(
            "color: #E0E0E0; font-size: 14px; font-weight: bold; letter-spacing: 0.5px;"
        )
        layout.addWidget(title_label)
        return header

    def _setup_watcher(self) -> None:
        """JsonWatcher'ı başlatır ve sinyalleri bağlar."""
        self._watcher = JsonWatcher(parent=self)
        self._watcher.fault_detected.connect(self._map_widget.on_fault_detected)
        self._watcher.schedule_updated.connect(self._maintenance_panel.on_schedule_updated)
        self._watcher.watch_error.connect(self._on_watch_error)
        self._watcher.start()
        logger.info("JsonWatcher başlatıldı.")

    # ──────────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────────

    def _on_watch_error(self, message: str) -> None:
        """Dosya izleme hatalarını durum çubuğunda gösterir."""
        self._status_bar.showMessage(f"⚠ İzleme hatası: {message}")
        logger.warning("Watcher hatası: %s", message)

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        """Pencere kapatılınca watcher'ı durdurur."""
        self._watcher.stop()
        logger.info("Uygulama kapatıldı.")
        super().closeEvent(event)


def run_gui() -> None:
    """GUI uygulamasını başlatır.

    main.py veya bağımsız çalıştırma için giriş noktası.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("GES Denetim Sistemi")
    app.setApplicationVersion(APP_VERSION)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
