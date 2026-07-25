from datetime import datetime
from typing import Any, Dict, List

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from rapidfuzz import fuzz

from config import config
from core.logger import logger
from db.history_db import HistoryDatabase
from gui.styles.style_loader import load_component_style
from gui.widgets.card_item import CardItem


class CardView(QWidget):
    """View that displays notifications as cards with date range filter."""

    def __init__(self, db: HistoryDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_range = "Today"
        self.cached_notifications: List[Dict[str, Any]] = []
        self.sort_mode = "Date"
        self.search_query = ""

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Sidebar with date ranges
        sidebar = QVBoxLayout()
        sidebar.setSpacing(6)

        self.range_buttons = {}
        # Moved "Custom Date" to the bottom, right below "All"
        ranges = [
            "Today",
            "Yesterday",
            "Last 7 Days",
            "This Month",
            "All",
            "Custom Date",
        ]
        for r_name in ranges:
            btn = QPushButton(r_name)
            btn.setObjectName("SidebarFilterBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(110)
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _, name=r_name: self._set_range(name))
            sidebar.addWidget(btn)
            self.range_buttons[r_name] = btn

        # From / To Date Pickers Container for Custom Date range
        self.custom_date_container = QWidget()
        custom_layout = QVBoxLayout(self.custom_date_container)
        custom_layout.setContentsMargins(0, 4, 0, 4)
        custom_layout.setSpacing(4)

        self.from_lbl = QLabel("From:")
        self.from_lbl.setObjectName("DateLabel")
        self.date_from = QDateEdit()
        self.date_from.setObjectName("DateEdit")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setDisplayFormat("yyyy-MM-dd")

        self.to_lbl = QLabel("To:")
        self.to_lbl.setObjectName("DateLabel")
        self.date_to = QDateEdit()
        self.date_to.setObjectName("DateEdit")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("yyyy-MM-dd")

        self.date_go_btn = QPushButton("Go")
        self.date_go_btn.setObjectName("DateGoBtn")
        self.date_go_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.date_go_btn.clicked.connect(self._on_custom_date_go_clicked)

        custom_layout.addWidget(self.from_lbl)
        custom_layout.addWidget(self.date_from)
        custom_layout.addWidget(self.to_lbl)
        custom_layout.addWidget(self.date_to)
        custom_layout.addWidget(self.date_go_btn)

        self.custom_date_container.hide()
        sidebar.addWidget(self.custom_date_container)
        self.range_buttons["Today"].setChecked(True)
        sidebar.addStretch()

        main_layout.addLayout(sidebar, 0)

        # Scroll area for cards
        self.scroll = QScrollArea()
        self.scroll.setObjectName("CardScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.list_container = QWidget()
        self.list_container.setObjectName("CardListContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.list_container)
        main_layout.addWidget(self.scroll, 1)

        self.reload_theme()
        self.refresh_data()

    def reload_theme(self):
        theme = config.current_theme
        fg_alpha = config.data.get("fg_opacity", 1.0)

        bg_color = theme.get("bg_color", "#1e1e2e")
        border_color = theme.get("border_color", "#45475a")
        title_color = theme.get("title_color", "#cdd6f4")
        muted_color = theme.get("muted_color", "#6c7086")
        accent_color = theme.get("accent_color", "#89b4fa")

        style_vars = {
            "bg_rgba": config.hex_to_rgba(bg_color, 0.8),
            "bg_opaque": config.hex_to_rgba(bg_color, 1.0),
            "border_rgba": config.hex_to_rgba(border_color, 0.4),
            "border_radius": str(theme.get("border_radius", "6px")),
            "title_rgba": config.hex_to_rgba(title_color, fg_alpha),
            "muted_rgba": config.hex_to_rgba(muted_color, fg_alpha),
            "accent_rgba": config.hex_to_rgba(accent_color, fg_alpha),
        }

        try:
            rendered_qss = load_component_style("card_view.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error("Failed to load card_view.qss template; returned empty.")
        except Exception as e:
            logger.error(
                "Error applying card view stylesheet",
                extra={"error_type": type(e).__name__, "details": str(e)},
            )

    # ---------- Range selection ----------
    def _set_range(self, range_name: str):
        self.current_range = range_name
        logger.info(f"CardView range changed to: {range_name}")
        for name, btn in self.range_buttons.items():
            btn.setChecked(name == range_name)
        self.custom_date_container.setVisible(range_name == "Custom Date")
        self.refresh_data()

    def _on_custom_date_go_clicked(self):
        if self.current_range == "Custom Date":
            logger.info(
                f"Custom date range applied: {self.date_from.date().toString('yyyy-MM-dd')} to {self.date_to.date().toString('yyyy-MM-dd')}"
            )
            self.refresh_data()

    # ---------- Data loading and filtering ----------
    def refresh_data(self, sort_mode: str = None, search_query: str = None):
        """Load data based on range, sort, and search."""
        if sort_mode is not None:
            self.sort_mode = sort_mode
        if search_query is not None:
            self.search_query = search_query

        logger.debug(
            "Refreshing card view data",
            extra={
                "range": self.current_range,
                "sort_mode": self.sort_mode,
                "search_query": self.search_query,
            },
        )

        if self.current_range == "Custom Date":
            all_items = self.db.get_notifications_by_range("All")
            from_str = self.date_from.date().toString("yyyy-MM-dd")
            to_str = self.date_to.date().toString("yyyy-MM-dd")

            filtered_by_date = []
            for item in all_items:
                try:
                    ts_date = datetime.fromisoformat(item["timestamp"]).strftime(
                        "%Y-%m-%d"
                    )
                    # Check if notification falls inclusively within From and To dates
                    if from_str <= ts_date <= to_str:
                        filtered_by_date.append(item)
                except Exception:
                    continue
            self.cached_notifications = filtered_by_date
        else:
            self.cached_notifications = self.db.get_notifications_by_range(
                self.current_range
            )

        self._apply_sort_and_filter()

    def _apply_sort_and_filter(self):
        # Filter by search
        query = self.search_query.lower().strip()
        filtered = []
        if not query:
            filtered = self.cached_notifications[:]
        else:
            for item in self.cached_notifications:
                combined = f"{item['app_name']} {item['message']}".lower().strip()
                if (
                    query in combined
                    or fuzz.token_set_ratio(query.lower(), combined.lower()) >= 75
                ):
                    filtered.append(item)

        # Sort
        if self.sort_mode == "Date":
            filtered.sort(key=lambda x: x["timestamp"], reverse=True)
        elif self.sort_mode == "App":
            filtered.sort(key=lambda x: x["app_name"].lower())
        elif self.sort_mode == "Date and App":
            filtered.sort(
                key=lambda x: (x["timestamp"], x["app_name"].lower()), reverse=True
            )

        self.filtered_notifications = filtered
        logger.debug(f"CardView filtered items count: {len(filtered)}")
        self._populate_cards(filtered)

    def _populate_cards(self, items: List[Dict[str, Any]]):
        # Clear existing widgets (keep stretch)
        while self.list_layout.count() > 1:
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not items:
            empty = QLabel("No notifications found.")
            empty.setObjectName("EmptyNoticeLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            return

        for item in items:
            card = CardItem(item)
            card.delete_requested.connect(self._delete_single)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _delete_single(self, notification_id: int):
        logger.info(f"CardView deleting single notification ID: {notification_id}")
        self.db.delete_notification(notification_id)
        self.refresh_data()
