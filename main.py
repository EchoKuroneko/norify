import asyncio
import sys
import ctypes
from PyQt6.QtCore import QSharedMemory
from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

from PyQt6.QtGui import QIcon

from core.hotkey_controller import handle_global_hotkey
from core.hotkey_listener import HotkeyListenerThread
from core.listener import NotificationSignals, WinRTListener
from core.logger import logger
from config import APP_NAME, APP_ID, ICON_PATH, DB_FILE
from db.history_db import HistoryDatabase
from gui.action_center import ActionCenterWindow
from gui.settings import SettingsWindow
from gui.toast_manager import ToastManager
from gui.tray import SystemTrayManager
from gui.styles.style_loader import apply_theme
from core.utils import generate_ico_file


def set_windows_app_id():
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


async def main_async(app: QApplication):
    logger.info("Initializing core services and UI components...")

    db = HistoryDatabase(DB_FILE)
    manager = ToastManager(db)
    signals = NotificationSignals()

    settings_window = SettingsWindow()
    settings_window.test_notification.connect(manager.spawn_toast)
    action_center = ActionCenterWindow(manager, settings_window, db=db)
    tray_manager = SystemTrayManager(app, manager, settings_window, action_center)

    # Hotkey listener
    hotkey_thread = HotkeyListenerThread()
    hotkey_thread.triggered.connect(
        lambda action_id: handle_global_hotkey(
            action_id, action_center, settings_window
        )
    )
    hotkey_thread.start()

    # Route signals to UI
    signals.received.connect(
        lambda app_name, msg, icon: manager.spawn_toast(
            app_name, msg, icon if icon else None
        )
    )

    # Notification Listener
    listener = WinRTListener(signals)
    listener_task = asyncio.create_task(listener.start())

    # Create a shutdown event tied to Qt's exit signal
    shutdown_event = asyncio.Event()
    app.aboutToQuit.connect(shutdown_event.set)

    logger.info("Application loop running.")

    # Wait until app.quit() or tray exit is triggered
    await shutdown_event.wait()

    logger.info("Shutdown signal received. Cleaning up background tasks...")

    # Clean up background tasks on shutdown
    hotkey_thread.stop()
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    logger.info("Cleanup complete. Exiting application.")


def main():
    logger.info("Starting application...")

    app = QApplication(sys.argv)
    shared_memory = QSharedMemory(f"Local\\{APP_ID}")
    if shared_memory.attach():
        logger.warning("Another instance of the application is already running.")
        sys.exit(0)

    if shared_memory.isAttached():
        shared_memory.detach()

    if not shared_memory.create(1):
        logger.error("Error: Could not create shared memory segment.")
        sys.exit(1)

    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    generate_ico_file()
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    app.setQuitOnLastWindowClosed(False)

    # 1. Apply global QSS styles from styles/ folder
    apply_theme(app)

    # 2. Bridge Qt Event Loop with Asyncio
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        with loop:
            loop.run_until_complete(main_async(app))
    except (RuntimeError, asyncio.CancelledError) as e:
        logger.warning(
            "Event loop interrupted during exit",
            extra={"error_type": type(e).__name__},
        )
    except Exception as e:
        logger.error(
            "Unhandled exception in main loop",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )


if __name__ == "__main__":
    main()
