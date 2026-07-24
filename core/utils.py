import os
from PyQt6.QtCore import QFileInfo, QPointF, Qt
from PyQt6.QtGui import QIcon, QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QFileIconProvider
from PIL import Image

from core.logger import logger
from config import ICON_DIR


def get_icon_from_exe(exe_path: str) -> QIcon | None:
    """Extracts native QIcon directly from an executable file path."""
    if exe_path and os.path.exists(exe_path):
        try:
            provider = QFileIconProvider()
            icon = provider.icon(QFileInfo(exe_path))
            if not icon.isNull():
                logger.debug(
                    "Successfully extracted QIcon from EXE",
                    extra={"exe_path": exe_path},
                )
                return icon
            logger.warning(
                "Failed to obtain valid QIcon from EXE path",
                extra={"exe_path": exe_path},
            )
        except Exception as e:
            logger.error(
                "Error extracting icon from EXE path",
                extra={"exe_path": exe_path, "error_type": type(e).__name__},
            )
            return None
    else:
        logger.warning(
            "EXE path does not exist or is invalid",
            extra={"exe_path": exe_path},
        )

    return None


def draw_icon(size: int, has_update: bool = False) -> QPixmap:
    """Programmatically generates a unique, crisp vector app icon for Norify."""
    # Create a high-res pixmap for crisp scaling on all displays (e.g., 64x64)
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    scale_factor = size / 64.0
    painter.scale(scale_factor, scale_factor)

    # 1. Draw Rounded App Background Card
    bg_path = QPainterPath()
    bg_path.addRoundedRect(4, 4, 56, 56, 14, 14)

    # Subtle dark gradient background
    bg_gradient = QLinearGradient(4, 4, 60, 60)
    bg_gradient.setColorAt(0.0, QColor("#313244"))  # Surface color
    bg_gradient.setColorAt(1.0, QColor("#1e1e2e"))  # Base background color
    painter.setBrush(bg_gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(bg_path)

    # 2. Draw Stylized Notification Bell
    bell_path = QPainterPath()
    # Bell dome
    bell_path.moveTo(32, 16)
    bell_path.cubicTo(22, 16, 20, 26, 20, 36)
    bell_path.lineTo(44, 36)
    bell_path.cubicTo(44, 26, 42, 16, 32, 16)
    # Bell base rim
    bell_path.addRoundedRect(18, 36, 28, 4, 2, 2)

    # Accent color for the bell (Catppuccin Blue / Theme accent)
    bell_color = QColor("#89b4fa")
    painter.setBrush(bell_color)
    painter.drawPath(bell_path)

    # Bell clapper (the little ball at the bottom)
    painter.drawEllipse(QPointF(32, 43), 3, 3)

    if has_update:
        # 3. Draw Notification Pulse Dot (Top Right)
        # Represents the "live listener / unread indicator"
        glow_color = QColor("#f38ba8")  # Vibrant accent / notification red-pink
        painter.setBrush(glow_color)
        painter.drawEllipse(QPointF(46, 18), 5, 5)

    painter.end()
    return pixmap


def generate_ico_file():
    # Standard Windows icon sizes
    sizes = [16, 32, 64, 128, 256]
    pil_images = []

    for size in sizes:
        png_path = f"{ICON_DIR}/icon_{size}.png"
        if os.path.exists(png_path):
            continue
        qpixmap = draw_icon(size)
        qpixmap.save(png_path, "PNG")
        pil_images.append(Image.open(png_path))

    icon_path = f"{ICON_DIR}/app_icon.ico"
    if not os.path.exists(icon_path):
        # Save all sizes into a single multi-resolution .ico file
        pil_images[0].save(
            icon_path,
            format="ICO",
            sizes=[(img.width, img.height) for img in pil_images],
            append_images=pil_images[1:],
        )

    for img in pil_images:
        img.close()
