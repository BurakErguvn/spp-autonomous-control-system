"""Etkileşimli GES santral haritası bileşeni (Dijital İkiz).

Panel ızgarasını çizer; YZ modülünden gelen arıza tespitlerini
arıza türüne göre renk kodlu olarak haritada işaretler.

Sinyal bağlantısı:
    JsonWatcher.fault_detected → MapWidget.on_fault_detected
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QRectF, pyqtSlot
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QCursor
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QLabel,
)

logger = logging.getLogger(__name__)

PANEL_LAYOUT_PATH = Path(__file__).parent / "assets" / "panel_layout.json"

# ── Renk paleti ──────────────────────────────────────────────────────────────
COLOR_NORMAL = QColor("#2E7D32")       # Koyu yeşil — sağlam panel
COLOR_HOTSPOT = QColor("#D32F2F")      # Kırmızı — ısınma noktası
COLOR_MIKRO_CATLAK = QColor("#F57C00") # Turuncu — mikro çatlak
COLOR_TOZLANMA = QColor("#FBC02D")     # Sarı — tozlanma
COLOR_BORDER = QColor("#1B5E20")       # Panel çerçevesi
COLOR_BG = QColor("#121212")           # Arka plan

FAULT_COLORS: dict[str, QColor] = {
    "hotspot": COLOR_HOTSPOT,
    "mikro_catlak": COLOR_MIKRO_CATLAK,
    "tozlanma": COLOR_TOZLANMA,
}

PANEL_W = 60   # piksel
PANEL_H = 40   # piksel
PANEL_GAP = 10 # piksel


class PanelItem(QGraphicsRectItem):
    """Tek bir güneş panelini temsil eden grafik öğesi.

    Args:
        panel_id: Panelin benzersiz tam sayı kimliği.
        row: Izgara satır konumu.
        col: Izgara sütun konumu.
    """

    def __init__(self, panel_id: int, row: int, col: int) -> None:
        x = col * (PANEL_W + PANEL_GAP)
        y = row * (PANEL_H + PANEL_GAP)
        super().__init__(QRectF(x, y, PANEL_W, PANEL_H))

        self.panel_id = panel_id
        self._fault: str | None = None
        self._confidence: float = 0.0

        self.setPen(QPen(COLOR_BORDER, 1.5))
        self.setBrush(QBrush(COLOR_NORMAL))
        self.setAcceptHoverEvents(True)

        # Panel ID etiketi
        self._label = QGraphicsTextItem(str(panel_id), self)
        self._label.setDefaultTextColor(QColor("#FFFFFF"))
        font = QFont("Inter", 7, QFont.Weight.Bold)
        self._label.setFont(font)
        self._label.setPos(x + 2, y + 2)

    def mark_fault(self, fault_type: str, confidence: float) -> None:
        """Paneli arızalı olarak işaretler.

        Args:
            fault_type: "hotspot", "mikro_catlak" veya "tozlanma".
            confidence: Güven skoru (0.0–1.0).
        """
        self._fault = fault_type
        self._confidence = confidence
        color = FAULT_COLORS.get(fault_type, COLOR_NORMAL)
        self.setBrush(QBrush(color))
        logger.debug("Panel %d → %s (%.2f)", self.panel_id, fault_type, confidence)

    def reset(self) -> None:
        """Paneli sağlam duruma döndürür."""
        self._fault = None
        self._confidence = 0.0
        self.setBrush(QBrush(COLOR_NORMAL))

    def hoverEnterEvent(self, event) -> None:  # noqa: N802
        """Fare üzerine gelince tooltip göster."""
        if self._fault:
            tip = (
                f"Panel #{self.panel_id}\n"
                f"Arıza: {self._fault}\n"
                f"Güven: {self._confidence:.0%}"
            )
        else:
            tip = f"Panel #{self.panel_id} — Sağlam"
        QToolTip.showText(QCursor.pos(), tip)
        super().hoverEnterEvent(event)


class MapWidget(QWidget):
    """Etkileşimli GES santral haritası (Dijital İkiz).

    panel_layout.json'dan ızgara yapısını yükler ve arıza tespitlerini
    renk kodlu olarak haritada gösterir.

    Example:
        >>> map_widget = MapWidget()
        >>> watcher.fault_detected.connect(map_widget.on_fault_detected)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._panels: dict[int, PanelItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🗺️  Santral Dijital Haritası")
        title.setStyleSheet(
            "color: #E0E0E0; font-size: 14px; font-weight: bold; padding: 8px;"
        )
        layout.addWidget(title)

        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(COLOR_BG))

        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(self._view.renderHints())
        self._view.setStyleSheet("border: none; background: #121212;")
        layout.addWidget(self._view)

        self._legend_label = QLabel(self._build_legend_html())
        self._legend_label.setTextFormat(Qt.TextFormat.RichText)
        self._legend_label.setStyleSheet("padding: 4px;")
        layout.addWidget(self._legend_label)

        self._load_layout()

    # ──────────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────────

    @pyqtSlot(list)
    def on_fault_detected(self, detections: list[dict]) -> None:
        """YZ'den gelen arıza listesini haritaya yansıtır.

        Args:
            detections: ariza_verileri.json içeriği (list of dict).
        """
        # Her güncellemede önce tüm panelleri sıfırla
        for panel in self._panels.values():
            panel.reset()

        for det in detections:
            panel_id = det.get("panel_id")
            fault = det.get("hasar")
            confidence = det.get("guven_skoru", 0.0)

            if panel_id is None or fault is None:
                continue

            panel_item = self._panels.get(panel_id)
            if panel_item:
                panel_item.mark_fault(fault, confidence)
            else:
                logger.warning(
                    "Haritada panel_id=%d bulunamadı — panel_layout.json kontrol edilmeli.",
                    panel_id,
                )

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _load_layout(self) -> None:
        """panel_layout.json dosyasından panel ızgarasını yükler."""
        if not PANEL_LAYOUT_PATH.exists():
            logger.error("panel_layout.json bulunamadı: %s", PANEL_LAYOUT_PATH)
            return

        try:
            with open(PANEL_LAYOUT_PATH, encoding="utf-8") as f:
                layout = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("panel_layout.json okunamadı: %s", exc)
            return

        for panel_data in layout.get("panels", []):
            item = PanelItem(
                panel_id=panel_data["panel_id"],
                row=panel_data["row"],
                col=panel_data["col"],
            )
            self._scene.addItem(item)
            self._panels[panel_data["panel_id"]] = item

        logger.info("%d panel haritaya yüklendi.", len(self._panels))

    @staticmethod
    def _build_legend_html() -> str:
        """Renk kodlu açıklama HTML'i oluşturur."""
        return (
            "<small>"
            "<span style='color:#2E7D32'>■</span> Sağlam &nbsp;"
            "<span style='color:#D32F2F'>■</span> Hotspot &nbsp;"
            "<span style='color:#F57C00'>■</span> Mikro Çatlak &nbsp;"
            "<span style='color:#FBC02D'>■</span> Tozlanma"
            "</small>"
        )
