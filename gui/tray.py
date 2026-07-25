from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QDialog, QMenu, QSystemTrayIcon
import webbrowser

from core.logger import logger
from config import APP_NAME, APP_VERSION, ICON_DIR, ICON_PATH, config
from gui.action_center import ActionCenterWindow
from gui.settings import SettingsWindow
from gui.update_dialog import UpdateDialog
from core.update import check_for_update


class UpdateWorker(QObject):
    update_available = pyqtSignal(str, str, bool)
    no_update_found = pyqtSignal()
    error_occurred = pyqtSignal()

    def __init__(self, current_version: str, manual: bool = False):
        super().__init__()
        self.current_version = current_version
        self.manual = manual

    def run(self):
        logger.info(
            "UpdateWorker started check",
            extra={"current_version": self.current_version, "manual": self.manual},
        )
        try:
            result = check_for_update(self.current_version)
            if result:
                latest_version, download_url = result
                logger.info(
                    "New version detected by worker",
                    extra={
                        "latest_version": latest_version,
                        "download_url": download_url,
                    },
                )
                self.update_available.emit(latest_version, download_url, self.manual)
            else:
                logger.info("No newer version found on GitHub.")
                if self.manual:
                    self.no_update_found.emit()
        except Exception as e:
            logger.error(
                "Error checking for updates",
                extra={"error_type": type(e).__name__, "details": str(e)},
                exc_info=True,
            )
            if self.manual:
                self.error_occurred.emit()
        finally:
            QThread.currentThread().quit()


class SystemTrayManager:
    """Manages Taskbar Tray Icon & Right-Click Context Menu."""

    def __init__(self, app, toast_manager, settings_window, action_center):
        self.app = app
        self.toast_manager = toast_manager
        self.settings_window = settings_window
        self.action_center = action_center
        self._update_thread = None
        self.has_update = False

        # Create System Tray Icon
        self.tray = QSystemTrayIcon()
        self.set_tray_icon()
        self.tray.setToolTip(APP_NAME)

        self._build_menu()

        self.toast_manager.dnd_changed.connect(self._on_dnd_state_changed)
        self.tray.show()

        logger.debug("Triggering background initial update check...")
        self.check_updates(manual=False)

    def set_tray_icon(self):
        suffix = "_unread" if self.has_update else ""
        icon_path = ICON_DIR / f"app_icon{suffix}.ico"
        self.tray.setIcon(QIcon(str(icon_path)))
        logger.debug(
            "Tray icon updated",
            extra={"has_update": self.has_update, "icon_path": str(icon_path)},
        )

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

        self.update_action = QAction("Check for Updates", self.menu)
        self.update_action.triggered.connect(self._manual_update_check)
        self.menu.addAction(self.update_action)

        self.menu.addSeparator()

        quit_action = self.menu.addAction("Exit")
        quit_action.triggered.connect(self._on_quit)

        self.tray.setContextMenu(self.menu)
        logger.debug("System tray context menu built successfully.")

    def _manual_update_check(self):
        logger.info("Check for Updates menu item clicked.")
        self.check_updates(manual=True)

    def check_updates(self, manual: bool = False):
        logger.info(
            "check_updates called",
            extra={
                "thread_exists": self._update_thread is not None,
            },
        )
        if self._update_thread:
            logger.info(
                "Thread object state",
                extra={
                    "thread_repr": repr(self._update_thread),
                },
            )
        if self._update_thread and self._update_thread.isRunning():
            logger.debug("Update check already in progress. Skipping request.")
            return

        logger.info("Initializing update check thread...", extra={"manual": manual})
        self._update_thread = QThread()
        self.worker = UpdateWorker(APP_VERSION, manual=manual)
        self.worker.moveToThread(self._update_thread)

        self._update_thread.started.connect(self.worker.run)
        self.worker.update_available.connect(self._handle_update_available)

        if manual:
            self.worker.no_update_found.connect(self._handle_no_update)
            self.worker.error_occurred.connect(self._handle_update_error)

        self.worker.update_available.connect(self._update_thread.quit)
        self.worker.update_available.connect(self.worker.deleteLater)
        self.worker.no_update_found.connect(self._update_thread.quit)
        self.worker.no_update_found.connect(self.worker.deleteLater)
        self.worker.error_occurred.connect(self._update_thread.quit)
        self.worker.error_occurred.connect(self.worker.deleteLater)

        self._update_thread.finished.connect(self._cleanup_update_thread)
        self._update_thread.start()

    def _show_themed_message(
        self,
        title: str,
        text: str,
        informative_text: str = "",
        is_question: bool = False,
    ) -> bool:
        """Helper to display custom modal dialog matching SettingsWindow design."""
        dialog = UpdateDialog(
            title=title,
            text=text,
            informative_text=informative_text,
            is_question=is_question,
        )
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _handle_update_available(
        self, latest_version: str, download_url: str, manual: bool
    ):
        logger.info(
            "Handling available update in UI",
            extra={"latest_version": latest_version, "manual": manual},
        )
        self.has_update = True
        self.set_tray_icon()

        if not manual:
            return

        accepted = self._show_themed_message(
            title="Update Available",
            text=f"A new version ({latest_version}) is available!",
            informative_text="Would you like to open the release page to download it?",
            is_question=True,
        )

        if accepted:
            logger.info("User accepted update prompt; opening release URL.")
            webbrowser.open(download_url)
        else:
            logger.info("User declined update prompt.")

    def _handle_no_update(self):
        logger.info("Handling manual check: App is already up to date.")
        self.has_update = False
        self.set_tray_icon()

        self._show_themed_message(
            title="No Updates",
            text="You are already running the latest version.",
            is_question=False,
        )

    def _handle_update_error(self):
        logger.warning("Handling manual check: Update network check failed.")
        self._show_themed_message(
            title="Update Check Failed",
            text="Could not check for updates. Please check your network connection.",
            is_question=False,
        )

    def _cleanup_update_thread(self):
        logger.debug("Update thread cleaned up.")
        if self._update_thread:
            self._update_thread.deleteLater()
        self._update_thread = None
        self.worker = None

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
