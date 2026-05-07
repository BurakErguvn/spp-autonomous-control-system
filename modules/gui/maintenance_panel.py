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
    "Ekip",
    "Süre (dk)",
    "Maliyet (₺)",
    "Bakım Tarihi",
]

PRIORITY_COLORS: dict[str, str] = {
    "kritik": "#D32F2F",
    "yüksek": "#F57C00",
    "orta": "#FBC02D",
    "düşük": "#388E3C",
}

# Ekip bazlı renk paleti (3 ekip için)
TEAM_COLORS: list[str] = ["#80CBC4", "#FFAB91", "#90CAF9"]


class MaintenancePanel(QWidget):
    """Bakım Yönetim Kontrol Paneli.

    Optimizasyon modülünden gelen görev çizelgesini tablo olarak,
    VRP rotasını sıralı liste olarak gösterir.

    Beklenen gorev_cizelgesi.json formatı::

        {
            "generated_at": "...",
            "total_cost_tl": 12450.0,
            "total_distance_km": 4.2,
            "total_service_time_min": 980,
            "team_count": 3,
            "tasks": [
                {
                    "panel_id": 12,
                    "hasar": "hotspot",
                    "priority": "kritik",
                    "estimated_cost": 1570.0,
                    "service_min": 45,
                    "team_id": 1,
                    "scheduled_date": "2026-03-28"
                },
                ...
            ],
            "routes": {
                "1": [12, 7],
                "2": [23, 5],
                "3": []
            }
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
        routes = schedule.get("routes") or {}
        # Geriye dönük uyumluluk: eski "route" alanı varsa tek ekip listesi olarak ele al
        if not routes and "route" in schedule:
            routes = {"1": schedule.get("route", [])}

        total_cost = schedule.get("total_cost_tl", schedule.get("total_cost", 0.0))
        total_km = schedule.get("total_distance_km", 0.0)
        generated_at = schedule.get("generated_at", "—")

        self._update_summary(len(tasks), total_cost, total_km, generated_at, schedule.get("note"))
        self._populate_table(tasks)
        self._populate_routes(routes)

        logger.info(
            "Bakım çizelgesi güncellendi: %d görev | %.0f TL | %d ekip",
            len(tasks),
            total_cost,
            len(routes),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _update_summary(
        self,
        task_count: int,
        total_cost: float,
        total_km: float,
        generated_at: str,
        note: str | None = None,
    ) -> None:
        """Özet satırını günceller."""
        text = (
            f"Toplam {task_count} görev  |  "
            f"Tahmini maliyet: {total_cost:,.0f} ₺  |  "
            f"Mesafe: {total_km:.2f} km  |  "
            f"Oluşturulma: {generated_at}"
        )
        if note:
            text += f"\n{note}"
        self._summary_label.setText(text)
        self._summary_label.setStyleSheet(
            "color: #B0BEC5; font-size: 12px; padding: 2px 0 8px 0;"
        )

    def _populate_table(self, tasks: list[dict]) -> None:
        """Görev listesini tabloya doldurur."""
        if not tasks:
            self._show_empty_state()
            return

        self._table.clearSpans()
        self._table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            values = [
                str(task.get("panel_id", "—")),
                task.get("hasar", "—"),
                task.get("priority", "—"),
                f"#{task.get('team_id', '—')}",
                str(task.get("service_min", "—")),
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

    def _populate_routes(self, routes: dict) -> None:
        """3 ekip için ayrı başlıklı rota listesi gösterir."""
        self._route_list.clear()

        if not routes:
            self._route_list.addItem("Rota bilgisi bekleniyor…")
            return

        any_visited = False
        # Ekip ID'leri string ya da int olabilir; sırala
        sorted_team_ids = sorted(routes.keys(), key=lambda k: int(k))
        for idx, team_id in enumerate(sorted_team_ids):
            panels = routes[team_id]
            color = TEAM_COLORS[idx % len(TEAM_COLORS)]

            header = QListWidgetItem(f"▼ Ekip #{team_id}  ({len(panels)} panel)")
            header.setForeground(QColor(color))
            font = header.font()
            font.setBold(True)
            self._route_list.addItem(header)

            if not panels:
                placeholder = QListWidgetItem("    (görev atanmadı)")
                placeholder.setForeground(QColor("#616161"))
                self._route_list.addItem(placeholder)
                continue

            any_visited = True
            for step, panel_id in enumerate(panels, start=1):
                item = QListWidgetItem(f"    {step}. Panel #{panel_id}")
                item.setForeground(QColor(color))
                self._route_list.addItem(item)

        if not any_visited:
            self._route_list.addItem("Hiç ekip görev almadı.")

    def _show_empty_state(self) -> None:
        """İlk yüklemede veya görev olmadığında boş durum mesajını gösterir."""
        self._table.clearSpans()
        self._table.setRowCount(1)
        placeholder = QTableWidgetItem("Optimizasyon çıktısı bekleniyor…")
        placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setForeground(QColor("#616161"))
        self._table.setSpan(0, 0, 1, len(TABLE_HEADERS))
        self._table.setItem(0, 0, placeholder)

    @staticmethod
    def _group_style() -> str:
        """Grup kutusu stil dizisi."""
        return (
            "QGroupBox { color: #9E9E9E; font-size: 12px; font-weight: bold; "
            "border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
