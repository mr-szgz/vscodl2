# VSCODL2

VSCODL2 is a Windows desktop application for scanning and downloading VSCO galleries. The interface is native Qt; the browser session is a visible Google Chrome window controlled by Playwright.

Complete site verification yourself before starting an automatic gallery scan:

1. Paste a gallery URL.
2. Choose **Open browser session**.
3. In Chrome, log in or complete any verification VSCO requests until gallery images appear.
4. Return to VSCODL2 and choose **Start full gallery scan**. The app clicks **Load more** and scrolls automatically. It pauses for recognized verification screens and can be cancelled.
5. Choose **Download all** to save every captured image and video.

VSCODL2 starts the installed `chrome.exe` directly with its own persistent profile at `./data/browser-profile`, then attaches Playwright over Chrome DevTools for observation and post-confirmation scrolling. Chrome owns its native user agent, headers, network stack, JavaScript engine, service workers, cache, sandbox, extensions UI, and rendering. Login and verification state are created only through that visible browser and retained by Chrome. The app does not import cookies, use another browser profile, override headers, route requests, abort requests, block ads, disable JavaScript, or bypass verification. Before confirmation it only opens the requested URL and observes the page; it does not click or scroll.

## Original quality and scanning

Images use the original asset URL, including VSCO's region-specific image origin where its URL identifies one. Image sizing, cropping, format conversion, and compression parameters are removed; unrelated query parameters are retained unchanged. Downloads are not resized or upscaled. An upload below 1920×1080 remains below Full HD; larger uploads retain their source resolution. Videos use the direct video URL supplied by the media record, not the preview image.

New downloads use an `_original` filename suffix so an existing preview from an older version does not prevent downloading the original. Existing `_original` files are skipped.

The scanner collects initial `window.__PRELOADED_STATE__` media and completed gallery API responses from the selected profile. It deduplicates by media ID before parsing repeated entries and processes responses outside browser event callbacks. After confirmation it clicks **Load more** and scrolls every 1.5 seconds, stopping when VSCO reports no next cursor. If no media arrives for 30 seconds, it stops with an explicit notice that gallery completeness is unconfirmed. It does not bypass verification or replay API requests.

Browser warnings, failed requests, and HTTP errors appear in the diagnostics panel and are saved to `./data/browser-console.log`. If the worker fails, its full traceback appears there and is also saved to `./data/last-error.log`.

Reviewed implementations: [michabirklbauer/vsco_downloader](https://github.com/michabirklbauer/vsco_downloader) for preloaded media URLs and [NickJGG/vsco-downloader](https://github.com/NickJGG/vsco-downloader) for response collection and ID deduplication. VSCO's image-origin URL patterns were cross-checked against [gallery-dl's VSCO extractor](https://github.com/mikf/gallery-dl/blob/master/gallery_dl/extractor/vsco.py). The implementation here is independently written.

Browser profile data, scan manifests, and downloads are stored below `./data`:

```text
data/
  browser-profile/
  scans/
  <username>/
    photo/
    video/
```

## Run from source

```powershell
uv sync --extra test
uv run vscodl2
```

Google Chrome must be installed.

## Test

```powershell
uv run pytest -q
```

Tests use local fixtures and never contact VSCO.

The optional `uv run pytest -m browser` test opens installed Google Chrome against a local fixture to exercise navigation, image loading, API capture, and persistent browser state. It is excluded from the default suite.
