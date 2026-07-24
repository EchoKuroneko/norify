import json, os, sys
from pathlib import Path
from typing import Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from core.logger import logger


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


AUTHOR_NAME = "EchoKuroneko"
APP_NAME = "Norify"
APP_ID = AUTHOR_NAME + "." + APP_NAME

# Paths
app_data_dir = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
app_data_dir.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = app_data_dir / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = ASSETS_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ICON_DIR = ASSETS_DIR / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

ICON_PATH = ICON_DIR / "app_icon.ico"

THEMES_FILE = Path(resource_path(os.path.join("assets", "themes.json")))

SETTINGS_FILE = app_data_dir / "settings.json"
DB_FILE = app_data_dir / f"{APP_NAME.lower()}.db"

# Built-in fallback theme in case themes.json is missing or invalid
FALLBACK_THEMES: Dict[str, Dict[str, str]] = {
    "Catppuccin Macchiato": {
        "bg_color": "#1e1e2e",
        "border_color": "#313244",
        "border_radius": "10px",
        "title_color": "#89b4fa",
        "body_color": "#cdd6f4",
        "close_btn_color": "#a6adc8",
        "close_btn_hover": "#f38ba8",
        "progress_bar_bg": "#313244",
        "progress_bar_fill": "#89b4fa",
    }
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme_name": "Catppuccin Macchiato",
    "bg_opacity": 0.85,
    "ui_bg_opacity": 0.95,  # 0.85 to 1.0
    "fg_opacity": 1.00,
    "toast_duration_ms": 5000,
    "toast_position": "bottom_right",  # "bottom_right", "top_right", "bottom_left", "top_left"
    "action_center_position": "right",  # "right", "left"
}


def load_themes() -> Dict[str, Dict[str, str]]:
    """Loads theme definitions from disk, falling back to embedded defaults."""
    if THEMES_FILE.exists():
        try:
            with open(THEMES_FILE, "r", encoding="utf-8") as f:
                themes = json.load(f)
                logger.info("Loaded %d themes from %s", len(themes), THEMES_FILE.name)
                return themes
        except Exception as e:
            logger.error(
                "Failed to parse %s, using fallback theme: %s", THEMES_FILE.name, e
            )
    else:
        logger.warning(
            "%s not found. Using internal fallback themes.", THEMES_FILE.name
        )

    return FALLBACK_THEMES.copy()


THEMES = load_themes()


class ConfigManager(QObject):
    """Loads, saves, and manages application settings and theme state."""

    theme_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.data: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        """Loads configuration from settings.json."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
                    self.data.update(user_settings)
                logger.info("Settings loaded successfully from %s", SETTINGS_FILE.name)
            except Exception as e:
                logger.error("Error loading settings from disk: %s", e)
        else:
            logger.info("No settings file found. Using defaults.")

    def save(self) -> None:
        """Saves current configuration to settings.json."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            logger.info("Settings saved successfully.")
        except Exception as e:
            logger.error("Failed to save settings: %s", e)

    @property
    def current_theme(self) -> Dict[str, str]:
        """Returns the dictionary properties for the active theme."""
        theme_name = self.data.get("theme_name", "Catppuccin Macchiato")
        if theme_name in THEMES:
            return THEMES[theme_name]

        logger.warning("Theme '%s' not found. Falling back.", theme_name)
        return next(iter(THEMES.values()))

    @property
    def current_position(self) -> str:
        """Returns the active toast notification position key."""
        return self.data.get("toast_position", "bottom_right")

    def set_theme(self, theme_name: str) -> None:
        """Updates the active theme, saves settings, and emits a change signal."""
        if theme_name not in THEMES:
            logger.warning("Attempted to set unknown theme: '%s'", theme_name)
            return

        self.data["theme_name"] = theme_name
        self.save()
        logger.info("Active theme updated to '%s'", theme_name)
        self.theme_changed.emit()

    @staticmethod
    def hex_to_rgba(hex_code: str, alpha: float) -> str:
        """Converts a hex color code and alpha float into a CSS 'rgba(r, g, b, a)' string."""
        color = QColor(hex_code)
        if not color.isValid():
            logger.warning("Invalid hex code '%s' supplied to hex_to_rgba.", hex_code)
            return f"rgba(0, 0, 0, {alpha:.2f})"
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.2f})"


config = ConfigManager()

# Notification Layout Dimensions
TOAST_WIDTH = 320
TOAST_SPACING = 10  # Gap between stacked cards
SCREEN_MARGIN = 15  # Margin from screen edges
