<img src="assets/Logo.png" alt="VSCODL2" style="max-width: 640px; width: 100%;">

# VSCODL2

VSCODL2 is a Windows desktop application for scanning and downloading VSCO galleries. The interface is native Qt; the browser session is a visible Google Chrome window controlled by Playwright.

Complete site verification yourself before starting an automatic gallery scan.

## Files

The download folder is configurable in the app and defaults to the system Downloads folder:

```text
Downloads/VSCODL2/
  <username>/
    photo/
    video/
```

Settings, browser profile data, scan manifests, and logs are stored below the system user configuration folder returned by `platformdirs.user_config_path("VSCODL2", appauthor=False)`:

```text
VSCODL2/
  settings.json
  browser-profile/
  scans/
  browser-console.log
  last-error.log
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
