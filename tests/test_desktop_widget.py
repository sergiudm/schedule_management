"""
Unit tests for schedule_management.desktop_widget module.
"""

from __future__ import annotations

import schedule_management.desktop_widget as desktop_widget
from schedule_management.desktop_widget import (
    _TEMPLATE_FILE,
    install_widget,
    is_widget_installed,
    uninstall_widget,
)


def test_widget_template_exists():
    assert _TEMPLATE_FILE.exists()
    content = _TEMPLATE_FILE.read_text(encoding="utf-8")
    assert "{{RMD_PATH}}" in content
    assert "{{REFRESH_FREQUENCY}}" in content


def test_install_widget_non_darwin(monkeypatch):
    monkeypatch.setattr(desktop_widget.platform, "system", lambda: "Linux")
    assert install_widget() is False


def test_install_and_uninstall_widget(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_widget.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop_widget, "_get_uebersicht_widgets_dir", lambda: tmp_path)
    monkeypatch.setattr(desktop_widget, "_is_uebersicht_installed", lambda: True)

    assert is_widget_installed() is False

    result = install_widget(rmd_path="/usr/local/bin/rmd")
    assert result is True

    widget_file = tmp_path / desktop_widget.WIDGET_DIR_NAME / desktop_widget.WIDGET_FILE_NAME
    assert widget_file.exists()
    content = widget_file.read_text(encoding="utf-8")
    assert "{{RMD_PATH}}" not in content
    assert "/usr/local/bin/rmd" in content

    assert is_widget_installed() is True

    uninstall_result = uninstall_widget()
    assert uninstall_result is True

    assert is_widget_installed() is False
