# VSCODL2

VSCODL2 is a Windows desktop application for scanning and downloading VSCO galleries. The interface is native Qt; the browser session is a visible Google Chrome window controlled by Playwright.

Complete site verification yourself before starting an automatic gallery scan.

## Files

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
