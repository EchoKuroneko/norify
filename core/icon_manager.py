import os
import winreg
from pathlib import Path
from typing import Optional

import psutil
from PyQt6.QtCore import QFileInfo
from PyQt6.QtWidgets import QFileIconProvider
from winrt.windows.storage.streams import DataReader

from config import CACHE_DIR
from core.logger import logger


class IconManager:
    """Handles extracting app icon streams from WinRT and caching them locally."""

    @staticmethod
    def get_icon_from_exe(exe_path: str):
        """Extracts native QIcon directly from an executable file path."""
        if exe_path and os.path.exists(exe_path):
            provider = QFileIconProvider()
            icon = provider.icon(QFileInfo(exe_path))
            if not icon.isNull():
                logger.debug(
                    "Successfully extracted QIcon from EXE",
                    extra={"exe_path": exe_path},
                )
                return icon

        logger.warning(
            "Failed to get valid QIcon from path", extra={"exe_path": exe_path}
        )
        return None

    @staticmethod
    def _find_exe_by_app_id(app_id: str) -> Optional[str]:
        """Dynamically resolves ANY Windows AUMID or App Name to its .exe path."""
        if not app_id:
            return None

        logger.debug("Searching EXE for Raw App ID / Name", extra={"app_id": app_id})

        # 1. Direct EXE Path Check
        if os.path.exists(app_id) and app_id.endswith(".exe"):
            logger.info("App ID is direct executable path", extra={"exe_path": app_id})
            return app_id

        # 2. Extract clean keyword (e.g., 'com.squirrel.Discord.Discord' -> 'discord')
        parts = [
            p.lower()
            for p in app_id.replace("!", ".").split(".")
            if p.lower() not in ("com", "squirrel", "desktop")
        ]
        keyword = parts[-1] if parts else app_id.lower()
        logger.debug(
            "Extracted search keyword from App ID",
            extra={"keyword": keyword, "app_id": app_id},
        )

        # 3. HKLM AppUserModelId
        try:
            reg_path = rf"SOFTWARE\Classes\AppUserModelId\{app_id}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                icon_res, _ = winreg.QueryValueEx(key, "IconUri")
                if icon_res and os.path.exists(icon_res):
                    logger.info(
                        "Resolved via AppUserModelId Registry",
                        extra={"icon_uri": icon_res},
                    )
                    return icon_res
        except OSError:
            pass

        # 4. HKLM App Paths (Try using keyword)
        try:
            reg_path = (
                rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{keyword}.exe"
            )
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                exe_path, _ = winreg.QueryValueEx(key, "")
                if exe_path and os.path.exists(exe_path):
                    logger.info(
                        "Resolved via App Paths Registry",
                        extra={"exe_path": exe_path},
                    )
                    return exe_path
        except OSError:
            pass

        # 5. HKCU Uninstall Entries (Per-user Electron / Squirrel Apps)
        try:
            reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    if keyword in subkey_name.lower():
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                install_loc, _ = winreg.QueryValueEx(
                                    subkey, "InstallLocation"
                                )
                                if install_loc and os.path.exists(install_loc):
                                    install_path = Path(install_loc)
                                    matches = list(install_path.rglob(f"{keyword}.exe"))

                                    valid_exes = [
                                        str(p)
                                        for p in matches
                                        if not any(
                                            x in p.name.lower()
                                            for x in (
                                                "update",
                                                "unins",
                                                "setup",
                                            )
                                        )
                                    ]

                                    if valid_exes:
                                        resolved = sorted(valid_exes)[-1]
                                        logger.info(
                                            "Resolved via HKCU Uninstall registry",
                                            extra={"exe_path": resolved},
                                        )
                                        return resolved
                            except OSError:
                                continue
        except OSError:
            pass

        # 6. Running Process Lookup
        try:
            for proc in psutil.process_iter(["name", "exe"]):
                p_name = proc.info.get("name") or ""
                if p_name.lower() == f"{keyword}.exe":
                    exe_path = proc.info.get("exe")
                    if exe_path and os.path.exists(exe_path):
                        logger.info(
                            "Resolved via Running Process lookup",
                            extra={"process_name": p_name, "exe_path": exe_path},
                        )
                        return exe_path
        except Exception as e:
            logger.debug(
                "Process search check failed",
                extra={"error_type": type(e).__name__},
            )

        logger.warning(
            "Could not resolve executable path for App ID",
            extra={"app_id": app_id},
        )
        return None

    @classmethod
    async def extract_and_cache(cls, app_info, app_name: str) -> Optional[str]:
        safe_name = (
            "".join(c for c in app_name if c.isalnum() or c in (" ", "_")).strip()
            or "unknown_app"
        )
        icon_path = CACHE_DIR / f"{safe_name}.png"

        logger.debug(
            "Requesting icon for application",
            extra={"app_name": app_name, "icon_path": str(icon_path)},
        )

        # 1. Return cached icon if present
        if icon_path.exists():
            logger.debug(
                "Icon loaded from local cache",
                extra={"icon_path": str(icon_path)},
            )
            return str(icon_path)

        # 2. Try WinRT Stream
        try:
            display_info = app_info.display_info
            logo_ref = None
            try:
                logo_ref = display_info.get_logo()
            except (TypeError, ValueError):
                from winrt.windows.foundation import Size

                logo_ref = display_info.get_logo(Size(32.0, 32.0))

            if logo_ref:
                stream = await logo_ref.open_read_async()
                if stream and stream.size > 0:
                    reader = DataReader(stream)
                    await reader.load_async(stream.size)
                    buffer = bytearray(stream.size)
                    reader.read_bytes(buffer)

                    with open(icon_path, "wb") as f:
                        f.write(buffer)

                    logger.info(
                        "Successfully extracted icon via WinRT Stream",
                        extra={"icon_path": str(icon_path)},
                    )
                    return str(icon_path)
                else:
                    logger.warning(
                        "WinRT logo stream was empty",
                        extra={"app_name": app_name},
                    )
        except Exception as e:
            logger.debug(
                "WinRT stream extraction failed/skipped",
                extra={"app_name": app_name, "error_type": type(e).__name__},
            )

        # 3. Fallback to Executable Search
        try:
            app_id = getattr(app_info, "app_user_model_id", "") or app_name
            logger.debug(
                "Attempting EXE fallback with App ID",
                extra={"app_id": app_id},
            )
            exe_path = cls._find_exe_by_app_id(app_id)

            if exe_path:
                qicon = cls.get_icon_from_exe(exe_path)
                if qicon:
                    pixmap = qicon.pixmap(32, 32)
                    if not pixmap.isNull():
                        pixmap.save(str(icon_path), "PNG")
                        logger.info(
                            "Saved EXE extracted icon to PNG cache",
                            extra={"icon_path": str(icon_path)},
                        )
                        return str(icon_path)
                    else:
                        logger.warning(
                            "QIcon pixmap was null for path",
                            extra={"exe_path": exe_path},
                        )
        except Exception as e:
            logger.error(
                "EXE fallback failed",
                extra={"app_name": app_name, "error_type": type(e).__name__},
            )

        logger.error(
            "All icon extraction attempts failed",
            extra={"app_name": app_name},
        )
        return None
