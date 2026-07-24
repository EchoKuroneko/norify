from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from config import config
from core.logger import logger
from db.history_db import HistoryDatabase
from gui.toast_widget import ToastWidget


class ToastManager(QObject):
    dnd_changed = pyqtSignal(bool)

    def __init__(self, db: HistoryDatabase, max_visible: int = 4):
        super().__init__()

        self.active_toasts: List[ToastWidget] = []
        self.toast_queue: List[Tuple[str, str, Optional[str]]] = []
        self.dnd_enabled: bool = False
        self.max_visible: int = max_visible
        self.spacing = 10  # Gap between stacked toasts
        self.screen_padding = 15  # Padding from screen edge
        self.db = db

    def _get_toast_position_info(
        self, toast_index: int, target_toast: ToastWidget
    ) -> Tuple[QPoint, bool]:
        """Calculates target position and alignment based on primary screen geometry."""
        try:
            screen = QGuiApplication.primaryScreen()
            screen_geo = (
                screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
            )
        except Exception as e:
            logger.error(
                "Error retrieving screen geometry, falling back to default resolution",
                extra={"error_type": type(e).__name__},
            )
            screen_geo = QRect(0, 0, 1920, 1080)

        position_setting = config.data.get("toast_position", "bottom_right")
        is_right = "right" in position_setting
        is_top = "top" in position_setting

        # 1. Determine X Position
        if is_right:
            base_x = screen_geo.right() - ToastWidget.MAX_WIDTH - self.screen_padding
        else:
            base_x = screen_geo.left() + self.screen_padding

        # 2. Calculate accurate height for text wrapping
        def get_accurate_height(w: ToastWidget) -> int:
            w.setFixedWidth(ToastWidget.MAX_WIDTH)
            w.ensurePolished()
            w.adjustSize()
            return w.sizeHint().height()

        # 3. Calculate accumulated Y height of all toasts below target_index
        accumulated_height = sum(
            get_accurate_height(t) + self.spacing
            for t in self.active_toasts[:toast_index]
        )
        target_height = get_accurate_height(target_toast)

        # 4. Determine Y Position
        if is_top:
            base_y = screen_geo.top() + self.screen_padding + accumulated_height
        else:
            base_y = (
                screen_geo.bottom()
                - self.screen_padding
                - accumulated_height
                - target_height
            )

        return QPoint(base_x, base_y), is_right

    def spawn_toast(self, app_name: str, message: str, icon_path: Optional[str] = None):
        """Processes an incoming notification and enqueues or displays it."""
        self._log_to_history(app_name, message, icon_path)

        if self.dnd_enabled:
            logger.info(
                "DND active; notification suppressed",
                extra={"app_name": app_name},
            )
            return

        if len(self.active_toasts) >= self.max_visible:
            self.toast_queue.append((app_name, message, icon_path))
            logger.info(
                "Toast limit reached; added to queue",
                extra={
                    "app_name": app_name,
                    "queue_length": len(self.toast_queue),
                },
            )
            return

        self._create_and_show_toast(app_name, message, icon_path)

    def _create_and_show_toast(
        self, app_name: str, message: str, icon_path: Optional[str] = None
    ):
        """Instantiates, positions, and animates a new toast widget."""
        try:
            toast = ToastWidget(
                app_name=app_name,
                message=message,
                icon_path=icon_path,
                on_close_callback=self._on_toast_closed,
            )
            self.active_toasts.append(toast)
            toast_index = len(self.active_toasts) - 1

            target_pos, is_right = self._get_toast_position_info(toast_index, toast)
            toast.show_animated(
                target_pos,
                is_right_aligned=is_right,
                screen_padding=self.screen_padding,
            )
        except Exception as e:
            logger.error(
                "Failed to instantiate or display ToastWidget",
                extra={
                    "app_name": app_name,
                    "error_type": type(e).__name__,
                },
            )

    def _reposition_toasts(self):
        """Restacks remaining active toasts smoothly when one closes."""
        for idx, toast in enumerate(self.active_toasts):
            try:
                target_pos, is_right = self._get_toast_position_info(idx, toast)
                toast.show_animated(
                    target_pos,
                    is_right_aligned=is_right,
                    screen_padding=self.screen_padding,
                )
            except Exception as e:
                logger.error(
                    "Failed to reposition toast widget",
                    extra={"toast_index": idx, "error_type": type(e).__name__},
                )

    def _on_toast_closed(self, toast: ToastWidget):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            self._reposition_toasts()

        # Pop next toast from queue if available
        if self.toast_queue and len(self.active_toasts) < self.max_visible:
            next_app, next_msg, next_icon = self.toast_queue.pop(0)
            self._create_and_show_toast(next_app, next_msg, next_icon)

    def _log_to_history(
        self, app_name: str, message: str, icon_path: Optional[str] = None
    ):
        """Saves notification entry to SQLite database."""
        try:
            self.db.add_notification(app_name, message, icon_path)
        except Exception as e:
            logger.error(
                "Failed to log notification entry to history database",
                extra={"app_name": app_name, "error_type": type(e).__name__},
            )

    def set_dnd(self, enabled: bool):
        """Updates DND state and notifies UI components."""
        if self.dnd_enabled != enabled:
            self.dnd_enabled = enabled
            self.dnd_changed.emit(enabled)
            logger.info("Do Not Disturb state updated", extra={"dnd_enabled": enabled})
