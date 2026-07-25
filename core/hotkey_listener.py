from PyQt6.QtCore import QThread, pyqtSignal
from pynput import keyboard

from core.logger import logger
from core.shortcuts import APP_SHORTCUTS


class HotkeyListenerThread(QThread):
    """Global system hotkey listener thread."""

    triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None

    @staticmethod
    def _parse_hotkey_to_pynput(key_str: str) -> str:
        """Dynamically converts user-friendly shortcut strings to pynput format."""
        parts = [p.strip().lower() for p in key_str.split("+")]
        formatted = []
        for p in parts:
            if p == "escape" or p == "esc":
                formatted.append("<esc>")
            elif len(p) == 1:
                formatted.append(p)
            else:
                formatted.append(f"<{p}>")
        return "+".join(formatted)

    def run(self) -> None:
        logger.info("Initializing global hotkey listener thread")
        try:
            # Map standard global hotkey shortcut
            hotkeys_map = {}
            for item in APP_SHORTCUTS:
                action_id = item.get("id")
                raw_key = item.get("key", "")
                if not action_id or not raw_key:
                    continue
                pynput_key = self._parse_hotkey_to_pynput(raw_key)
                hotkeys_map[pynput_key] = (
                    lambda aid=action_id: self._on_hotkey_triggered(aid)
                )
                logger.info(
                    f"Registered dynamic hotkey [{action_id}]: {raw_key} -> {pynput_key}"
                )
            if hotkeys_map:
                with keyboard.GlobalHotKeys(hotkeys_map) as self._listener:
                    self._listener.join()
            else:
                logger.warning("No valid global hotkeys found in configuration.")
        except Exception as e:
            logger.error(
                "Error running HotkeyListenerThread loop",
                extra={"error_type": type(e).__name__},
            )

    def _on_hotkey_triggered(self, action_id: str) -> None:
        logger.info("Global hotkey combo triggered")
        self.triggered.emit(action_id)

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
