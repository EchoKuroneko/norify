import os
from datetime import datetime
from typing import Any, Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBitmap, QFont, QPainter, QPixmap, QRegion
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from config import config
from core.logger import logger
from gui.styles.style_loader import load_component_style


class CardItem(QFrame):
    """Individual card representing a past notification."""

    delete_requested = pyqtSignal(int)

    def __init__(self, data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_id = data.get("id", -1)
        theme = config.current_theme
        fg_alpha = config.data.get("fg_opacity", 1.0)

        self.setObjectName("Card")
        bg_rgba = config.hex_to_rgba(theme.get("bg_color", "#1e1e2e"), 0.6)
        border_rgba = config.hex_to_rgba(theme.get("border_color", "#45475a"), 0.4)
        title_color = theme.get("title_color", "#cdd6f4")
        body_color = theme.get("body_color", "#cdd6f4")
        muted_color = theme.get("muted_color", "#6c7086")
        error_color = theme.get("error_color", "#f38ba8")

        style_vars = {
            "card_bg_rgba": bg_rgba,
            "card_border_rgba": border_rgba,
            "title_rgba": config.hex_to_rgba(title_color, fg_alpha),
            "msg_rgba": config.hex_to_rgba(body_color, fg_alpha),
            "muted_rgba": config.hex_to_rgba(muted_color, fg_alpha),
            "error_rgba": config.hex_to_rgba(error_color, fg_alpha),
        }

        try:
            rendered_qss = load_component_style("card_item.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error("Failed to load card_item.qss template; returned empty.")
        except Exception as e:
            logger.error(
                "Error applying card list item stylesheet",
                extra={"error_type": type(e).__name__, "details": str(e)},
            )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon_label.setObjectName("CardIconLabel")
        icon_label.setFixedSize(28, 28)
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
                28,
                28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            transparent_pixmap = QPixmap(28, 28)
            transparent_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(transparent_pixmap)
            painter.setOpacity(fg_alpha)
            x_offset = (28 - src_pixmap.width()) // 2
            y_offset = (28 - src_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, src_pixmap)
            painter.end()
            icon_label.setPixmap(transparent_pixmap)
        else:
            icon_label.setText("🔔")

        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Text details
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(data.get("app_name", "Unknown App"))
        title_label.setObjectName("CardTitleLabel")
        title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        try:
            ts = datetime.fromisoformat(data["timestamp"])
            time_str = ts.strftime("%I:%M %p")
        except Exception:
            time_str = ""

        time_label = QLabel(time_str)
        time_label.setObjectName("CardTimeLabel")
        time_label.setFont(QFont("Segoe UI", 8))

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)

        msg_label = QLabel(data.get("message", ""))
        msg_label.setObjectName("CardMsgLabel")
        msg_label.setFont(QFont("Segoe UI", 9))
        msg_label.setWordWrap(True)

        text_layout.addLayout(header_layout)
        text_layout.addWidget(msg_label)

        layout.addLayout(text_layout, 1)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setObjectName("CardDeleteBtn")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self._on_delete_clicked())
        layout.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignTop)

    def _on_delete_clicked(self):
        logger.debug(f"Delete requested for card item ID: {self.item_id}")
        self.delete_requested.emit(self.item_id)
