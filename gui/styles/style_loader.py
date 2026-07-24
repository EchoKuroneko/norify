from pathlib import Path
from typing import Any, Dict

from PyQt6.QtWidgets import QApplication
from core.logger import logger

# Resolve absolute path to the directory where this style manager resides
STYLES_DIR = Path(__file__).resolve().parent


def load_component_style(filename: str, context: Dict[str, Any]) -> str:
    """Reads a .qss template file and replaces {placeholders} with context values.

    Uses simple string substitution to avoid format specifier crashes (ValueError)
    caused by colons in standard CSS blocks.
    """
    file_path = (
        STYLES_DIR / filename if not Path(filename).is_absolute() else Path(filename)
    )

    try:
        if not file_path.exists():
            logger.error(
                "Stylesheet template file missing",
                extra={"file_name": filename, "path": str(file_path.resolve())},
            )
            return ""

        content = file_path.read_text(encoding="utf-8")

        # Directly replace keys provided in context, leaving standard CSS braces untouched
        for key, val in context.items():
            content = content.replace(f"{{{key}}}", str(val))

        return content

    except Exception as e:
        logger.error(
            "Failed to load or parse component style",
            extra={
                "file_name": filename,
                "error_type": type(e).__name__,
                "details": str(e),
            },
        )
        return ""


def load_application_styles(styles_dir: str = "styles") -> str:
    """Discovers, reads, and concatenates static application .qss files.

    Ignores dynamic component templates (e.g., toast.qss) so raw {placeholders}
    are not passed to Qt's global stylesheet parser.
    """
    style_path = Path(styles_dir)
    if not style_path.is_absolute():
        if (STYLES_DIR / styles_dir).exists():
            style_path = STYLES_DIR / styles_dir
        elif STYLES_DIR.name == styles_dir:
            style_path = STYLES_DIR

    if not style_path.exists() or not style_path.is_dir():
        logger.error(
            "Style directory missing",
            extra={
                "directory_name": style_path.name,
                "resolved_path": str(style_path.resolve()),
            },
        )
        return ""

    combined_styles = []
    loaded_files = []

    for qss_file in sorted(style_path.glob("*.qss")):
        # Skip dynamic component templates intended for runtime context replacement
        if qss_file.name in (
            "toast.qss",
            "action_center.qss",
        ) or qss_file.name.endswith(".template.qss"):
            continue

        try:
            content = qss_file.read_text(encoding="utf-8")
            combined_styles.append(f"/* Source: {qss_file.name} */\n" + content)
            loaded_files.append(qss_file.name)
        except Exception as e:
            logger.error(
                "Failed to read stylesheet file",
                extra={
                    "file_name": qss_file.name,
                    "error_type": type(e).__name__,
                    "details": str(e),
                },
            )

    logger.info(
        "Successfully loaded application stylesheets",
        extra={"loaded_count": len(loaded_files), "files": loaded_files},
    )

    return "\n\n".join(combined_styles)


def apply_theme(app: QApplication, styles_dir: str = "styles") -> None:
    """Applies global concatenated stylesheets directly to the main QApplication."""
    stylesheet = load_application_styles(styles_dir)
    if stylesheet:
        app.setStyleSheet(stylesheet)
