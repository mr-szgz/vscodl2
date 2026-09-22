import json

from vscodl2.app import MainWindow
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QFileDialog


def configure_app_paths(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    downloads_dir = tmp_path / "Downloads"
    monkeypatch.setattr("vscodl2.app.user_config_path", lambda *args, **kwargs: config_dir)
    monkeypatch.setattr("vscodl2.app.user_downloads_path", lambda: downloads_dir)
    return config_dir, downloads_dir


def test_initial_ui_is_ready_for_manual_browser_session(qtbot, tmp_path, monkeypatch):
    config_dir, downloads_dir = configure_app_paths(monkeypatch, tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.windowTitle() == "VSCODL2"
    assert window.url.text() == ""
    assert window.open_button.text() == "Open browser session"
    assert not window.confirm_button.isEnabled()
    assert not window.download_button.isEnabled()
    assert window.config_dir == config_dir
    assert window.download_dir == downloads_dir / "VSCODL2"
    assert window.download_directory.text() == str(downloads_dir / "VSCODL2")
    assert json.loads(window.settings_path.read_text()) == {
        "download_directory": str(downloads_dir / "VSCODL2")
    }


def test_download_folder_picker_persists_selection(qtbot, tmp_path, monkeypatch):
    configure_app_paths(monkeypatch, tmp_path)
    selected = tmp_path / "Media"
    selected.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(selected))
    window = MainWindow()
    qtbot.addWidget(window)

    window.browse_downloads_button.click()

    assert window.download_dir == selected
    assert window.download_directory.text() == str(selected)
    assert json.loads(window.settings_path.read_text()) == {
        "download_directory": str(selected)
    }
    restored = MainWindow()
    qtbot.addWidget(restored)
    assert restored.download_dir == selected


def test_scanned_event_populates_results(qtbot, tmp_path, monkeypatch):
    configure_app_paths(monkeypatch, tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    event = {
        "type": "scanned",
        "scan_path": str(tmp_path / "data" / "scans" / "fixture.json"),
        "items": [
            {
                "media_id": "fixture",
                "media_type": "Image",
                "url": "https://media.test/fixture.jpg",
                "filename": "fixture.jpg",
                "width": 100,
                "height": 200,
                "captured_at": 1700000000000,
                "description": "Fixture",
            }
        ],
    }

    window.handle_event(event)

    assert window.model.rowCount() == 1
    assert window.result_count.text() == "1 items"
    assert window.download_button.isEnabled()


def test_full_worker_error_can_be_read_copied_and_retrieved_from_disk(qtbot, tmp_path, monkeypatch):
    configure_app_paths(monkeypatch, tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    error = "Traceback (most recent call last):\n" + "  fixture stack frame\n" * 50
    error += "BrowserContext.new_page: Target page, context or browser has been closed\n"
    window.stderr_buffer = error
    window.operation = "scan"
    window._worker_finished(1, QProcess.ExitStatus.NormalExit)
    assert window.error_details.toPlainText() == error
    assert window.error_details.isVisible()
    assert window.open_button.isEnabled()
    assert not window.download_button.isEnabled()
    assert window.captured_label.text() == "Operation stopped"
    window.copy_error_button.click()
    assert QApplication.clipboard().text() == error
    assert (window.config_dir / "last-error.log").read_text() == error


def test_browser_failures_are_visible_and_saved(qtbot, tmp_path, monkeypatch):
    configure_app_paths(monkeypatch, tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.handle_event({
        "type": "browser_log",
        "level": "error",
        "message": "HTTP 403: https://vsco.co/api/3.0/medias/profile",
    })
    assert "HTTP 403" in window.error_details.toPlainText()
    assert window.error_details.isVisible()
    assert "HTTP 403" in (window.config_dir / "browser-console.log").read_text()
