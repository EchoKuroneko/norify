import asyncio
from typing import Set
from PyQt6.QtCore import QObject, pyqtSignal

from winrt.windows.ui.notifications.management import (
    UserNotificationListener,
    UserNotificationListenerAccessStatus,
)
from winrt.windows.ui.notifications import NotificationKinds

from core.icon_manager import IconManager
from core.logger import logger


class NotificationSignals(QObject):
    """Bridge signals between WinRT background threads and PyQt main thread."""

    received = pyqtSignal(str, str, str)  # app_name, message, icon_path


class WinRTListener:
    """Listens for OS-level toasts via Windows Runtime APIs."""

    def __init__(self, signals: NotificationSignals):
        self.signals = signals
        self.seen_ids: Set[int] = set()

    async def start(self) -> None:
        try:
            listener = UserNotificationListener.current
            access = await listener.request_access_async()

            if access != UserNotificationListenerAccessStatus.ALLOWED:
                logger.error("WinRT Notification access DENIED in Windows Settings")
                return

            logger.info("WinRT Listener initialized and listening for notifications.")

            while True:
                try:
                    notifications = await listener.get_notifications_async(
                        NotificationKinds.TOAST
                    )
                    for n in notifications:
                        if n.id in self.seen_ids:
                            continue

                        self.seen_ids.add(n.id)
                        app_name = n.app_info.display_info.display_name or "System"

                        # Parse message body elements
                        msg_parts = []
                        if n.notification and n.notification.visual:
                            for binding in n.notification.visual.bindings:
                                for text in binding.get_text_elements():
                                    if text.text:
                                        msg_parts.append(text.text)

                        full_message = (
                            "\n".join(msg_parts) if msg_parts else "New Notification"
                        )

                        # Fetch and cache app icon asynchronously
                        icon_path = None
                        try:
                            icon_path = await IconManager.extract_and_cache(
                                n.app_info, app_name
                            )
                        except Exception as ie:
                            logger.error(
                                "Failed to extract icon for notification",
                                extra={
                                    "app_name": app_name,
                                    "error_type": type(ie).__name__,
                                },
                            )

                        # Emit signal without logging message content (Privacy-first)
                        logger.info(
                            "Notification received and processed",
                            extra={"app_name": app_name, "notification_id": n.id},
                        )
                        self.signals.received.emit(
                            app_name, full_message, icon_path or ""
                        )

                except Exception as loop_err:
                    logger.error(
                        "Error in WinRT notification processing loop",
                        extra={"error_type": type(loop_err).__name__},
                    )

                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(
                "Fatal error starting WinRTListener",
                extra={"error_type": type(e).__name__},
            )
