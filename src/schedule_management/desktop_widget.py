"""
Desktop widget installer for Übersicht (macOS only).

Generates and installs an Übersicht widget that displays `rmd ls` output
on the desktop. Handles Übersicht installation via Homebrew if needed.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tomllib
from pathlib import Path

from schedule_management.i18n import _t


WIDGET_NAME = "rmd-tasks"
WIDGET_DIR_NAME = f"{WIDGET_NAME}.widget"
WIDGET_FILE_NAME = f"{WIDGET_NAME}.widget.coffee"

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_TEMPLATE_FILE = _TEMPLATE_DIR / "rmd-tasks.widget.coffee"

DEFAULT_REFRESH_SECONDS = 30


def _get_uebersicht_widgets_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Übersicht" / "widgets"


def _is_uebersicht_installed() -> bool:
    result = subprocess.run(
        ["mdfind", "kMDItemCFBundleIdentifier == 'tracesOf.Uebersicht'"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _install_uebersicht() -> bool:
    if not shutil.which("brew"):
        print(_t("Homebrew is not installed. Please install it from https://brew.sh"))
        return False

    print(_t("Installing Übersicht via Homebrew..."))
    result = subprocess.run(
        ["brew", "install", "--cask", "ubersicht"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(_t("Failed to install Übersicht: {error}").format(error=result.stderr.strip()))
        return False
    print(_t("Übersicht installed successfully."))
    return True


def _find_rmd_path() -> str | None:
    return shutil.which("rmd")


def _get_refresh_frequency_ms() -> int:
    from schedule_management.config_layout import resolve_runtime_paths

    settings_path = resolve_runtime_paths().settings_path
    if settings_path.exists():
        try:
            with open(settings_path, "rb") as f:
                data = tomllib.load(f)
            seconds = data.get("desktop_widget", {}).get(
                "refresh_frequency", DEFAULT_REFRESH_SECONDS
            )
            return int(seconds) * 1000
        except (OSError, tomllib.TOMLDecodeError, ValueError):
            pass
    return DEFAULT_REFRESH_SECONDS * 1000


def install_widget(rmd_path: str | None = None) -> bool:
    if platform.system() != "Darwin":
        print(_t("Desktop widget is only supported on macOS."))
        return False

    if rmd_path is None:
        rmd_path = _find_rmd_path()
    if rmd_path is None:
        print(_t("Could not find 'rmd' executable in PATH."))
        return False

    if not _is_uebersicht_installed():
        if not _install_uebersicht():
            return False

    if not _TEMPLATE_FILE.exists():
        print(_t("Widget template not found: {path}").format(path=_TEMPLATE_FILE))
        return False

    widget_content = _TEMPLATE_FILE.read_text(encoding="utf-8")
    widget_content = widget_content.replace("{{RMD_PATH}}", rmd_path)
    widget_content = widget_content.replace(
        "{{REFRESH_FREQUENCY}}", str(_get_refresh_frequency_ms())
    )

    widgets_dir = _get_uebersicht_widgets_dir()
    widget_dir = widgets_dir / WIDGET_DIR_NAME
    widget_dir.mkdir(parents=True, exist_ok=True)

    widget_file = widget_dir / WIDGET_FILE_NAME
    widget_file.write_text(widget_content, encoding="utf-8")
    print(_t("Widget installed at: {path}").format(path=widget_dir))
    return True


def uninstall_widget() -> bool:
    widgets_dir = _get_uebersicht_widgets_dir()
    widget_dir = widgets_dir / WIDGET_DIR_NAME
    if widget_dir.exists():
        shutil.rmtree(widget_dir)
        print(_t("Widget removed."))
        return True
    print(_t("Widget is not installed."))
    return False


def is_widget_installed() -> bool:
    widget_dir = _get_uebersicht_widgets_dir() / WIDGET_DIR_NAME
    return widget_dir.exists()
