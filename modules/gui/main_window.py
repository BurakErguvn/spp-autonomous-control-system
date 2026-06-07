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
    QHBoxLayout,
    QWidget,
    QComboBox,
    QPushButton,
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

    def __init__(self, run_pipeline_callback=None, initial_scenario=None) -> None:
        super().__init__()
        self._run_pipeline_callback = run_pipeline_callback
        
        self._setup_window()
        self._setup_palette()
        self._setup_ui()
        self._setup_watcher()
        
        # Başlangıç senaryosunu seçicide ayarla (None ise "None" - Tüm Tesis)
        scen_str = str(initial_scenario) if initial_scenario else "None"
        index = self._scenario_combo.findData(scen_str)
        if index >= 0:
            self._scenario_combo.setCurrentIndex(index)

        # Başlangıçta arka planda çalışan simülasyon nedeniyle arayüzü kilitle
        self._restart_btn.setEnabled(False)
        self._scenario_combo.setEnabled(False)
        scen_name = "Tüm Tesis" if scen_str == "None" else f"Senaryo {scen_str}"
        self._status_bar.showMessage(f"Simülasyon çalışıyor ({scen_name})...")

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

        # Üst başlık şeridi (Kontrolleri ve Açıklamayı da içerir)
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
        """Üst başlık şeridini ve senaryo kontrollerini oluşturur."""
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("background: #0D1117; border-bottom: 1px solid #333;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Uygulama Başlığı
        title_label = QLabel(APP_TITLE)
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_label.setStyleSheet(
            "color: #E0E0E0; font-size: 12px; font-weight: bold; letter-spacing: 0.5px;"
        )
        layout.addWidget(title_label)

        # Dikey ayırıcı çizgi
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #2D333F;")
        sep.setFixedHeight(18)
        layout.addWidget(sep)

        # Senaryo Seçici Etiket
        scen_label = QLabel("Senaryo:")
        scen_label.setStyleSheet("color: #8B949E; font-weight: bold; font-size: 11px;")
        layout.addWidget(scen_label)

        # Senaryo Seçici ComboBox (Kompakt)
        self._scenario_combo = QComboBox()
        self._scenario_combo.setStyleSheet(
            "QComboBox { background: #21262D; color: #C9D1D9; border: 1px solid #30363D; border-radius: 4px; padding: 2px 6px; font-size: 11px; min-width: 140px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #21262D; color: #C9D1D9; selection-background-color: #1F6FEB; }"
        )
        self._scenario_combo.addItem("Senaryo A (Tozlanma)", "A")
        self._scenario_combo.addItem("Senaryo B (Hotspot)", "B")
        self._scenario_combo.addItem("Senaryo C (Çatlaklar)", "C")
        self._scenario_combo.addItem("Tam Koşum (Tüm Tesis)", "None")
        layout.addWidget(self._scenario_combo)

        # Yeniden Başlat Butonu (Kompakt)
        self._restart_btn = QPushButton("🔄 Yeniden Başlat")
        self._restart_btn.setStyleSheet(
            "QPushButton { background: #1F6FEB; color: white; border: none; border-radius: 4px; padding: 3px 10px; font-weight: bold; font-size: 11px; }"
            "QPushButton:hover { background: #388BFD; }"
            "QPushButton:pressed { background: #0D47A1; }"
        )
        self._restart_btn.clicked.connect(self._on_restart_clicked)
        layout.addWidget(self._restart_btn)

        # Açıklama Alanı (Kompakt)
        self._desc_label = QLabel()
        self._desc_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        layout.addWidget(self._desc_label, stretch=1)

        # Sinyal bağlantısı
        self._scenario_combo.currentIndexChanged.connect(self._on_scenario_changed)
        
        # İlk senaryo açıklamasını yükle
        self._on_scenario_changed()

        return header

    def _on_scenario_changed(self) -> None:
        """Senaryo değişiminde açıklamayı ve ipucunu (tooltip) günceller."""
        scen_id = self._scenario_combo.currentData()
        
        brief_desc = {
            "A": "Ekonomik olmayan tozlanma bakımı ertelenir (0 görev).",
            "B": "Uç noktalardaki 2 hotspot için acil rota çizilir.",
            "C": "10 dağınık çatlak tamiri 3 ekibe paylaştırılır.",
            "None": "Tüm 30 panel taranarak optimal plan çıkarılır."
        }
        
        full_desc = {
            "A": "Senaryo A: Tesisin %5'inde tozlanma (2 panel) simüle edilir. Bakım maliyeti fırsat kaybından yüksek olduğundan model bakımı ertelemelidir.",
            "B": "Senaryo B: Uç noktalarda 2 hotspot (must-fix) simüle edilir. Coğrafi olarak en uzak köşelere yangın riski nedeniyle acil müdahale rotası çizilir.",
            "C": "Senaryo C: Tesis genelinde 10 dağınık mikro çatlak simüle edilir. İş yükünün 3 araca (ekibe) en dengeli şekilde paylaştırılması beklenir.",
            "None": "Tam Koşum: Tüm 30 panel sırayla taranarak arızalı/sağlam durumlar tespit edilir ve optimal bakım planı çıkarılır."
        }
        
        self._desc_label.setText(brief_desc.get(scen_id, ""))
        self._desc_label.setToolTip(full_desc.get(scen_id, ""))
        self._scenario_combo.setToolTip(full_desc.get(scen_id, ""))

    def _on_restart_clicked(self) -> None:
        """Seçili senaryoya göre simülasyonu yeniden başlatır."""
        scen_id = self._scenario_combo.currentData()
        scen_val = None if scen_id == "None" else scen_id
        
        # 1. Arayüzü temizle ve kontrolleri kilitle
        self._restart_btn.setEnabled(False)
        self._scenario_combo.setEnabled(False)
        self._map_widget.clear_routes()
        self._map_widget.on_fault_detected([])  # Tüm panelleri varsayılan resimli/taranmamış yapar
        self._maintenance_panel.on_schedule_updated(
            {"tasks": [], "routes": {"1": [], "2": [], "3": []}, "total_cost_tl": 0}
        )
        scen_name = "Tüm Tesis" if scen_id == "None" else f"Senaryo {scen_id}"
        self._status_bar.showMessage(f"Simülasyon çalışıyor ({scen_name})...")
        
        # 2. Callback fonksiyonunu çağır (ayrı bir thread'de)
        if self._run_pipeline_callback:
            import threading
            threading.Thread(target=self._run_pipeline_callback, args=(scen_val,), daemon=True).start()

    def _setup_watcher(self) -> None:
        """JsonWatcher'ı başlatır ve sinyalleri bağlar."""
        self._watcher = JsonWatcher(parent=self)
        self._watcher.fault_detected.connect(self._map_widget.on_fault_detected)
        self._watcher.schedule_updated.connect(self._maintenance_panel.on_schedule_updated)
        self._watcher.schedule_updated.connect(self._map_widget.on_schedule_updated)
        self._watcher.schedule_updated.connect(self._on_schedule_updated)
        self._watcher.watch_error.connect(self._on_watch_error)
        self._watcher.start()
        logger.info("JsonWatcher başlatıldı.")

    # ──────────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────────

    def _on_schedule_updated(self, schedule: dict) -> None:
        """Optimizasyon tamamlandığında arayüzü tekrar aktif hale getirir."""
        self._restart_btn.setEnabled(True)
        self._scenario_combo.setEnabled(True)
        scen_id = self._scenario_combo.currentData()
        scen_name = "Tüm Tesis" if scen_id == "None" else f"Senaryo {scen_id}"
        self._status_bar.showMessage(f"Simülasyon tamamlandı ({scen_name}).")

    def _on_watch_error(self, message: str) -> None:
        """Dosya izleme hatalarını durum çubuğunda gösterir."""
        self._status_bar.showMessage(f"⚠ İzleme hatası: {message}")
        self._restart_btn.setEnabled(True)
        self._scenario_combo.setEnabled(True)
        logger.warning("Watcher hatası: %s", message)

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        """Pencere kapatılınca watcher'ı durdurur."""
        self._watcher.stop()
        logger.info("Uygulama kapatıldı.")
        super().closeEvent(event)


def run_gui(run_pipeline_callback=None, initial_scenario=None) -> None:
    """GUI uygulamasını başlatır.

    main.py veya bağımsız çalıştırma için giriş noktası.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("GES Denetim Sistemi")
    app.setApplicationVersion(APP_VERSION)

    window = MainWindow(run_pipeline_callback=run_pipeline_callback, initial_scenario=initial_scenario)
    window.show()
    sys.exit(app.exec())
