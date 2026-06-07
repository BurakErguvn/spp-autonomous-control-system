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
import math

from PyQt6.QtCore import Qt, QRect, QRectF, pyqtSlot
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QCursor, QPixmap
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

PANEL_W = 100  # piksel
PANEL_H = 70   # piksel
PANEL_GAP = 12 # piksel


class PanelItem(QGraphicsRectItem):
    """Tek bir güneş panelini temsil eden grafik öğesi.

    Args:
        panel_id: Panelin benzersiz tam sayı kimliği.
        row: Izgara satır konumu.
        col: Izgara sütun konumu.
    """

    def __init__(self, panel_id: int, row: int, col: int, default_image_path: str | None = None) -> None:
        x = col * (PANEL_W + PANEL_GAP)
        y = row * (PANEL_H + PANEL_GAP)
        super().__init__(QRectF(x, y, PANEL_W, PANEL_H))

        self.panel_id = panel_id
        self._fault: str | None = None
        self._confidence: float = 0.0
        self._default_image_path = default_image_path
        self._image_path = default_image_path
        self._gercek_durum: str | None = None

        self.setPen(QPen(COLOR_BORDER, 1.5))
        self.setBrush(QBrush(COLOR_NORMAL))
        self.setAcceptHoverEvents(True)

        # Panel ID etiketi (okunabilirlik için yarı saydam siyah arka plan ile)
        self._label = QGraphicsTextItem(self)
        self._label.setHtml(
            f"<div style='background-color: rgba(0,0,0,0.65); padding: 1px 4px; border-radius: 2px; font-family: Inter, sans-serif; color: white;'><b>{panel_id}</b></div>"
        )
        self._label.setPos(x + 2, y + 2)

        # Varsayılan resmi yükle
        self.set_unscanned_image(default_image_path)

    def mark_fault(
        self,
        fault_type: str,
        confidence: float,
        image_path: str | None = None,
        gercek_durum: str | None = None,
    ) -> None:
        """Paneli arızalı veya taranmış olarak işaretler.

        Args:
            fault_type: "hotspot", "mikro_catlak", "tozlanma" veya "sağlam".
            confidence: Güven skoru (0.0–1.0).
            image_path: Görüntü dosya yolu.
            gercek_durum: Gerçek hasar durumu.
        """
        self._fault = fault_type
        self._confidence = confidence
        self._image_path = image_path
        self._gercek_durum = gercek_durum

        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                PANEL_W,
                PANEL_H,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setBrush(QBrush(scaled_pixmap))
            
            if fault_type == "sağlam":
                self.setPen(QPen(COLOR_NORMAL, 1.5))
            else:
                color = FAULT_COLORS.get(fault_type, COLOR_HOTSPOT)
                self.setPen(QPen(color, 3.0))
        else:
            color = FAULT_COLORS.get(fault_type, COLOR_NORMAL) if fault_type != "sağlam" else COLOR_NORMAL
            self.setBrush(QBrush(color))
            self.setPen(QPen(COLOR_BORDER, 1.5))

        logger.debug(
            "Panel %d → %s (%.2f), gerçek: %s",
            self.panel_id,
            fault_type,
            confidence,
            gercek_durum,
        )

    def set_unscanned_image(self, image_path: str | None) -> None:
        """Taranmamış panel için resmi yarı saydam (soluk) şekilde yükler."""
        self._image_path = image_path
        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                PANEL_W,
                PANEL_H,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setBrush(QBrush(scaled_pixmap))
            self.setPen(QPen(QColor("#757575"), 1.5, Qt.PenStyle.DashLine))
        else:
            self.setBrush(QBrush(COLOR_NORMAL))
            self.setPen(QPen(COLOR_BORDER, 1.5))

    def reset(self) -> None:
        """Paneli taranmamış başlangıç durumuna döndürür."""
        self._fault = None
        self._confidence = 0.0
        self._gercek_durum = None
        self.set_unscanned_image(self._default_image_path)

    def hoverEnterEvent(self, event) -> None:  # noqa: N802
        """Fare üzerine gelince tooltip göster (kalıcı)."""
        if self._fault:
            model_tahmini = {
                "hotspot": "Hotspot (Sıcak Nokta)",
                "mikro_catlak": "Mikro Çatlak",
                "tozlanma": "Tozlanma",
                "sağlam": "Sağlam"
            }.get(self._fault, self._fault)
            
            gercek = {
                "hotspot": "Hotspot (Sıcak Nokta)",
                "mikro_catlak": "Mikro Çatlak",
                "tozlanma": "Tozlanma",
                "sağlam": "Sağlam"
            }.get(self._gercek_durum, "Bilinmiyor" if self._gercek_durum is None else self._gercek_durum)
            
            dogruluk = "✓ Doğru Tahmin" if self._fault == self._gercek_durum else "✗ Yanlış Tahmin"
            
            tip = (
                f"Panel #{self.panel_id}\n"
                f"Model Tahmini: {model_tahmini} (Güven: {self._confidence:.0%})\n"
                f"Gerçek Durum: {gercek}\n"
                f"Değerlendirme: {dogruluk}"
            )
        else:
            tip = f"Panel #{self.panel_id} — Sağlam (Taranmadı)"
        
        view = None
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
        QToolTip.showText(QCursor.pos(), tip, view, QRect(), 1000000)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # noqa: N802
        """Fare ayrılınca tooltip'i gizle."""
        QToolTip.hideText()
        super().hoverLeaveEvent(event)


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
        self._route_items: list[QGraphicsRectItem | QGraphicsLineItem] = []

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

    def clear_routes(self) -> None:
        """Tüm rota çizgilerini haritadan temizler."""
        for item in self._route_items:
            try:
                self._scene.removeItem(item)
            except Exception:
                pass
        self._route_items.clear()

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
                image_path = det.get("image_path")
                gercek_durum = det.get("gercek_durum")
                panel_item.mark_fault(fault, confidence, image_path, gercek_durum)
            else:
                logger.warning(
                    "Haritada panel_id=%d bulunamadı — panel_layout.json kontrol edilmeli.",
                    panel_id,
                )

    @pyqtSlot(dict)
    def on_schedule_updated(self, schedule: dict) -> None:
        """Optimizasyondan gelen rota bilgilerini haritaya neon çizgiler ve yön oklarıyla çizer."""
        # Eski rotaları temizle
        for item in self._route_items:
            try:
                self._scene.removeItem(item)
            except Exception:
                pass
        self._route_items.clear()

        routes = schedule.get("routes", {})
        if not routes:
            return

        # Ekip renkleri (Neon Mavi/Cyan, Neon Pembe/Magenta, Neon Sarı/Altın)
        team_colors = {
            "1": QColor("#00E5FF"),
            "2": QColor("#FF007F"),
            "3": QColor("#FFD600"),
        }

        depot_center_x = -PANEL_W - 30 + PANEL_W / 2
        depot_center_y = PANEL_H / 2

        for team_id, panel_list in routes.items():
            if not panel_list:
                continue

            color = team_colors.get(team_id, QColor("#FFFFFF"))
            pen = QPen(color, 2.5, Qt.PenStyle.SolidLine)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)

            # Rota adımlarını birleştir (Depo -> Paneller -> Depo)
            points = [(depot_center_x, depot_center_y)]
            for pid in panel_list:
                panel_item = self._panels.get(pid)
                if panel_item:
                    rect = panel_item.rect()
                    cx = rect.x() + rect.width() / 2
                    cy = rect.y() + rect.height() / 2
                    points.append((cx, cy))
            points.append((depot_center_x, depot_center_y))

            # Adımlar arasında çizgiler ve yön okları çiz
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                line_item = self._scene.addLine(x1, y1, x2, y2, pen)
                line_item.setEnabled(False)  # Fare etkileşimini engelle
                self._route_items.append(line_item)
                
                # Yolun yönünü gösteren küçük bir yön oku çiz
                self._draw_arrow(x1, y1, x2, y2, color)

    def _draw_arrow(self, x1: float, y1: float, x2: float, y2: float, color: QColor) -> None:
        """İki nokta arasındaki doğrunun ortasına yön oku çizer."""
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        dx = x2 - x1
        dy = y2 - y1
        angle = math.atan2(dy, dx)

        arrow_len = 8.0
        arrow_angle = math.pi / 6  # 30 derece

        p1_x = mx - arrow_len * math.cos(angle - arrow_angle)
        p1_y = my - arrow_len * math.sin(angle - arrow_angle)
        p2_x = mx - arrow_len * math.cos(angle + arrow_angle)
        p2_y = my - arrow_len * math.sin(angle + arrow_angle)

        pen = QPen(color, 2.0)
        line1 = self._scene.addLine(mx, my, p1_x, p1_y, pen)
        line2 = self._scene.addLine(mx, my, p2_x, p2_y, pen)
        
        line1.setEnabled(False)
        line2.setEnabled(False)
        
        self._route_items.append(line1)
        self._route_items.append(line2)

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

        # Depo öğesini çiz
        depot_rect = QRectF(-PANEL_W - 30, 0, PANEL_W, PANEL_H)
        self._depot_item = QGraphicsRectItem(depot_rect)
        self._depot_item.setBrush(QBrush(QColor("#0D1117")))
        self._depot_item.setPen(QPen(QColor("#00E676"), 2.0, Qt.PenStyle.DashLine))
        self._scene.addItem(self._depot_item)

        # Depo etiketi
        depot_label = QGraphicsTextItem(self._depot_item)
        depot_label.setHtml("<div style='color:#00E676; font-family: Inter, sans-serif; font-size: 9px; font-weight: bold;'>DEPO</div>")
        depot_label.setPos(-PANEL_W - 20, PANEL_H / 2 - 10)

        # Resim havuzunu yükle (taranmayan panellerin resmini göstermek için)
        dataset_images_dir = Path("data") / "SOLAR PANEL DET.v1i.yolo26" / "test" / "images"
        image_pool: list[Path] = []
        if dataset_images_dir.exists():
            image_pool = sorted(
                list(dataset_images_dir.glob("*.jpg"))
                + list(dataset_images_dir.glob("*.jpeg"))
                + list(dataset_images_dir.glob("*.png"))
            )

        for panel_data in layout.get("panels", []):
            pid = int(panel_data["panel_id"])
            default_img_path = None
            if image_pool:
                default_img_path = str(image_pool[pid % len(image_pool)])

            item = PanelItem(
                panel_id=pid,
                row=panel_data["row"],
                col=panel_data["col"],
                default_image_path=default_img_path
            )
            self._scene.addItem(item)
            self._panels[pid] = item

        logger.info("%d panel haritaya yüklendi.", len(self._panels))

    @staticmethod
    def _build_legend_html() -> str:
        """Renk kodlu açıklama HTML'i oluşturur."""
        return (
            "<small>"
            "<span style='color:#2E7D32'>■</span> Sağlam &nbsp;"
            "<span style='color:#D32F2F'>■</span> Hotspot &nbsp;"
            "<span style='color:#F57C00'>■</span> Mikro Çatlak &nbsp;"
            "<span style='color:#FBC02D'>■</span> Tozlanma &nbsp;|&nbsp; "
            "<b>Rotalar:</b> "
            "<span style='color:#00E5FF'>━</span> Ekip 1 &nbsp;"
            "<span style='color:#FF007F'>━</span> Ekip 2 &nbsp;"
            "<span style='color:#FFD600'>━</span> Ekip 3"
            "</small>"
        )
