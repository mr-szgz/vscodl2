"""Exercise the frozen worker with installed Chrome and a local gallery."""

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append(self.path)
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if self.path == "/asset.png":
            body = PNG
            content_type = "image/png"
        elif self.path.startswith("/api/3.0/medias/profile"):
            body = json.dumps({
                "media": [{
                    "type": "image",
                    "image": {
                        "_id": "frozen-api-item",
                        "is_video": False,
                        "video_url": "",
                        "responsive_url": f"{origin}/asset.png",
                        "upload_date": 1700000000000,
                        "capture_date_ms": 1690000000000,
                        "width": 1920,
                        "height": 1080,
                        "description": "Frozen API fixture",
                    },
                }],
                "next_cursor": None,
            }).encode()
            content_type = "application/json"
        else:
            state = {"medias": {"byId": {"frozen-preloaded-item": {"media": {
                "isVideo": False,
                "responsiveUrl": f"{origin}/asset.png",
                "uploadDate": 1700000000000,
                "captureDateMs": 1690000000000,
                "width": 2560,
                "height": 1440,
                "description": "Frozen preloaded fixture",
            }}}}}
            body = (
                "<html><body><h1>Frozen gallery fixture</h1>"
                '<img src="/asset.png">'
                "<script>window.__PRELOADED_STATE__=" + json.dumps(state) + ";"
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


def main():
    worker = Path(sys.argv[1]).resolve()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.requests = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    gallery = f"http://127.0.0.1:{server.server_port}/fixture/gallery"

    with tempfile.TemporaryDirectory(prefix="vscodl2-frozen-smoke-") as directory:
        request = {"operation": "scan", "job": {"gallery_url": gallery, "data_dir": directory}, "items": None}
        process = subprocess.Popen(
            [worker], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )
        stdout, stderr = process.communicate(json.dumps(request) + "\nresume\n", timeout=30)
        assert process.returncode == 0, stderr
        events = [json.loads(line) for line in stdout.splitlines()]
        scanned = next(event for event in events if event["type"] == "scanned")
        assert {item["media_id"] for item in scanned["items"]} == {
            "frozen-preloaded-item", "frozen-api-item",
        }
        assert any(event["type"] == "manual" for event in events)
        assert events[-1] == {"type": "done"}
        assert (Path(directory) / "browser-profile" / "Default").is_dir()
        assert (Path(directory) / "scans" / "fixture.json").is_file()

    server.shutdown()
    server.server_close()
    assert "/asset.png" in server.requests
    assert any(path.startswith("/api/3.0/medias/profile") for path in server.requests)
    print("Frozen worker browser smoke test passed: visible Chrome, image, API capture, profile, manifest.")


if __name__ == "__main__":
    main()
