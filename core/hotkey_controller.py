from core.logger import logger
from gui.action_center import ActionCenterWindow
from gui.settings import SettingsWindow


def handle_global_hotkey(
    action_id: str,
    action_center: ActionCenterWindow,
    settings_window: SettingsWindow,
):
  """Dynamically routes global shortcut actions without hard-coding."""
  logger.info(f"Handling global hotkey action: {action_id}")

  if action_id == "action_center":
    if action_center.isVisible():
      action_center.hide()
    else:
      action_center.show()
      action_center.activateWindow()
  elif action_id == "settings":
    settings_window.show()
    settings_window.raise_()
    settings_window.activateWindow()