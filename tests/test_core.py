from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import json
from types import SimpleNamespace

import pytest
import vscodl2.core as core
from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage

from vscodl2.core import (
    Control,
    Job,
    MediaItem,
    absolute_media_url,
    download_media,
    gallery_name,
    original_image_url,
    is_gallery_page,
)


def api_entry(*, video=False):
    return {
        "type": "image",
        "image": {
            "_id": "abc123",
            "is_video": video,
            "video_url": "video.vsco.test/media/abc123.mp4",
            "responsive_url": "im.vsco.test/media/abc123.jpg",
            "upload_date": 1700000000000,
            "capture_date_ms": 1690000000000,
            "width": 1920,
            "height": 1080,
            "description": "Fixture media",
        },
    }


def test_media_item_from_image_api():
    item = MediaItem.from_api(api_entry())

    assert item.media_id == "abc123"
    assert item.media_type == "Image"
    assert item.url == "https://im.vsco.test/media/abc123.jpg"
    assert item.filename == "1700000000000_abc123_original.jpg"


def test_media_item_from_video_api():
    item = MediaItem.from_api(api_entry(video=True))

    assert item.media_type == "Video"
    assert item.url == "https://video.vsco.test/media/abc123.mp4"
    assert item.preview_url == "https://im.vsco.test/media/abc123.jpg"


def test_gallery_helpers():
    assert gallery_name("https://vsco.co/-evalee/gallery") == "-evalee"
    assert absolute_media_url("//im.vsco.co/file.jpg") == "https://im.vsco.co/file.jpg"


def test_download_media_uses_username_photo_directory(tmp_path):
    image = QImage(2560, 1440, QImage.Format.Format_RGB32)
    image.fill(0xFF123456)
    encoded = QByteArray()
    buffer = QBuffer(encoded)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    payload = bytes(encoded)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    item = MediaItem(
        media_id="fixture",
        media_type="Image",
        url=f"http://127.0.0.1:{server.server_port}/fixture.png",
        preview_url="",
        filename="fixture_original.png",
        width=2560,
        height=1440,
        captured_at=1700000000000,
        description="",
    )
    events = []
    job = Job("https://vsco.co/fixture/gallery", str(tmp_path))
    job.download_path.mkdir(parents=True)
    legacy = job.download_path / "fixture.png"
    legacy.write_bytes(b"existing preview")

    download_media(job, [asdict(item)], events.append, Control())
    server.shutdown()

    destination = tmp_path / "fixture" / "photo" / "fixture_original.png"
    assert destination.read_bytes() == payload
    result = QImage(str(destination))
    assert (result.width(), result.height()) == (2560, 1440)
    assert legacy.read_bytes() == b"existing preview"
    assert events[-1] == {"type": "done", "stopped": False}


def test_download_media_uses_video_directory_and_skips_existing_file(tmp_path):
    item = MediaItem(
        media_id="fixture",
        media_type="Video",
        url="https://example.test/fixture.mp4",
        preview_url="",
        filename="fixture_original.mp4",
        width=1920,
        height=1080,
        captured_at=1700000000000,
        description="",
    )
    job = Job("https://vsco.co/fixture/gallery", str(tmp_path))
    destination = tmp_path / "fixture" / "video" / "fixture_original.mp4"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing video")
    events = []

    download_media(job, [asdict(item)], events.append, Control())

    assert destination.read_bytes() == b"existing video"
    assert events[-2] == {
        "type": "downloaded",
        "current": 1,
        "total": 1,
        "media_id": "fixture",
        "path": str(destination),
        "skipped": True,
    }
    assert events[-1] == {"type": "done", "stopped": False}


@pytest.mark.parametrize(("source", "expected"), [
    ("//im.vsco.co/aws-us-west-2/abc/photo.jpg?w=480&h=320&q=75&fit=crop&auto=webp",
     "https://image-aws-us-west-2.vsco.co/abc/photo.jpg"),
    ("im.vsco.co/1/abc/photo.jpg?w=320", "https://image.vsco.co/1/abc/photo.jpg"),
    ("https://im.vsco.co/media/photo.jpg?token=a%2Fb+z&w=400&expires=123",
     "https://im.vsco.co/media/photo.jpg?token=a%2Fb+z&expires=123"),
    ("https://other.test/photo.jpg?w=320", "https://other.test/photo.jpg?w=320"),
])
def test_original_image_url(source, expected):
    assert original_image_url(source) == expected


def preloaded_entry():
    return {
        "isVideo": False, "responsiveUrl": "im.vsco.co/1/abc/photo.jpg?w=320",
        "uploadDate": 1700000000000, "captureDateMs": 1690000000000,
        "width": 4032, "height": 3024, "description": "Original photo",
    }


def test_preloaded_photo_and_video_keep_source_resolution():
    photo = preloaded_entry()
    item = MediaItem.from_preloaded("abc", photo)
    assert item.url == "https://image.vsco.co/1/abc/photo.jpg"
    assert (item.width, item.height) == (4032, 3024)
    assert item.preview_url.endswith("?w=320")
    photo.update(isVideo=True, videoUrl="//video.vsco.co/abc.mp4?token=x%2Fy")
    video = MediaItem.from_preloaded("abc", photo)
    assert video.url == "https://video.vsco.co/abc.mp4?token=x%2Fy"
    assert video.filename.endswith("_original.mp4")


def test_api_video_wrapper():
    entry = api_entry(video=True)
    entry["type"] = "video"
    entry["video"] = entry.pop("image")
    assert MediaItem.from_api(entry).media_type == "Video"


def test_page_scope_excludes_other_profiles_and_impostor_hosts():
    gallery = "https://vsco.co/fixture/gallery"
    assert is_gallery_page("https://www.vsco.co/fixture/media/abc", gallery)
    assert not is_gallery_page("https://vsco.co/another/gallery", gallery)
    assert not is_gallery_page("https://vsco.co.evil.test/fixture/gallery", gallery)


def test_scan_collects_preloaded_and_api_once_without_extra_requests(tmp_path, monkeypatch):
    control = Control()
    events = []
    handlers = {}
    page_handlers = {}
    gallery = "https://vsco.co/fixture/gallery"
    page = SimpleNamespace(url=gallery)
    page.on = lambda event, callback: page_handlers.update({event: callback})
    page.evaluate = lambda script: {"preloaded": {"media": preloaded_entry()}}
    response = SimpleNamespace(status=200, json=lambda: {"media": [api_entry(), api_entry()], "next_cursor": None})
    request = SimpleNamespace(url="https://vsco.co/api/3.0/medias/profile?site_id=1",
                              frame=SimpleNamespace(page=page), response=lambda: response)

    def navigate(url, **kwargs):
        assert url == gallery
        page_handlers["domcontentloaded"]()
        handlers["requestfinished"](request)
        handlers["requestfinished"](request)

    page.goto = navigate
    page.wait_for_timeout = lambda milliseconds: control.resume()
    context = SimpleNamespace(pages=[page], new_page=lambda: page)
    context.on = lambda event, callback: handlers.update({event: callback})
    cdp = SimpleNamespace(send=lambda method: None)
    browser = SimpleNamespace(contexts=[context], new_browser_cdp_session=lambda: cdp)
    process = SimpleNamespace(wait=lambda: None)

    def launch_chrome(command):
        return process

    class Playwright:
        def __enter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=lambda endpoint: browser))

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(core, "sync_playwright", Playwright)
    monkeypatch.setattr(core.subprocess, "Popen", launch_chrome)
    monkeypatch.setattr(core, "available_debugging_port", lambda: 12345)
    monkeypatch.setattr(core, "wait_for_debugging_port", lambda port: None)
    job = Job(gallery, str(tmp_path))
    core.scan_gallery(job, events.append, control)
    manifest = json.loads(job.scan_path.read_text())
    assert {item["media_id"] for item in manifest["items"]} == {"abc123", "preloaded"}
    assert [event for event in events if event["type"] == "captured"] == [{"type": "captured", "total": 2}]
    assert events[-1] == {"type": "done"}


def test_full_scan_clicks_load_more_and_collects_over_1000_items():
    captured = {}
    clicks = []
    scrolls = []
    loads = []
    button = SimpleNamespace(count=lambda: 1, is_visible=lambda: True,
                             is_enabled=lambda: True, click=lambda: clicks.append(True))
    button.first = button
    absent = SimpleNamespace(count=lambda: 0)
    page = SimpleNamespace(
        get_by_text=lambda text, **kwargs: button if text == "Load more" else absent,
        evaluate=lambda script: scrolls.append(script), wait_for_timeout=lambda ms: None,
    )

    def collect():
        offset = len(captured)
        captured.update({str(i): None for i in range(offset, offset + 12)})
        loads.append(True)

    result = core.scroll_gallery(page, collect, captured, lambda: len(loads) == 84,
                                 lambda event: None, Control())
    assert len(captured) == 1008
    assert len(clicks) == len(scrolls) == 84
    assert result == "VSCO reported the final gallery page."


def test_scan_stall_does_not_claim_entire_gallery_was_scanned():
    waits = []
    page = SimpleNamespace(get_by_text=lambda *args, **kwargs: SimpleNamespace(count=lambda: 0),
                           evaluate=lambda script: None, wait_for_timeout=waits.append)
    result = core.scroll_gallery(page, lambda: None, {}, lambda: False, lambda event: None, Control())
    assert sum(waits) == 30000
    assert "completeness is not confirmed" in result


def test_scan_pauses_for_verification_and_can_be_cancelled():
    control = Control()
    challenge = SimpleNamespace(count=lambda: 1, is_visible=lambda: True)
    challenge.first = challenge
    page = SimpleNamespace(get_by_text=lambda *args, **kwargs: challenge,
                           wait_for_timeout=lambda ms: control.stop())
    events = []
    core.scroll_gallery(page, lambda: None, {}, lambda: False, events.append, control)
    assert events[0]["type"] == "manual"
    assert control.stopped.is_set()
