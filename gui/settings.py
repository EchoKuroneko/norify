from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPalette
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QSlider,
    QStyledItemDelegate,
    QVBoxLayout,
)

from config import THEMES, config, APP_NAME
from core.logger import logger
from core.startup import set_auto_start, is_auto_start_enabled
from gui.styles.style_loader import load_component_style


class SettingsWindow(QDialog):
    """Modern Settings Window matching the toast card aesthetic."""

    settings_changed = pyqtSignal()
    test_notification_requested = pyqtSignal()

    # INITIALIZATION & UI SETUP
    def __init__(self, parent=None):
        super().__init__(parent)
        name = f"Settings - {APP_NAME}"
        self.setWindowTitle(name)
        self.setFixedSize(380, 670)  # Expanded height for extra control
        self.is_pinned = False
        self._drag_pos = QPoint()

        self._update_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame(self)
        self.container.setObjectName("SettingsContainer")

        self.card_layout = QVBoxLayout(self.container)
        self.card_layout.setContentsMargins(16, 12, 16, 16)
        self.card_layout.setSpacing(14)

        self._setup_title_bar()
        self._setup_controls()
        self._setup_action_buttons()

        self.main_layout.addWidget(self.container)

        self.apply_theme_styles()
        self._update_combo_popup_style(self.theme_combo)
        self._update_combo_popup_style(self.pos_combo)
        self._update_combo_popup_style(self.ac_pos_combo)

    def _setup_title_bar(self):
        self.title_bar_frame = QFrame()
        self.title_bar_frame.setObjectName("TitleBar")
        self.title_bar_frame.setFixedHeight(40)

        title_bar_layout = QHBoxLayout(self.title_bar_frame)
        title_bar_layout.setContentsMargins(4, 4, 4, 0)
        title_bar_layout.setSpacing(6)

        title_label = QLabel("Settings")
        title_font = QFont("Segoe UI", 11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName("HeaderTitle")

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(26, 26)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setObjectName("PinBtn")
        self.pin_btn.setToolTip("Toggle Always on Top")
        self.pin_btn.clicked.connect(self.toggle_pin)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.clicked.connect(self.reject)

        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.pin_btn)
        title_bar_layout.addWidget(self.close_btn)

        self.card_layout.insertWidget(0, self.title_bar_frame)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("Divider")
        self.card_layout.addWidget(divider)

    def _setup_controls(self):
        # Theme Selection
        theme_box = QVBoxLayout()
        theme_box.setSpacing(4)
        theme_title = QLabel("Theme")
        theme_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        theme_title.setObjectName("SubHeader")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(
            config.data.get("theme_name", "Catppuccin Macchiato")
        )
        self._configure_combo_popup(self.theme_combo)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)

        theme_box.addWidget(theme_title)
        theme_box.addWidget(self.theme_combo)
        self.card_layout.addLayout(theme_box)

        # Toast Position Selection
        pos_box = QVBoxLayout()
        pos_box.setSpacing(4)
        pos_title = QLabel("Toast Position")
        pos_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        pos_title.setObjectName("SubHeader")

        self.pos_combo = QComboBox()
        self.pos_combo.addItems(
            ["Bottom Right", "Top Right", "Bottom Left", "Top Left"]
        )

        current_pos = config.data.get("toast_position", "bottom_right")
        pos_map = {"bottom_right": 0, "top_right": 1, "bottom_left": 2, "top_left": 3}
        self.pos_combo.setCurrentIndex(pos_map.get(current_pos, 0))

        self._configure_combo_popup(self.pos_combo)
        self.pos_combo.currentIndexChanged.connect(self._on_position_changed)

        pos_box.addWidget(pos_title)
        pos_box.addWidget(self.pos_combo)
        self.card_layout.addLayout(pos_box)

        # Action Center Position
        ac_pos_box = QVBoxLayout()
        ac_pos_box.setSpacing(4)
        ac_pos_title = QLabel("Action Center Position")
        ac_pos_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        ac_pos_title.setObjectName("SubHeader")

        self.ac_pos_combo = QComboBox()
        self.ac_pos_combo.addItems(["Right Side", "Left Side"])
        current_ac_pos = config.data.get("action_center_position", "right")
        self.ac_pos_combo.setCurrentIndex(0 if current_ac_pos == "right" else 1)

        self._configure_combo_popup(self.ac_pos_combo)
        self.ac_pos_combo.currentIndexChanged.connect(
            self._on_action_center_position_changed
        )

        ac_pos_box.addWidget(ac_pos_title)
        ac_pos_box.addWidget(self.ac_pos_combo)
        self.card_layout.addLayout(ac_pos_box)

        # Startup Checkbox
        self.startup_checkbox = QCheckBox("Start application on system startup")
        self.startup_checkbox.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.startup_checkbox.setObjectName("StartupCheckBox")
        self.startup_checkbox.setChecked(is_auto_start_enabled(APP_NAME))
        self.startup_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.startup_checkbox.toggled.connect(self.on_startup_toggled)
        self.card_layout.addWidget(self.startup_checkbox)

        # Settings & Action Center Background Opacity Slider (Min 85%)
        ui_bg_box = QVBoxLayout()
        ui_bg_box.setSpacing(4)

        current_ui_bg_opacity = max(0.85, float(config.data.get("ui_bg_opacity", 0.95)))
        self.ui_bg_title = QLabel(
            f"Settings & Action Center Background ({int(current_ui_bg_opacity * 100)}%)"
        )
        self.ui_bg_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.ui_bg_title.setObjectName("SubHeader")

        self.ui_bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.ui_bg_slider.setMinimum(85)
        self.ui_bg_slider.setMaximum(100)
        self.ui_bg_slider.setValue(int(current_ui_bg_opacity * 100))
        self.ui_bg_slider.valueChanged.connect(self.on_ui_bg_opacity_changed)

        ui_bg_box.addWidget(self.ui_bg_title)
        ui_bg_box.addWidget(self.ui_bg_slider)
        self.card_layout.addLayout(ui_bg_box)

        # Toast Background Opacity Slider (Explicitly for Notifications)
        bg_box = QVBoxLayout()
        bg_box.setSpacing(4)
        self.bg_title = QLabel(
            f"Notification Background Opacity ({int(config.data.get('bg_opacity', 0.85) * 100)}%)"
        )
        self.bg_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.bg_title.setObjectName("SubHeader")

        self.bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_slider.setMinimum(30)
        self.bg_slider.setMaximum(100)
        self.bg_slider.setValue(int(config.data.get("bg_opacity", 0.85) * 100))
        self.bg_slider.valueChanged.connect(self.on_bg_opacity_changed)

        bg_box.addWidget(self.bg_title)
        bg_box.addWidget(self.bg_slider)
        self.card_layout.addLayout(bg_box)

        # Notification Foreground Opacity Slider (Explicitly for Notifications Only)
        fg_box = QVBoxLayout()
        fg_box.setSpacing(4)
        self.fg_title = QLabel(
            f"Notification Foreground Opacity ({int(config.data.get('fg_opacity', 1.0) * 100)}%)"
        )
        self.fg_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.fg_title.setObjectName("SubHeader")

        self.fg_slider = QSlider(Qt.Orientation.Horizontal)
        self.fg_slider.setMinimum(20)
        self.fg_slider.setMaximum(100)
        self.fg_slider.setValue(int(config.data.get("fg_opacity", 1.0) * 100))
        self.fg_slider.valueChanged.connect(self.on_fg_opacity_changed)

        fg_box.addWidget(self.fg_title)
        fg_box.addWidget(self.fg_slider)
        self.card_layout.addLayout(fg_box)

        self.card_layout.addStretch(1)

    def _setup_action_buttons(self):
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.test_btn = QPushButton("🔔 Test Notification")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.setObjectName("TestBtn")
        self.test_btn.clicked.connect(self.on_test_clicked)

        self.done_btn = QPushButton("Done")
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.setObjectName("DoneBtn")
        self.done_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.test_btn, stretch=2)
        btn_layout.addWidget(self.done_btn, stretch=1)
        self.card_layout.addLayout(btn_layout)

    # COMBOBOX POPUP HELPERS
    def _configure_combo_popup(self, combo: QComboBox):
        list_view = QListView(combo)
        list_view.setItemDelegate(QStyledItemDelegate(list_view))
        list_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_view.setAutoFillBackground(True)
        combo.setView(list_view)

    def _update_combo_popup_style(self, combo: QComboBox):
        view = combo.view()
        if not view:
            return

        theme_bg = QColor(config.current_theme["bg_color"])

        # Apply clean background handling for the popup list
        pal = view.palette()
        pal.setColor(QPalette.ColorRole.Base, theme_bg)
        view.setPalette(pal)
        view.setAutoFillBackground(True)

        popup = view.parentWidget()
        if popup:
            pal = popup.palette()
            pal.setColor(QPalette.ColorRole.Window, theme_bg)
            popup.setPalette(pal)
            popup.setAutoFillBackground(True)
            popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    # PIN LOGIC & MOUSE DRAGGING
    def _update_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        if self.is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        logger.info("Window pin state toggled", extra={"pinned": self.is_pinned})
        self._update_window_flags()
        self.show()
        self.apply_theme_styles()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child and (
                child == self.title_bar_frame
                or self.title_bar_frame.isAncestorOf(child)
            ):
                self._drag_pos = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
        ) and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = QPoint()
        super().mouseReleaseEvent(event)

    # STYLES & EVENT HANDLERS
    def apply_theme_styles(self):
        theme = config.current_theme
        # Settings & Action Center background opacity
        bg_alpha = max(0.85, float(config.data.get("ui_bg_opacity", 0.95)))
        ui_fg_alpha = 1.0

        pin_bg = (
            config.hex_to_rgba(theme.get("progress_bar_fill", "#007ACC"), ui_fg_alpha)
            if self.is_pinned
            else "transparent"
        )
        pin_color = (
            config.hex_to_rgba(theme.get("bg_color", "#202020"), bg_alpha)
            if self.is_pinned
            else config.hex_to_rgba(theme.get("body_color", "#CCCCCC"), ui_fg_alpha)
        )

        style_vars = {
            "bg_rgba": config.hex_to_rgba(theme.get("bg_color", "#202020"), bg_alpha),
            "border_rgba": config.hex_to_rgba(
                theme.get("border_color", "#404040"), bg_alpha
            ),
            "border_radius": str(theme.get("border_radius", "12px")),
            "title_rgba": config.hex_to_rgba(
                theme.get("title_color", "#FFFFFF"), ui_fg_alpha
            ),
            "body_rgba": config.hex_to_rgba(
                theme.get("body_color", "#CCCCCC"), ui_fg_alpha
            ),
            "accent_rgba": config.hex_to_rgba(
                theme.get("progress_bar_fill", "#007ACC"), ui_fg_alpha
            ),
            "pin_bg": pin_bg,
            "pin_color": pin_color,
            "close_hover_rgba": config.hex_to_rgba(
                theme.get("close_btn_hover", "#FFFFFF"), ui_fg_alpha
            ),
            "dropdown_arrow_rgba": config.hex_to_rgba(
                theme.get("body_color", "#CCCCCC"), ui_fg_alpha
            ),
        }

        try:
            rendered_qss = load_component_style("settings.qss", style_vars)
            if rendered_qss:
                self.setStyleSheet(rendered_qss)
            else:
                logger.error(
                    "Failed to apply settings stylesheet; template returned empty."
                )
        except Exception as e:
            logger.error(
                "Error applying settings stylesheet",
                extra={
                    "error_type": type(e).__name__,
                    "details": str(e),
                },
            )

    def on_theme_changed(self, theme_name: str):
        config.data["theme_name"] = theme_name
        config.save()
        logger.info("Theme selection updated", extra={"theme_name": theme_name})

        if not self.theme_combo.view().isVisible():
            self.apply_theme_styles()
            self._update_combo_popup_style(self.theme_combo)
            self._update_combo_popup_style(self.pos_combo)
            self._update_combo_popup_style(self.ac_pos_combo)

        self.settings_changed.emit()
        if hasattr(config, "theme_changed"):
            config.theme_changed.emit()

    def on_bg_opacity_changed(self, value: int):
        opacity = value / 100.0
        config.data["bg_opacity"] = opacity
        self.bg_title.setText(f"Notification Background Opacity ({value}%)")
        config.save()
        logger.debug(
            "Notification background opacity adjusted", extra={"opacity": opacity}
        )
        self.settings_changed.emit()

    def on_ui_bg_opacity_changed(self, value: int):
        opacity = max(0.85, value / 100.0)
        config.data["ui_bg_opacity"] = opacity
        self.ui_bg_title.setText(f"Settings & Action Center Background ({value}%)")
        config.save()
        logger.debug("UI background opacity adjusted", extra={"opacity": opacity})
        self.apply_theme_styles()
        self.settings_changed.emit()

    def on_fg_opacity_changed(self, value: int):
        opacity = value / 100.0
        config.data["fg_opacity"] = opacity
        self.fg_title.setText(f"Notification Foreground Opacity ({value}%)")
        config.save()
        logger.debug(
            "Notification foreground opacity adjusted", extra={"opacity": opacity}
        )
        # Note: Does NOT call self.apply_theme_styles() so the settings UI remains isolated from toast text opacity changes
        self.settings_changed.emit()

    def _on_position_changed(self, index: int):
        value_map = {0: "bottom_right", 1: "top_right", 2: "bottom_left", 3: "top_left"}
        new_pos = value_map.get(index, "bottom_right")
        config.data["toast_position"] = new_pos
        config.save()
        logger.info("Toast position changed", extra={"toast_position": new_pos})
        self.settings_changed.emit()

    def _on_action_center_position_changed(self, index: int):
        new_pos = "right" if index == 0 else "left"
        config.data["action_center_position"] = new_pos
        config.save()
        logger.info(
            "Action center position changed", extra={"action_center_position": new_pos}
        )
        self.settings_changed.emit()

    def on_startup_toggled(self, checked: bool):
        set_auto_start(checked, APP_NAME)
        self.settings_changed.emit()

    def on_test_clicked(self):
        logger.info("Test notification requested from settings")
        self.test_notification_requested.emit()

    def showEvent(self, event):
        """Called automatically whenever the settings window is opened/shown."""
        super().showEvent(event)
        # Re-sync the checkbox state with the actual system registry
        if hasattr(self, "startup_checkbox"):
            # Temporarily block signals so toggled() doesn't fire and rewrite the registry while checking
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(is_auto_start_enabled(APP_NAME))
            self.startup_checkbox.blockSignals(False)
