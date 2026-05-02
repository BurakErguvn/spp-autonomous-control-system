"""Bakım görev tablosu ve VRP rota paneli.

Optimizasyon modülünden gelen gorev_cizelgesi.json içeriğini
okunabilir tablo ve rota listesi olarak sunar.

Sinyal bağlantısı:
    JsonWatcher.schedule_updated → MaintenancePanel.on_schedule_updated
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# Tablo sütun başlıkları
TABLE_HEADERS = [
    "Panel ID",
    "Arıza Türü",
    "Öncelik",
    "Tahmini Maliyet (₺)",
    "Bakım Tarihi",
]

PRIORITY_COLORS: dict[str, str] = {
    "kritik": "#D32F2F",
    "yüksek": "#F57C00",
    "orta": "#FBC02D",
    "düşük": "#388E3C",
}


class MaintenancePanel(QWidget):
    """Bakım Yönetim Kontrol Paneli.

    Optimizasyon modülünden gelen görev çizelgesini tablo olarak,
    VRP rotasını sıralı liste olarak gösterir.

    Expected gorev_cizelgesi.json format::

        {
            "generated_at": "2026-03-27T10:15:00",
            "total_cost": 4500.0,
            "tasks": [
                {
                    "panel_id": 12,
                    "hasar": "hotspot",
                    "priority": "kritik",
                    "estimated_cost": 1200.0,
                    "scheduled_date": "2026-03-28"
                },
                ...
            ],
            "route": [0, 12, 7, 23, 5]
        }

    Example:
        >>> panel = MaintenancePanel()
        >>> watcher.schedule_updated.connect(panel.on_schedule_updated)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI kurulumu
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Kontrol paneli bileşenlerini oluşturur."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Başlık
        title = QLabel("🔧  Bakım Yönetim Kontrol Paneli")
        title.setStyleSheet(
            "color: #E0E0E0; font-size: 14px; font-weight: bold; padding: 8px 0;"
        )
        main_layout.addWidget(title)

        # Özet satırı
        self._summary_label = QLabel("Bekleniyor…")
        self._summary_label.setStyleSheet("color: #9E9E9E; font-size: 12px; padding: 2px 0 8px 0;")
        main_layout.addWidget(self._summary_label)

        # İçerik (tablo + rota yan yana)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # Görev tablosu
        task_group = QGroupBox("Bu Hafta Yapılacak Görevler")
        task_group.setStyleSheet(self._group_style())
        task_layout = QVBoxLayout(task_group)
        self._table = self._build_table()
        task_layout.addWidget(self._table)
        content_layout.addWidget(task_group, stretch=3)

        # VRP rota listesi
        route_group = QGroupBox("Optimal Bakım Rotası")
        route_group.setStyleSheet(self._group_style())
        route_layout = QVBoxLayout(route_group)
        self._route_list = QListWidget()
        self._route_list.setStyleSheet(
            "background: #1E1E1E; color: #E0E0E0; "
            "border: none; font-size: 12px;"
        )
        route_layout.addWidget(self._route_list)
        content_layout.addWidget(route_group, stretch=1)

        # Başlangıç durumu
        self._show_empty_state()

    def _build_table(self) -> QTableWidget:
        """Görev tablosu widget'ı oluşturur."""
        table = QTableWidget(0, len(TABLE_HEADERS))
        table.setHorizontalHeaderLabels(TABLE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(
            "QTableWidget { background: #1E1E1E; color: #E0E0E0; "
            "gridline-color: #333; border: none; font-size: 12px; }"
            "QTableWidget::item:alternate { background: #262626; }"
            "QHeaderView::section { background: #333; color: #E0E0E0; "
            "font-weight: bold; border: none; padding: 4px; }"
        )
        return table

    # ──────────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────────

    @pyqtSlot(dict)
    def on_schedule_updated(self, schedule: dict) -> None:
        """Optimizasyon çıktısını tabloya ve rota listesine yansıtır.

        Args:
            schedule: gorev_cizelgesi.json içeriği.
        """
        tasks = schedule.get("tasks", [])
        route = schedule.get("route", [])
        total_cost = schedule.get("total_cost", 0.0)
        generated_at = schedule.get("generated_at", "—")

        self._update_summary(len(tasks), total_cost, generated_at)
        self._populate_table(tasks)
        self._populate_route(route)

        logger.info("Bakım çizelgesi güncellendi: %d görev, %.0f₺", len(tasks), total_cost)

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _update_summary(self, task_count: int, total_cost: float, generated_at: str) -> None:
        """Özet satırını günceller."""
        self._summary_label.setText(
            f"Toplam {task_count} görev  |  "
            f"Tahmini maliyet: {total_cost:,.0f} ₺  |  "
            f"Oluşturulma: {generated_at}"
        )
        self._summary_label.setStyleSheet(
            "color: #B0BEC5; font-size: 12px; padding: 2px 0 8px 0;"
        )

    def _populate_table(self, tasks: list[dict]) -> None:
        """Görev listesini tabloya doldurur."""
        self._table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            values = [
                str(task.get("panel_id", "—")),
                task.get("hasar", "—"),
                task.get("priority", "—"),
                f"{task.get('estimated_cost', 0):,.0f}",
                task.get("scheduled_date", "—"),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Öncelik sütununu renklendir
                if col == 2:
                    color_hex = PRIORITY_COLORS.get(val.lower(), "#E0E0E0")
                    item.setForeground(QColor(color_hex))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                self._table.setItem(row, col, item)

    def _populate_route(self, route: list) -> None:
        """VRP rotasını liste olarak gösterir."""
        self._route_list.clear()

        if not route:
            self._route_list.addItem("Rota bilgisi bekleniyor…")
            return

        for step, panel_id in enumerate(route, start=1):
            item = QListWidgetItem(f"  {step}. Panel #{panel_id}")
            item.setForeground(QColor("#80CBC4"))
            self._route_list.addItem(item)

    def _show_empty_state(self) -> None:
        """İlk yüklemede boş durum mesajını gösterir."""
        self._table.setRowCount(1)
        placeholder = QTableWidgetItem("Optimizasyon çıktısı bekleniyor…")
        placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setForeground(QColor("#616161"))
        self._table.setSpan(0, 0, 1, len(TABLE_HEADERS))
        self._table.setItem(0, 0, placeholder)

        self._route_list.addItem("Rota bekleniyor…")

    @staticmethod
    def _group_style() -> str:
        """Grup kutusu stil dizisi."""
        return (
            "QGroupBox { color: #9E9E9E; font-size: 12px; font-weight: bold; "
            "border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
