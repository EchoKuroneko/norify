import os
from typing import Optional

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import (
    QBitmap,
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPixmap,
    QRegion,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import TOAST_WIDTH, config
from core.logger import logger
from gui.animations import ToastAnimationHelper
from gui.styles.style_loader import load_component_style


class ToastWidget(QWidget):
    """Modern, frameless custom overlay toast window."""

    MIN_WIDTH = 260
    MAX_WIDTH = TOAST_WIDTH

    def __init__(
        self,
        app_name: str,
        message: str,
        icon_path: Optional[str] = None,
        on_close_callback=None,
        parent=None,
    ):
        super().__init__(parent)
        self.app_name = app_name
        self.message = message
        self.on_close_callback = on_close_callback

        self.total_time_ms = config.data.get("toast_duration_ms", 5000)
        self.remaining_time_ms = self.total_time_ms
        self.timer_interval = 30

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)

        self.container = QWidget(self)
        self.container.setObjectName("Container")

        bg_alpha = config.data.get("bg_opacity", 0.85)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, int(110 * bg_alpha)))
        shadow.setOffset(0, 3)
        self.container.setGraphicsEffect(shadow)
        main_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 4)
        container_layout.setSpacing(4)

        content_widget = QWidget()
        card_layout = QHBoxLayout(content_widget)
        card_layout.setContentsMargins(10, 8, 10, 6)
        card_layout.setSpacing(10)

        # 1. App Icon
        fg_alpha = config.data.get("fg_opacity", 1.0)
        if icon_path and os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setFixedSize(16, 16)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            raw_pixmap = QPixmap(icon_path)

            if not raw_pixmap.isNull():
                image = raw_pixmap.toImage()
                alpha_mask = image.createAlphaMask()
                region = QRegion(QBitmap.fromImage(alpha_mask))
                rect = region.boundingRect()
                if rect.isValid() and not rect.isEmpty():
                    raw_pixmap = raw_pixmap.copy(rect)

            src_pixmap = raw_pixmap.scaled(
                16,
                16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            transparent_pixmap = QPixmap(16, 16)
            transparent_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(transparent_pixmap)
            painter.setOpacity(fg_alpha)
            x_offset = (16 - src_pixmap.width()) // 2
            y_offset = (16 - src_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, src_pixmap)
            painter.end()

            icon_label.setPixmap(transparent_pixmap)
            card_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # 2. Text Column
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_label = QLabel(app_name)
        title_label.setObjectName("TitleLabel")
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        title_label.setFont(title_font)

        self.msg_label = QLabel()
        self.msg_label.setObjectName("MessageLabel")
        msg_font = QFont("Segoe UI", 9)
        self.msg_label.setFont(msg_font)
        self.msg_label.setWordWrap(True)
        self.msg_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        max_chars = 65
        if len(message) > max_chars:
            display_text = message[: max_chars - 3].rstrip() + "..."
        else:
            display_text = message
        self.msg_label.setText(display_text)

        font_metrics = QFontMetrics(msg_font)
        self.msg_label.setMaximumHeight(font_metrics.lineSpacing() * 2)

        text_layout.addWidget(title_label)
        text_layout.addWidget(self.msg_label)
        card_layout.addLayout(text_layout, 1)

        # 3. Close Button
        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_toast)
        card_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        container_layout.addWidget(content_widget)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("ToastProgressBar")
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, self.total_time_ms)
        self.progress_bar.setValue(self.total_time_ms)
        container_layout.addWidget(self.progress_bar)

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        self._apply_stylesheet()
        self.adjustSize()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_progress)
        self.update_timer.start(self.timer_interval)

        logger.debug(
            "ToastWidget initialized",
            extra={
                "app_name": self.app_name,
                "duration_ms": self.total_time_ms,
            },
        )

    def _apply_stylesheet(self):
        theme = config.current_theme
        bg_alpha = config.data.get("bg_opacity", 0.85)
        fg_alpha = config.data.get("fg_opacity", 1.0)

        style_vars = {
            "bg_rgba": config.hex_to_rgba(theme.get("bg_color", "#202020"), bg_alpha),
            "border_rgba": config.hex_to_rgba(
                theme.get("border_color", "#404040"), bg_alpha
            ),
            "border_radius": str(theme.get("border_radius", "6px")),
            "title_rgba": config.hex_to_rgba(
                theme.get("title_color", "#FFFFFF"), fg_alpha
            ),
            "body_rgba": config.hex_to_rgba(
                theme.get("body_color", "#CCCCCC"), fg_alpha
            ),
            "close_rgba": config.hex_to_rgba(
                theme.get("close_btn_color", "#AAAAAA"), fg_alpha
            ),
            "close_hover_rgba": config.hex_to_rgba(
                theme.get("close_btn_hover", "#FFFFFF"), fg_alpha
            ),
            "bar_bg_rgba": config.hex_to_rgba(
                theme.get("progress_bar_bg", "#333333"), bg_alpha
            ),
            "bar_fill_rgba": config.hex_to_rgba(
                theme.get("progress_bar_fill", "#007ACC"), fg_alpha
            ),
        }

        try:
            rendered_qss = load_component_style("toast.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error(
                    "Failed to apply toast stylesheet; template returned empty."
                )
        except Exception as e:
            logger.error(
                "Error rendering ToastWidget stylesheet",
                extra={
                    "error_type": type(e).__name__,
                    "details": str(e),
                },
            )

    def enterEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
            logger.debug(
                "Toast auto-dismiss paused on hover",
                extra={"app_name": self.app_name},
            )
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.update_timer.isActive() and self.remaining_time_ms > 0:
            self.update_timer.start(self.timer_interval)
            logger.debug(
                "Toast auto-dismiss resumed on leave",
                extra={"app_name": self.app_name},
            )
        super().leaveEvent(event)

    def _update_progress(self):
        self.remaining_time_ms -= self.timer_interval
        if self.remaining_time_ms <= 0:
            self.progress_bar.setValue(0)
            self.close_toast()
        else:
            self.progress_bar.setValue(self.remaining_time_ms)

    def show_animated(
        self,
        target_pos: QPoint,
        is_right_aligned: bool = True,
        screen_padding: int = 15,
    ):
        self.adjustSize()
        actual_pos = QPoint(target_pos)

        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            if is_right_aligned:
                right_x = screen_geo.right() - self.width() - screen_padding
                actual_pos.setX(right_x)
            else:
                left_x = screen_geo.left() + screen_padding
                actual_pos.setX(left_x)

        logger.debug(
            "Showing animated toast notification",
            extra={
                "app_name": self.app_name,
                "is_right_aligned": is_right_aligned,
            },
        )

        self.show()
        ToastAnimationHelper.slide_in(self, actual_pos)

    def get_calculated_height(self) -> int:
        self.ensurePolished()
        self.container.adjustSize()
        self.adjustSize()
        return self.height()

    def close_toast(self):
        self.update_timer.stop()
        logger.debug("Closing toast widget", extra={"app_name": self.app_name})
        if self.on_close_callback:
            self.on_close_callback(self)
        self.close()
