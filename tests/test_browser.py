"""Explicit local integration tests: pytest -m browser (opens installed Chrome)."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PySide6.QtCore import Qt

from vscodl2 import core
from vscodl2.app import MainWindow


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class GalleryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append(self.path)
        self.server.request_headers.append((self.path, dict(self.headers)))
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if self.path == "/asset.png":
            body = PNG
            content_type = "image/png"
        elif self.path.startswith("/api/3.0/medias/profile"):
            body = json.dumps({
                "media": [{
                    "type": "image",
                    "image": {
                        "_id": "api-item",
                        "is_video": False,
                        "video_url": "",
                        "responsive_url": f"{origin}/asset.png",
                        "upload_date": 1700000000000,
                        "capture_date_ms": 1690000000000,
                        "width": 1920,
                        "height": 1080,
                        "description": "API fixture",
                    },
                }],
                "next_cursor": None,
            }).encode()
            content_type = "application/json"
        elif self.path.startswith(("/session-check", "/client-info")):
            body = b"{}"
            content_type = "application/json"
        else:
            state = {"medias": {"byId": {"preloaded-item": {"media": {
                "isVideo": False,
                "responsiveUrl": f"{origin}/asset.png",
                "uploadDate": 1700000000000,
                "captureDateMs": 1690000000000,
                "width": 2560,
                "height": 1440,
                "description": "Preloaded fixture",
            }}}}}
            body = (
                "<html><body><h1>Local gallery fixture</h1>"
                '<img id="fixture-image" src="/asset.png">'
                "<script>window.__PRELOADED_STATE__=" + json.dumps(state) + ";"
                "window.hadSavedSession=localStorage.getItem('vscodl2_session');"
                "fetch('/client-info?webdriver='+navigator.webdriver+'&ua='+encodeURIComponent(navigator.userAgent));"
                "fetch('/session-check?restored='+(window.hadSavedSession||''));"
                "localStorage.setItem('vscodl2_session','saved');"
                "fetch('/api/3.0/medias/profile?site_id=1');</script>"
                "</body></html>"
            ).encode()
            content_type = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def start_gallery_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), GalleryHandler)
    server.requests = []
    server.request_headers = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/fixture/gallery"


@pytest.mark.browser
def test_real_chrome_loads_image_captures_api_and_restores_own_profile(tmp_path):
    server, gallery = start_gallery_server()
    job = core.Job(gallery, str(tmp_path))

    for _ in range(2):
        control = core.Control()
        events = []

        def emit(event):
            events.append(event)
            if event["type"] == "manual":
                control.resume()

        core.scan_gallery(job, emit, control)
        manifest = json.loads(job.scan_path.read_text(encoding="utf-8"))
        assert {item["media_id"] for item in manifest["items"]} == {"preloaded-item", "api-item"}
        assert events[-1] == {"type": "done"}
        assert any(event["type"] == "manual" for event in events)
        assert any(event["type"] == "scanned" for event in events)

    server.shutdown()
    server.server_close()
    assert server.requests.count("/asset.png") >= 2
    assert sum(path.startswith("/api/3.0/medias/profile") for path in server.requests) >= 2
    session_checks = [path for path in server.requests if path.startswith("/session-check")]
    assert session_checks[0] == "/session-check?restored="
    assert session_checks[1] == "/session-check?restored=saved"
    navigation_headers = next(headers for path, headers in server.request_headers if path == "/fixture/gallery")
    assert "Chrome/" in navigation_headers["User-Agent"]
    assert "HeadlessChrome" not in navigation_headers["User-Agent"]
    assert "text/html" in navigation_headers["Accept"]
    assert navigation_headers["Sec-Fetch-Dest"] == "document"
    assert navigation_headers["Sec-Fetch-Mode"] == "navigate"
    client_info = next(path for path in server.requests if path.startswith("/client-info"))
    assert "webdriver=false" in client_info
    assert "Chrome" in client_info
    assert (tmp_path / "browser-profile" / "Default").is_dir()


@pytest.mark.browser
def test_qt_open_and_confirm_buttons_drive_real_browser_worker(qtbot, tmp_path, monkeypatch):
    server, gallery = start_gallery_server()
    monkeypatch.chdir(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.url.setText(gallery)
    window.show()

    qtbot.mouseClick(window.open_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.confirm_button.isEnabled(), timeout=20000)
    assert window.captured_label.text() == "Browser session active"
    qtbot.mouseClick(window.confirm_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.worker.state() == window.worker.ProcessState.NotRunning, timeout=30000)

    server.shutdown()
    server.server_close()
    assert not window.error_details.isVisible()
    assert window.model.rowCount() == 2
    assert window.result_count.text() == "2 items"
    assert server.requests.count("/asset.png") >= 1
    assert any(path.startswith("/api/3.0/medias/profile") for path in server.requests)
