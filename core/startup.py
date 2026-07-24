import os
import sys
import winreg

from config import APP_NAME
from core.logger import logger

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APPROVED_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
)

# Windows StartupApproved states
STARTUP_ENABLED = bytes([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
STARTUP_DISABLED = bytes([0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def _get_app_path() -> str:
    """Returns the executable/script path used for startup."""

    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'


def set_auto_start(enabled: bool, app_name: str = APP_NAME) -> bool:
    """
    Enables or disables application startup.

    When disabled, the Run key is retained and only the
    StartupApproved state is changed, matching Task Manager behavior.
    """
    if sys.platform != "win32":
        return False

    app_path = _get_app_path()

    try:
        # Ensure the Run key exists
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_ALL_ACCESS,
        ) as key:
            winreg.SetValueEx(
                key,
                app_name,
                0,
                winreg.REG_SZ,
                app_path,
            )

        # Ensure StartupApproved key exists
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_KEY,
        ) as key:
            state = STARTUP_ENABLED if enabled else STARTUP_DISABLED

            winreg.SetValueEx(
                key,
                app_name,
                0,
                winreg.REG_BINARY,
                state,
            )

        logger.info(
            f"Auto-startup {'enabled' if enabled else 'disabled'} successfully."
        )
        return True

    except Exception as e:
        logger.error(
            "Failed to modify auto-startup registry",
            extra={
                "error_type": type(e).__name__,
                "details": str(e),
            },
        )
        return False


def is_auto_start_enabled(app_name: str = APP_NAME) -> bool:
    """
    Checks whether Windows considers the application enabled at startup.

    Returns:
        True:
            - Run key exists and StartupApproved is enabled.
            - Run key exists and StartupApproved entry does not yet exist.
        False:
            - Run key missing.
            - StartupApproved marks the application as disabled.
    """
    if sys.platform != "win32":
        return False

    try:
        # Application must exist in Run
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, app_name)

    except FileNotFoundError:
        return False

    try:
        # Check Task Manager state
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            data, _ = winreg.QueryValueEx(key, app_name)

            if isinstance(data, bytes):
                return data[0] == 0x02

            return False

    except FileNotFoundError:
        # StartupApproved entry doesn't exist yet.
        # Windows treats this as enabled.
        return True

    except Exception:
        return False


def get_auto_start_status(app_name: str = APP_NAME) -> str:
    """
    Returns:
        - 'enabled'
        - 'disabled'
        - 'not_installed'
    """
    if sys.platform != "win32":
        return "not_installed"

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, app_name)

    except FileNotFoundError:
        return "not_installed"

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            data, _ = winreg.QueryValueEx(key, app_name)

            if data[0] == 0x02:
                return "enabled"

            if data[0] == 0x03:
                return "disabled"

            return f"unknown ({data[0]})"

    except FileNotFoundError:
        return "enabled"
