from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import config
from core.logger import logger
from db.history_db import HistoryDatabase
from gui.styles.style_loader import load_component_style
from gui.views.card_view import CardView
from gui.views.grouped_view import GroupedView
from gui.settings import SettingsWindow


class ActionCenterBackdrop(QWidget):
    """Full-screen transparent overlay to capture clicks outside the Action Center."""

    def __init__(self, action_center: "ActionCenterWindow"):
        super().__init__()
        self.action_center = action_center

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setCursor(Qt.CursorShape.ArrowCursor)
        # Keeps hit-testing active while remaining invisible to the user
        self.setWindowOpacity(0.01)

    def mousePressEvent(self, event: QMouseEvent):
        global_pos = event.globalPosition().toPoint()
        logger.info(
            f"Backdrop clicked at screen pos ({global_pos.x()}, {global_pos.y()}) -> Hiding Action Center."
        )
        self.action_center.hide()
        super().mousePressEvent(event)


class ActionCenterWindow(QWidget):
    """Main Action Center flyout with switchable views, sorting controls, and click logging."""

    def __init__(
        self,
        toast_manager,
        settings_window: SettingsWindow,
        db: HistoryDatabase,
        parent=None,
    ):
        super().__init__(parent)
        self.toast_manager = toast_manager
        self.settings_window = settings_window
        self.db = db
        self.current_view_name = "cards"  # "cards" or "grouped"

        # Create the full-screen click-catcher overlay
        self.backdrop = ActionCenterBackdrop(self)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        # Outer layout for the transparent window wrapper
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Inner container frame matching SettingsCard pattern to handle background alpha cleanly
        self.container = QFrame(self)
        self.container.setObjectName("ActionCenterCard")

        self._init_ui()
        self._init_modal_overlay()

        self.toast_manager.dnd_changed.connect(self._on_dnd_state_changed)

        self._theme_dirty = True
        if hasattr(config, "theme_changed"):
            config.theme_changed.connect(self._mark_theme_dirty)

        self._position_panel()

    def _init_ui(self):
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)

        # --- TOP BAR ---
        top_bar = QHBoxLayout()
        title = QLabel("Action Center")
        title.setObjectName("ActionCenterTitle")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        self.dnd_btn = QPushButton("🌙 DND")
        self.dnd_btn.setObjectName("DndBtn")
        self.dnd_btn.setCheckable(True)
        self.dnd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dnd_btn.setChecked(self.toast_manager.dnd_enabled)
        self.dnd_btn.toggled.connect(self._on_dnd_toggled)

        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("SettingsBtn")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._open_settings)

        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.setObjectName("ClearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_all_history)

        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(self.dnd_btn)
        top_bar.addWidget(self.settings_btn)
        top_bar.addWidget(self.clear_btn)

        container_layout.addLayout(top_bar)

        # --- SEARCH BAR ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search history...")
        self.search_input.setObjectName("SearchInput")
        self.search_input.textChanged.connect(self._on_search_changed)
        container_layout.addWidget(self.search_input)

        # --- CONTROLS BAR (Sort & View) ---
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        # Sort Control
        sort_label = QLabel("Sort by:")
        sort_label.setFont(QFont("Segoe UI", 9))
        sort_label.setObjectName("SortLabel")
        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("SortCombo")
        self.sort_combo.addItems(["Date", "App", "Date and App"])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)

        controls_layout.addWidget(sort_label)
        controls_layout.addWidget(self.sort_combo)

        controls_layout.addSpacing(10)

        # View Control Dropdown
        view_label = QLabel("View:")
        view_label.setFont(QFont("Segoe UI", 9))
        view_label.setObjectName("ViewLabel")
        self.view_combo = QComboBox()
        self.view_combo.setObjectName("ViewCombo")
        self.view_combo.addItems(["Cards", "Grouped"])
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)

        controls_layout.addWidget(view_label)
        controls_layout.addWidget(self.view_combo)

        controls_layout.addStretch()
        container_layout.addLayout(controls_layout)

        # --- STACKED VIEWS ---
        self.stacked = QStackedWidget()
        self.card_view = CardView(self.db)
        self.grouped_view = GroupedView(self.db)
        self.stacked.addWidget(self.card_view)  # index 0
        self.stacked.addWidget(self.grouped_view)  # index 1

        container_layout.addWidget(self.stacked, 1)

        # Add the container frame to the outer window layout
        self.main_layout.addWidget(self.container)

    def _init_modal_overlay(self):
        """Modal backdrop for confirmation dialogs."""
        self.modal_backdrop = QWidget(self)
        self.modal_backdrop.setObjectName("ModalBackdrop")
        self.modal_backdrop.hide()

        backdrop_layout = QVBoxLayout(self.modal_backdrop)
        backdrop_layout.setContentsMargins(0, 0, 0, 0)
        backdrop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.confirm_overlay = QFrame(self.modal_backdrop)
        self.confirm_overlay.setObjectName("ConfirmOverlay")
        self.confirm_overlay.setFixedWidth(360)

        overlay_layout = QVBoxLayout(self.confirm_overlay)
        overlay_layout.setContentsMargins(18, 16, 18, 16)
        overlay_layout.setSpacing(12)

        overlay_title = QLabel("Clear All History?")
        overlay_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        overlay_title.setObjectName("ConfirmTitle")

        overlay_msg = QLabel("Are you sure? This action cannot be undone.")
        overlay_msg.setFont(QFont("Segoe UI", 9))
        overlay_msg.setObjectName("ConfirmMsg")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.confirm_yes_btn = QPushButton("Clear All")
        self.confirm_yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_yes_btn.setObjectName("ConfirmYesBtn")
        self.confirm_yes_btn.clicked.connect(self._on_confirm_clear_yes)

        self.confirm_no_btn = QPushButton("Cancel")
        self.confirm_no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_no_btn.setObjectName("ConfirmNoBtn")
        self.confirm_no_btn.clicked.connect(self._on_confirm_clear_no)

        btn_row.addStretch()
        btn_row.addWidget(self.confirm_no_btn)
        btn_row.addWidget(self.confirm_yes_btn)

        overlay_layout.addWidget(overlay_title)
        overlay_layout.addWidget(overlay_msg)
        overlay_layout.addLayout(btn_row)

        backdrop_layout.addWidget(self.confirm_overlay)

    # ------------------- Event & Click Logging -------------------
    def mousePressEvent(self, event: QMouseEvent):
        clicked_widget = self.childAt(event.position().toPoint())
        widget_info = (
            f"{clicked_widget.__class__.__name__}"
            f" (objectName: '{clicked_widget.objectName()}')"
            if clicked_widget
            else "ActionCenterWindow background"
        )

        logger.debug(
            "Mouse Press on panel",
            extra={
                "button": event.button().name,
                "x": event.position().x(),
                "y": event.position().y(),
                "target": widget_info,
            },
        )
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.modal_backdrop.setGeometry(self.rect())

    # ------------------- View Switching -------------------
    def _on_view_changed(self, index: int):
        self.stacked.setCurrentIndex(index)
        self.current_view_name = "cards" if index == 0 else "Grouped"
        logger.info(
            "View mode changed",
            extra={"index": index, "view": self.current_view_name},
        )
        self._refresh_current_view()

    # ------------------- Search / Sort -------------------
    def _on_search_changed(self, text: str):
        logger.debug(f"Search query updated: '{text}'")
        self._refresh_current_view()

    def _on_sort_changed(self, index: int):
        logger.info(f"Sort mode changed: {self.sort_combo.currentText()}")
        self._refresh_current_view()

    def _refresh_current_view(self):
        view = self.stacked.currentWidget()
        sort_mode = self.sort_combo.currentText()
        search_text = self.search_input.text().strip()
        if hasattr(view, "refresh_data"):
            view.refresh_data(sort_mode=sort_mode, search_query=search_text)

    # ------------------- DND -------------------
    def _on_dnd_toggled(self, checked: bool):
        logger.info(f"DND toggled -> {checked}")
        self.toast_manager.set_dnd(checked)

    def _on_dnd_state_changed(self, enabled: bool):
        self.dnd_btn.blockSignals(True)
        self.dnd_btn.setChecked(enabled)
        self.dnd_btn.blockSignals(False)

    # ------------------- Clear All -------------------
    def _clear_all_history(self):
        current_view = self.stacked.currentWidget()
        items = getattr(current_view, "filtered_notifications", []) or getattr(
            current_view, "cached_notifications", []
        )

        if not items:
            logger.info("Clear All triggered, but no items were present to clear.")
            return

        logger.info(f"Displaying Clear All modal confirmation for {len(items)} items.")
        self.modal_backdrop.setGeometry(self.rect())
        self.modal_backdrop.show()
        self.modal_backdrop.raise_()

    def _on_confirm_clear_yes(self):
        current_view = self.stacked.currentWidget()
        items = getattr(current_view, "filtered_notifications", []) or getattr(
            current_view, "cached_notifications", []
        )

        if items:
            ids_to_delete = [item["id"] for item in items if "id" in item]
            logger.info(f"User confirmed Clear All. Deleting IDs: {ids_to_delete}")
            self.db.delete_notifications_by_ids(ids_to_delete)

        self.modal_backdrop.hide()
        self._refresh_current_view()

    def _on_confirm_clear_no(self):
        logger.info("User cancelled Clear All action.")
        self.modal_backdrop.hide()

    # ------------------- Settings -------------------
    def _open_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    # ------------------- Theme -------------------
    def reload_theme(self):
        theme = config.current_theme
        # Settings & Action Center background opacity (enforcing minimum 85% opacity floor)
        bg_alpha = max(0.85, float(config.data.get("ui_bg_opacity", 0.95)))
        ui_fg_alpha = 1.0

        style_vars = {
            "bg_rgba": config.hex_to_rgba(theme.get("bg_color", "#1e1e2e"), bg_alpha),
            "border_rgba": config.hex_to_rgba(
                theme.get("border_color", "#45475a"), bg_alpha
            ),
            "border_radius": str(theme.get("border_radius", "8px")),
            "title_rgba": config.hex_to_rgba(
                theme.get("title_color", "#cdd6f4"), ui_fg_alpha
            ),
            "body_rgba": config.hex_to_rgba(
                theme.get("body_color", "#cdd6f4"), ui_fg_alpha
            ),
            "accent_rgba": config.hex_to_rgba(
                theme.get("progress_bar_fill", "#89b4fa"), ui_fg_alpha
            ),
            "search_bg": config.hex_to_rgba(theme.get("bg_color", "#1e1e2e"), bg_alpha),
        }

        try:
            rendered_qss = load_component_style("action_center.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error(
                    "Failed to apply action center stylesheet; template returned empty."
                )
        except Exception as e:
            logger.error(
                "Error applying action center stylesheet",
                extra={
                    "error_type": type(e).__name__,
                    "details": str(e),
                },
            )
        self.card_view.reload_theme()
        self.grouped_view.reload_theme()
        self._refresh_current_view()

    def _mark_theme_dirty(self):
        self._theme_dirty = True

    # ------------------- Window positioning -------------------
    def showEvent(self, event):
        super().showEvent(event)

        if self._theme_dirty:
            self.reload_theme()
            self._theme_dirty = False

        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            self.backdrop.setGeometry(screen.geometry())

        self.backdrop.show()
        self._position_panel()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()
        if (
            len(self.search_input.text()) == 1
            and not self.search_input.hasSelectedText()
        ):
            self.search_input.clear()
        logger.info("Action Center & full-screen backdrop displayed.")

    def hideEvent(self, event):
        self.backdrop.hide()
        self.modal_backdrop.hide()
        logger.info("Action Center & backdrop hidden.")
        super().hideEvent(event)

    def _position_panel(self):
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return

        geo = screen.availableGeometry()
        panel_width = min(420, geo.width())
        ac_position = config.data.get("action_center_position", "right")

        if ac_position == "left":
            x_pos = geo.x()
        else:
            x_pos = geo.x() + geo.width() - panel_width

        y_pos = geo.y()
        self.setGeometry(int(x_pos), int(y_pos), int(panel_width), int(geo.height()))

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange:
            if not self.isActiveWindow() and self.isVisible():
                logger.info("Window lost activation state; hiding panel.")
                self.hide()
        super().changeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.modal_backdrop.isVisible():
                logger.info("Escape pressed: closing confirmation overlay.")
                self.modal_backdrop.hide()
            else:
                logger.info("Escape pressed: hiding Action Center.")
                self.hide()
        else:
            super().keyPressEvent(event)
