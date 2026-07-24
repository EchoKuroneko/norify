import os
from datetime import datetime
from typing import Any, Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBitmap, QFont, QPainter, QPixmap, QRegion
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from config import config
from core.logger import logger
from gui.styles.style_loader import load_component_style


class GroupItem(QFrame):
    """Single item in the grouped view (simpler than card)."""

    delete_requested = pyqtSignal(int)

    def __init__(self, data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_id = data.get("id", -1)
        theme = config.current_theme
        fg_alpha = config.data.get("fg_opacity", 1.0)

        self.setObjectName("GroupListItem")
        bg_rgba = config.hex_to_rgba(theme.get("bg_color", "#1e1e2e"), 0.4)
        border_rgba = config.hex_to_rgba(theme.get("border_color", "#45475a"), 0.3)
        title_color = theme.get("title_color", "#cdd6f4")
        msg_color = theme.get("message_color", "#bac2de")

        style_vars = {
            "group_item_bg_rgba": bg_rgba,
            "group_item_border_rgba": border_rgba,
            "title_rgba": title_color,
            "msg_rgba": msg_color,
        }

        try:
            rendered_qss = load_component_style("group_item.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error("Failed to load group_item.qss template; returned empty.")
        except Exception as e:
            logger.error(
                "Error applying group item stylesheet",
                extra={"error_type": type(e).__name__, "details": str(e)},
            )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon
        icon_label = QLabel()
        icon_label.setObjectName("GroupItemIconLabel")
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        icon_path = data.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            raw_pixmap = QPixmap(icon_path)
            if not raw_pixmap.isNull():
                image = raw_pixmap.toImage()
                alpha_mask = image.createAlphaMask()
                region = QRegion(QBitmap.fromImage(alpha_mask))
                rect = region.boundingRect()
                if rect.isValid() and not rect.isEmpty():
                    raw_pixmap = raw_pixmap.copy(rect)
            src_pixmap = raw_pixmap.scaled(
                24,
                24,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            transparent_pixmap = QPixmap(24, 24)
            transparent_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(transparent_pixmap)
            painter.setOpacity(fg_alpha)
            x_offset = (24 - src_pixmap.width()) // 2
            y_offset = (24 - src_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, src_pixmap)
            painter.end()
            icon_label.setPixmap(transparent_pixmap)
        else:
            icon_label.setText("🔔")

        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        top_line = QHBoxLayout()
        app_label = QLabel(data.get("app_name", "Unknown App"))
        app_label.setObjectName("GroupItemTitleLabel")
        app_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        try:
            ts = datetime.fromisoformat(data["timestamp"])
            time_str = ts.strftime("%I:%M %p")
        except Exception:
            time_str = ""

        time_label = QLabel(time_str)
        time_label.setObjectName("GroupItemTimeLabel")
        time_label.setFont(QFont("Segoe UI", 8))

        top_line.addWidget(app_label)
        top_line.addStretch()
        top_line.addWidget(time_label)

        msg_label = QLabel(data.get("message", ""))
        msg_label.setObjectName("GroupItemMsgLabel")
        msg_label.setFont(QFont("Segoe UI", 8))
        msg_label.setWordWrap(True)

        text_layout.addLayout(top_line)
        text_layout.addWidget(msg_label)
        layout.addLayout(text_layout, 1)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setObjectName("GroupItemDeleteBtn")
        del_btn.setFixedSize(18, 18)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self._on_delete_clicked())
        layout.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignTop)

    def _on_delete_clicked(self):
        logger.debug(f"Delete requested for group item ID: {self.item_id}")
        self.delete_requested.emit(self.item_id)
