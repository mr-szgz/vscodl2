"""Browser capture and download workflows for VSCODL2."""

from dataclasses import asdict, dataclass
from collections import deque
from datetime import datetime
import json
import re
import socket
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import unquote_plus, urlsplit, urlunsplit

import requests
from playwright.sync_api import sync_playwright

from . import __version__


CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


@dataclass(frozen=True)
class MediaItem:
    media_id: str
    media_type: str
    url: str
    filename: str
    width: int
    height: int
    captured_at: int
    description: str

    @classmethod
    def from_api(cls, entry):
        payload = entry[entry["type"]]
        is_video = entry["type"] == "video" or payload["is_video"]
        media_url = payload["video_url"] if is_video else payload["responsive_url"]
        media_url = absolute_media_url(media_url)
        if not is_video:
            media_url = original_image_url(media_url)
        media_type = "Video" if is_video else "Image"
        suffix = Path(urlsplit(media_url).path).suffix or (".mp4" if is_video else ".jpg")
        media_id = payload["_id"]
        return cls(
            media_id=media_id,
            media_type=media_type,
            url=media_url,
            filename=f"{payload['upload_date']}_{media_id}_original{suffix}",
            width=payload["width"],
            height=payload["height"],
            captured_at=payload["capture_date_ms"],
            description=payload["description"],
        )

    @classmethod
    def from_preloaded(cls, media_id, payload):
        is_video = payload["isVideo"]
        url = absolute_media_url(payload["videoUrl"] if is_video else payload["responsiveUrl"])
        if not is_video:
            url = original_image_url(url)
        suffix = Path(urlsplit(url).path).suffix or (".mp4" if is_video else ".jpg")
        return cls(
            media_id=media_id,
            media_type="Video" if is_video else "Image",
            url=url,
            filename=f"{payload['uploadDate']}_{media_id}_original{suffix}",
            width=payload["width"],
            height=payload["height"],
            captured_at=payload["captureDateMs"],
            description=payload["description"],
        )

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    @property
    def captured_text(self):
        return datetime.fromtimestamp(self.captured_at / 1000).astimezone().strftime("%Y-%m-%d %H:%M")


@dataclass(frozen=True)
class Job:
    gallery_url: str
    data_dir: str

    @property
    def data_path(self):
        return Path(self.data_dir)

    @property
    def profile_path(self):
        return self.data_path / "browser-profile"

    @property
    def scan_path(self):
        return self.data_path / "scans" / f"{gallery_name(self.gallery_url)}.json"

    @property
    def download_path(self):
        return self.data_path / gallery_name(self.gallery_url)


class Control:
    def __init__(self):
        self.ready = threading.Event()
        self.stopped = threading.Event()

    def resume(self):
        self.ready.set()

    def stop(self):
        self.stopped.set()
        self.ready.set()


def absolute_media_url(value):
    if value.startswith("//"):
        return "https:" + value
    if "://" not in value:
        return "https://" + value
    return value


def gallery_name(url):
    return urlsplit(url).path.strip("/").split("/")[0]


def original_image_url(value):
    """Remove VSCO image delivery transforms; retain opaque query values verbatim."""
    url = urlsplit(absolute_media_url(value))
    if url.hostname in {"im.vsco.co", "img.vsco.co"}:
        region, separator, asset_path = url.path.lstrip("/").partition("/")
        if separator and region.startswith("aws-"):
            url = url._replace(netloc=f"image-{region}.vsco.co", path="/" + asset_path)
        elif separator and region.isdecimal():
            url = url._replace(netloc="image.vsco.co")
        transforms = {"w", "h", "max-w", "max-h", "dpr", "fit", "crop", "rect", "ar", "q", "auto", "fm"}
        query = "&".join(
            part for part in url.query.split("&")
            if unquote_plus(part.partition("=")[0]) not in transforms
        )
        return urlunsplit(url._replace(query=query))
    return url.geturl()


def is_gallery_page(url, gallery_url):
    parsed = urlsplit(url)
    requested = urlsplit(gallery_url)
    return (
        parsed.hostname.removeprefix("www.") == requested.hostname.removeprefix("www.")
        and gallery_name(url) == gallery_name(gallery_url)
    )


def scroll_gallery(page, collect, captured, exhausted, emit, control):
    """Drive the visible gallery only after the user confirms the session."""
    idle_rounds = 0
    while not control.stopped.is_set() and not exhausted() and idle_rounds < 20:
        challenge = page.get_by_text(re.compile(
            r"^(Verify you are human|Sorry, you have been blocked|Just a moment\.\.\.)$", re.I
        ))
        if challenge.count() and challenge.first.is_visible():
            control.ready.clear()
            emit({"type": "manual", "message": "Scanning paused for site verification. Complete it in the browser, then resume scanning."})
            while not control.ready.is_set():
                page.wait_for_timeout(250)
            if control.stopped.is_set():
                break
            idle_rounds = 0
        before = len(captured)
        more = page.get_by_text("Load more", exact=True)
        if more.count() and more.first.is_visible() and more.first.is_enabled():
            more.first.click()
        page.evaluate("() => window.scrollTo(0, document.scrollingElement.scrollHeight)")
        page.wait_for_timeout(1500)
        collect()
        idle_rounds = idle_rounds + 1 if len(captured) == before else 0
        emit({"type": "stage", "message": f"Scanning gallery: {len(captured)} items found. Waiting for the next page…"})
    if exhausted():
        return "VSCO reported the final gallery page."
    return "No new media for 30 seconds; gallery completeness is not confirmed."


def close_chrome(browser, chrome_process):
    browser.new_browser_cdp_session().send("Browser.close")
    chrome_process.wait()


def available_debugging_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_for_debugging_port(port):
    deadline = time.monotonic() + 30
    result = 1
    while result and time.monotonic() < deadline:
        with socket.socket() as probe:
            result = probe.connect_ex(("127.0.0.1", port))
        if result:
            time.sleep(0.05)


def scan_gallery(job, emit, control):
    job.data_path.mkdir(parents=True, exist_ok=True)
    job.profile_path.mkdir(parents=True, exist_ok=True)
    captured = {}
    completed = deque()
    documents = deque()
    final_page = False
    port = available_debugging_port()
    emit({"type": "stage", "message": "Starting the installed Google Chrome with the saved VSCODL2 profile…"})
    chrome_process = subprocess.Popen(
        [
            CHROME_PATH,
            f"--user-data-dir={job.profile_path}",
            f"--remote-debugging-port={port}",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
    )
    wait_for_debugging_port(port)
    with sync_playwright() as playwright:
        emit({"type": "stage", "message": "Attaching the scanner to the full Chrome browser…"})
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0]

        def capture(request):
            url = urlsplit(request.url)
            if (
                url.hostname.removeprefix("www.") == urlsplit(job.gallery_url).hostname.removeprefix("www.")
                and url.path.rstrip("/") == "/api/3.0/medias/profile"
                and is_gallery_page(request.frame.page.url, job.gallery_url)
            ):
                completed.append(request)

        def collect():
            nonlocal final_page
            before = len(captured)
            while completed:
                response = completed.popleft().response()
                if response.status == 200:
                    data = response.json()
                    if "next_cursor" in data:
                        final_page = not data["next_cursor"]
                    for entry in data["media"]:
                        payload = entry[entry["type"]]
                        if payload["_id"] not in captured:
                            item = MediaItem.from_api(entry)
                            captured[item.media_id] = item
            while documents:
                document = documents.popleft()
                if is_gallery_page(document.url, job.gallery_url):
                    state = document.evaluate("() => window.__PRELOADED_STATE__?.medias?.byId ?? null")
                    if state is not None:
                        for media_id, entry in state.items():
                            if media_id not in captured:
                                item = MediaItem.from_preloaded(media_id, entry["media"])
                                captured[item.media_id] = item
            if len(captured) != before:
                emit({"type": "captured", "total": len(captured)})

        def observe(page):
            page.on("domcontentloaded", lambda: documents.append(page))
            page.on(
                "console",
                lambda message: emit({
                    "type": "browser_log",
                    "level": message.type,
                    "message": message.text,
                }) if message.type in {"warning", "error"} else None,
            )
            page.on(
                "requestfailed",
                lambda request: emit({
                    "type": "browser_log",
                    "level": "error",
                    "message": f"Request failed: {request.method} {request.url} — {request.failure}",
                }),
            )
            page.on(
                "response",
                lambda response: emit({
                    "type": "browser_log",
                    "level": "error",
                    "message": f"HTTP {response.status}: {response.url}",
                }) if response.status >= 400 else None,
            )

        context.on("requestfinished", capture)
        context.on("page", observe)
        for open_page in context.pages:
            observe(open_page)
        page = context.pages[0] if context.pages else context.new_page()
        emit({"type": "stage", "message": "Opening the gallery in Chromium…"})
        page.goto(job.gallery_url, wait_until="domcontentloaded", timeout=120000)
        emit(
            {
                "type": "manual",
                "message": (
                    "Log in or complete verification in the browser. When gallery images are visible, "
                    "start the full scan here. VSCODL2 will click Load more and scroll through the gallery."
                ),
            }
        )

        while not control.ready.is_set():
            page.wait_for_timeout(250)
            collect()

        if control.stopped.is_set():
            close_chrome(browser, chrome_process)
            emit({"type": "done", "stopped": True})
            return

        collect()
        completion = scroll_gallery(page, collect, captured, lambda: final_page, emit, control)
        if control.stopped.is_set():
            close_chrome(browser, chrome_process)
            emit({"type": "done", "stopped": True})
            return
        items = list(captured.values())
        job.scan_path.parent.mkdir(parents=True, exist_ok=True)
        job.scan_path.write_text(
            json.dumps(
                {"gallery_url": page.url, "items": [asdict(item) for item in items]},
                indent=2,
            ),
            encoding="utf-8",
        )
        close_chrome(browser, chrome_process)

    emit(
        {
            "type": "scanned",
            "gallery_url": job.gallery_url,
            "scan_path": str(job.scan_path),
            "items": [asdict(item) for item in items],
            "completion": completion,
        }
    )
    emit({"type": "done"})


def download_media(job, item_values, emit, control):
    items = [MediaItem.from_dict(values) for values in item_values]
    emit({"type": "progress", "current": 0, "total": len(items)})

    with requests.Session() as session:
        session.headers.update(
            {
                "User-Agent": f"VSCODL2/{__version__}",
                "Referer": job.gallery_url,
                "Accept-Encoding": "identity",
            }
        )
        for current, item in enumerate(items, 1):
            if control.stopped.is_set():
                break
            media_directory = "video" if item.media_type == "Video" else "photo"
            destination = job.download_path / media_directory / item.filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                emit(
                    {
                        "type": "downloaded",
                        "current": current,
                        "total": len(items),
                        "media_id": item.media_id,
                        "path": str(destination),
                        "skipped": True,
                    }
                )
                continue
            partial = destination.with_suffix(destination.suffix + ".part")
            with session.get(item.url, stream=True, timeout=120) as response:
                response.raise_for_status()
                with partial.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if control.stopped.is_set():
                            break
                        if chunk:
                            file.write(chunk)
            if control.stopped.is_set():
                break
            partial.replace(destination)
            emit(
                {
                    "type": "downloaded",
                    "current": current,
                    "total": len(items),
                    "media_id": item.media_id,
                    "path": str(destination),
                    "skipped": False,
                }
            )

    emit({"type": "done", "stopped": control.stopped.is_set()})
