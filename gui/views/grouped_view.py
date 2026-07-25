from datetime import datetime
from typing import Any, Dict, List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from rapidfuzz import fuzz

from config import config
from core import logger
from db.history_db import HistoryDatabase
from gui.styles.style_loader import load_component_style
from gui.widgets.group_item import GroupItem


class GroupedView(QWidget):
    """View that displays notifications grouped by date or app, with collapsible headers."""

    def __init__(self, db: HistoryDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.cached_notifications: List[Dict[str, Any]] = []
        self.filtered_notifications: List[Dict[str, Any]] = []
        self.sort_mode = "Date"
        self.search_query = ""
        # Store references to group containers and their item widgets
        self.group_widgets: List[Tuple[QPushButton, QWidget]] = []

        self._init_ui()
        self.reload_theme()
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("GroupScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setObjectName("GroupListContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 4, 0)
        self.container_layout.setSpacing(6)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def reload_theme(self):
        theme = config.current_theme
        fg_alpha = config.data.get("fg_opacity", 1.0)

        bg_hex = theme.get("bg_color", "#1e1e2e")
        text_hex = theme.get("title_color", "#cdd6f4")
        border_hex = theme.get("border_color", "#45475a")
        muted_hex = theme.get("muted_color", "#6c7086")
        error_hex = theme.get("error_color", "#f38ba8")

        style_vars = {
            "group_header_bg_rgba": config.hex_to_rgba(bg_hex, 0.6),
            "group_header_border_rgba": config.hex_to_rgba(border_hex, 0.4),
            "group_header_hover_rgba": config.hex_to_rgba(border_hex, 0.6),
            "border_radius": str(theme.get("border_radius", "6px")),
            "title_rgba": config.hex_to_rgba(text_hex, fg_alpha),
            "muted_rgba": config.hex_to_rgba(muted_hex, fg_alpha),
            "error_rgba": config.hex_to_rgba(error_hex, fg_alpha),
            "bg_opaque": config.hex_to_rgba(bg_hex, 1.0),
        }

        try:
            rendered_qss = load_component_style("grouped_view.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error(
                    "Failed to load grouped_view.qss template; returned empty."
                )
        except Exception as e:
            pass

    def refresh_data(self, sort_mode: str = None, search_query: str = None):
        if sort_mode is not None:
            self.sort_mode = sort_mode
        if search_query is not None:
            self.search_query = search_query

        # Get all notifications
        self.cached_notifications = self.db.get_notifications_by_range("All")
        self._apply_sort_and_filter()

    def _apply_sort_and_filter(self):
        # Filter by search
        query = self.search_query.lower().strip()
        items = self.cached_notifications[:]
        if query:
            filtered = []
            for item in items:
                combined = f"{item['app_name']} {item['message']}".lower().strip()
                if query in combined or fuzz.token_set_ratio(query, combined) >= 75:
                    filtered.append(item)
            items = filtered

        self.filtered_notifications = items

        # Group based on sort_mode
        if self.sort_mode == "Date":
            grouped = self._group_by_date(items)
        elif self.sort_mode == "App":
            grouped = self._group_by_app(items)
        else:  # "Date and App"
            grouped = self._group_by_date_then_app(items)

        self._populate_groups(grouped)

    def _group_by_date(
        self, items: List[Dict[str, Any]]
    ) -> List[Tuple[str, List[Dict]]]:
        groups = {}
        for item in items:
            try:
                date_str = datetime.fromisoformat(item["timestamp"]).strftime(
                    "%Y-%m-%d"
                )
            except Exception:
                date_str = "Unknown"
            groups.setdefault(date_str, []).append(item)
        sorted_dates = sorted(groups.keys(), reverse=True)
        return [(date, groups[date]) for date in sorted_dates]

    def _group_by_app(
        self, items: List[Dict[str, Any]]
    ) -> List[Tuple[str, List[Dict]]]:
        groups = {}
        for item in items:
            app = item["app_name"]
            groups.setdefault(app, []).append(item)
        sorted_apps = sorted(groups.keys())
        return [(app, groups[app]) for app in sorted_apps]

    def _group_by_date_then_app(
        self, items: List[Dict[str, Any]]
    ) -> List[Tuple[str, List[Dict]]]:
        date_groups = {}
        for item in items:
            try:
                date_str = datetime.fromisoformat(item["timestamp"]).strftime(
                    "%Y-%m-%d"
                )
            except Exception:
                date_str = "Unknown"
            date_groups.setdefault(date_str, []).append(item)
        result = []
        for date in sorted(date_groups.keys(), reverse=True):
            sub_items = date_groups[date]
            sub_items.sort(key=lambda x: x["app_name"].lower())
            result.append((date, sub_items))
        return result

    def _populate_groups(self, groups: List[Tuple[str, List[Dict]]]):
        # Clear existing widgets (keep stretch)
        while self.container_layout.count() > 1:
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # Clean up nested layouts
                while child.layout().count():
                    item = child.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

        self.group_widgets.clear()

        if not groups:
            empty = QLabel("No notifications found.")
            empty.setObjectName("EmptyNoticeLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.container_layout.insertWidget(0, empty)
            return

        theme = config.current_theme
        arrow_color = str(theme.get("body_color", "#a6adc8"))

        for group_name, items in groups:
            group_frame = QFrame()
            group_frame.setObjectName("GroupFrame")
            group_layout = QVBoxLayout(group_frame)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(4)

            # --- HEADER BAR CONTAINER ---
            header_bar = QWidget()
            header_bar.setObjectName("GroupHeaderBar")
            header_bar_layout = QHBoxLayout(header_bar)
            header_bar_layout.setContentsMargins(8, 4, 8, 4)
            header_bar_layout.setSpacing(6)

            # Arrow Label (styled with custom color)
            arrow_label = QLabel(
                f"<span style='color: {arrow_color}; font-size: 11pt;'>▾</span>"
            )
            arrow_label.setObjectName("GroupArrowLabel")

            # Group Name Label
            title_label = QLabel(group_name)
            title_label.setObjectName("GroupTitleLabel")
            title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

            # Group Clear Button
            clear_group_btn = QPushButton("✕")
            clear_group_btn.setObjectName("GroupClearBtn")
            clear_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            header_bar_layout.addWidget(arrow_label)
            header_bar_layout.addWidget(title_label)
            header_bar_layout.addStretch()
            header_bar_layout.addWidget(clear_group_btn)

            # --- ITEMS CONTAINER ---
            items_widget = QWidget()
            items_widget.setObjectName("GroupItemsContainer")
            items_layout = QVBoxLayout(items_widget)
            items_layout.setContentsMargins(10, 0, 0, 0)
            items_layout.setSpacing(4)

            for item in items:
                list_item = GroupItem(item)
                list_item.delete_requested.connect(self._delete_single)
                items_layout.addWidget(list_item)

            # Toggle state & functionality
            is_expanded = [True]

            def toggle_group(
                event=None, state=is_expanded, widget=items_widget, arrow=arrow_label
            ):
                state[0] = not state[0]
                widget.setVisible(state[0])
                symbol = "▾" if state[0] else "▸"
                arrow.setText(
                    f"<span style='color: {arrow_color}; font-size: 11pt;'>{symbol}</span>"
                )

            # Make header bar clickable to expand/collapse
            header_bar.mousePressEvent = toggle_group

            # Connect group clear button
            clear_group_btn.clicked.connect(
                lambda _, g_items=items, g_name=group_name: self._clear_group_history(
                    g_items, g_name
                )
            )

            group_layout.addWidget(header_bar)
            group_layout.addWidget(items_widget)

            self.container_layout.insertWidget(
                self.container_layout.count() - 1, group_frame
            )

    def _clear_group_history(self, group_items: List[Dict[str, Any]], group_name: str):
        """Prompts the parent Action Center window's confirmation modal to delete group items."""
        action_center = self.window()
        if hasattr(action_center, "modal_backdrop"):
            ids_to_delete = [item["id"] for item in group_items if "id" in item]

            # Update modal text dynamically for category context
            if hasattr(action_center, "confirm_overlay"):
                title_lbl = action_center.confirm_overlay.findChild(
                    QLabel, "ConfirmTitle"
                )
                msg_lbl = action_center.confirm_overlay.findChild(QLabel, "ConfirmMsg")

                if title_lbl:
                    title_lbl.setText(f"Clear '{group_name}'?")
                if msg_lbl:
                    msg_lbl.setText(
                        f"Are you sure you want to delete {len(ids_to_delete)} notifications from this group?"
                    )

            # Temporarily redirect ActionCenter's yes-handler to clear only this group
            def confirm_yes_override():
                self.db.delete_notifications_by_ids(ids_to_delete)
                action_center.modal_backdrop.hide()

                # Restore original handler
                action_center.confirm_yes_btn.clicked.disconnect()
                action_center.confirm_yes_btn.clicked.connect(
                    action_center._on_confirm_clear_yes
                )

                self.refresh_data()

            action_center.confirm_yes_btn.clicked.disconnect()
            action_center.confirm_yes_btn.clicked.connect(confirm_yes_override)

            action_center.modal_backdrop.setGeometry(action_center.rect())
            action_center.modal_backdrop.show()
            action_center.modal_backdrop.raise_()

    def _delete_single(self, notification_id: int):
        self.db.delete_notification(notification_id)
        self.refresh_data()
