from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon, QFont, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from config import ICON_PATH, config
from core.logger import logger
from gui.styles.style_loader import load_component_style


class UpdateDialog(QDialog):
    """Custom themed dialog for update notifications matching app styling."""

    def __init__(
        self,
        title: str,
        text: str,
        informative_text: str = "",
        is_question: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(500)
        self._drag_pos = QPoint()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame(self)
        self.container.setObjectName("MessageContainer")

        self.card_layout = QVBoxLayout(self.container)
        self.card_layout.setContentsMargins(16, 12, 16, 16)
        self.card_layout.setSpacing(14)

        self._setup_title_bar(title)
        self._init_ui(text, informative_text, is_question)

        self.main_layout.addWidget(self.container)

        if ICON_PATH and ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._apply_styles()

    def _setup_title_bar(self, title_text: str):
        self.title_bar_frame = QFrame()
        self.title_bar_frame.setObjectName("TitleBar")
        self.title_bar_frame.setFixedHeight(40)

        title_bar_layout = QHBoxLayout(self.title_bar_frame)
        title_bar_layout.setContentsMargins(4, 4, 4, 0)
        title_bar_layout.setSpacing(6)

        title_label = QLabel(title_text)
        title_label.setObjectName("HeaderTitle")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.clicked.connect(self.reject)

        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.close_btn)

        self.card_layout.insertWidget(0, self.title_bar_frame)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("Divider")
        self.card_layout.addWidget(divider)

    def _init_ui(self, text: str, informative_text: str, is_question: bool):
        if text:
            self.msg_label = QLabel(text)
            self.msg_label.setObjectName("SubHeader")
            self.msg_label.setWordWrap(True)
            self.card_layout.addWidget(self.msg_label)

        if informative_text:
            self.info_label = QLabel(informative_text)
            self.info_label.setObjectName("SubHeader")
            self.info_label.setWordWrap(True)
            self.card_layout.addWidget(self.info_label)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        if is_question:
            self.cancel_btn = QPushButton("No")
            self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_btn.setObjectName("CancelBtn")
            self.cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(self.cancel_btn)

            self.ok_btn = QPushButton("Yes")
            self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.ok_btn.setObjectName("DoneBtn")
            self.ok_btn.clicked.connect(self.accept)
            btn_layout.addWidget(self.ok_btn)
        else:
            self.ok_btn = QPushButton("Ok")
            self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.ok_btn.setObjectName("DoneBtn")
            self.ok_btn.clicked.connect(self.accept)
            btn_layout.addWidget(self.ok_btn)

        self.card_layout.addLayout(btn_layout)

    def _apply_styles(self):
        theme = config.current_theme
        bg_alpha = max(0.85, float(config.data.get("ui_bg_opacity", 0.95)))

        style_vars = {
            "bg_rgba": config.hex_to_rgba(theme.get("bg_color", "#202020"), bg_alpha),
            "border_rgba": config.hex_to_rgba(
                theme.get("border_color", "#404040"), bg_alpha
            ),
            "border_radius": str(theme.get("border_radius", "12px")),
            "title_rgba": config.hex_to_rgba(theme.get("title_color", "#FFFFFF"), 1.0),
            "body_rgba": config.hex_to_rgba(theme.get("body_color", "#CCCCCC"), 1.0),
            "accent_rgba": config.hex_to_rgba(
                theme.get("progress_bar_fill", "#007ACC"), 1.0
            ),
            "close_hover_rgba": config.hex_to_rgba(
                theme.get("close_btn_hover", "#FFFFFF"), 1.0
            ),
        }

        try:
            rendered_qss = load_component_style("message_box.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error(
                    "Failed to apply settings stylesheet; template returned empty."
                )
        except Exception as e:
            logger.error(
                "Error applying settings stylesheet",
                extra={
                    "error_type": type(e).__name__,
                    "details": str(e),
                },
            )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child and (
                child == self.title_bar_frame
                or self.title_bar_frame.isAncestorOf(child)
            ):
                self._drag_pos = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
        ) and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = QPoint()
        super().mouseReleaseEvent(event)
