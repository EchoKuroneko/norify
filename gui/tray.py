from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from core.logger import logger
from config import APP_NAME, ICON_PATH
from gui.action_center import ActionCenterWindow
from gui.settings import SettingsWindow


class SystemTrayManager:
    """Manages Taskbar Tray Icon & Right-Click Context Menu."""

    def __init__(self, app, toast_manager, settings_window, action_center):
        self.app = app
        self.toast_manager = toast_manager
        self.settings_window = settings_window
        self.action_center = action_center

        # Create System Tray Icon
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(str(ICON_PATH)))
        self.tray.setToolTip(APP_NAME)

        self._build_menu()

        self.toast_manager.dnd_changed.connect(self._on_dnd_state_changed)
        self.tray.show()

    def _build_menu(self):
        """Create Right-Click Context Menu."""
        self.menu = QMenu()

        self.dnd_action = self.menu.addAction("Do Not Disturb")
        self.dnd_action.setCheckable(True)
        self.dnd_action.setChecked(self.toast_manager.dnd_enabled)
        self.dnd_action.toggled.connect(self._toggle_dnd)

        settings_action = self.menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)

        action_center_btn = self.menu.addAction("Action Center")
        action_center_btn.triggered.connect(self.open_action_center)

        self.menu.addSeparator()

        quit_action = self.menu.addAction("Exit")
        quit_action.triggered.connect(self._on_quit)

        self.tray.setContextMenu(self.menu)

    def _on_quit(self):
        """Clean up tray icon and request Qt application shutdown."""
        logger.info("Application shutdown initiated from system tray")
        self.tray.hide()
        self.app.quit()

    def _toggle_dnd(self, checked: bool):
        self.toast_manager.set_dnd(checked)

    def _on_dnd_state_changed(self, enabled: bool):
        """Called whenever DND changes from ANY source (Tray, Action Center, etc)."""
        self.dnd_action.blockSignals(True)
        self.dnd_action.setChecked(enabled)
        self.dnd_action.blockSignals(False)

        status = "enabled" if enabled else "disabled"
        logger.debug("DND state sync updated in tray", extra={"dnd_enabled": enabled})

        self.toast_manager._create_and_show_toast(
            app_name=APP_NAME,
            message=f"Do Not Disturb is now {status}.",
            icon_path=None,
        )

    def open_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
        self.settings_window.test_notification_requested.connect(
            self.trigger_test_toast
        )
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def open_action_center(self):
        if not self.action_center:
            self.action_center = ActionCenterWindow(
                self.toast_manager, self.settings_window, self.toast_manager.db
            )

        # Refresh action center data if a refresh method exists
        if hasattr(self.action_center, "refresh_data"):
            self.action_center.refresh_data()

        self.action_center.show()
        self.action_center.raise_()
        self.action_center.activateWindow()

    def trigger_test_toast(self):
        self.toast_manager.spawn_toast(
            app_name="Preview Toast",
            message="Sample Notification",
            icon_path=str(ICON_PATH),
        )
