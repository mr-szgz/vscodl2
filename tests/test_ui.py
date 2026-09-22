from vscodl2.app import MainWindow
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication


def test_initial_ui_is_ready_for_manual_browser_session(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.windowTitle() == "VSCODL2"
    assert window.open_button.text() == "Open browser session"
    assert not window.confirm_button.isEnabled()
    assert not window.download_button.isEnabled()
    assert window.data_dir == tmp_path / "data"


def test_scanned_event_populates_results(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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
                "preview_url": "https://media.test/preview.jpg",
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
    monkeypatch.chdir(tmp_path)
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
    assert (window.data_dir / "last-error.log").read_text() == error


def test_browser_failures_are_visible_and_saved(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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
    assert "HTTP 403" in (window.data_dir / "browser-console.log").read_text()
