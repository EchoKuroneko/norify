from PyQt6.QtCore import QThread, pyqtSignal
from pynput import keyboard

from core.logger import logger


class HotkeyListenerThread(QThread):
    """Global system hotkey listener thread."""

    triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None

    def run(self) -> None:
        logger.info("Initializing global hotkey listener thread")
        try:
            # Map standard global hotkey shortcut
            hotkeys = {"<ctrl>+<alt>+h": self._on_hotkey_triggered}

            with keyboard.GlobalHotKeys(hotkeys) as self._listener:
                self._listener.join()
        except Exception as e:
            logger.error(
                "Error running HotkeyListenerThread loop",
                extra={"error_type": type(e).__name__},
            )

    def _on_hotkey_triggered(self) -> None:
        logger.info("Global hotkey combo triggered")
        self.triggered.emit()

    def stop(self) -> None:
        """Safely stops the listener thread on app shutdown."""
        try:
            if self._listener:
                self._listener.stop()
            self.quit()
            self.wait()
            logger.info("HotkeyListenerThread stopped successfully")
        except Exception as e:
            logger.error(
                "Error during HotkeyListenerThread shutdown",
                extra={"error_type": type(e).__name__},
            )
