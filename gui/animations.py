from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
)

from core.logger import logger


class ToastAnimationHelper:
    """Handles slide-in and fade-out visual transition effects."""

    @staticmethod
    def slide_in(widget, target_pos: QPoint, duration: int = 250) -> None:
        """Slides in a widget from a offset position to its target coordinates."""
        # Start offset 30px to the right for slide effect
        start_pos = QPoint(target_pos.x() + 30, target_pos.y())
        widget.move(start_pos)

        logger.debug(
            "Starting toast slide-in animation",
            extra={
                "start_x": start_pos.x(),
                "start_y": start_pos.y(),
                "target_x": target_pos.x(),
                "target_y": target_pos.y(),
                "duration_ms": duration,
            },
        )

        try:
            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(target_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

            # Keep reference to prevent GC cleanup
            widget._slide_anim = anim
        except Exception as e:
            logger.error(
                "Failed to execute slide-in animation",
                extra={"error_type": type(e).__name__},
            )
