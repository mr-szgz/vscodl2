# Changelog

All notable changes to VSCODL2 are documented in this file.

## [2.2.3] - 2026-09-22

### Added

- Added a download-folder selector that defaults to the system Downloads directory and persists the selected location.
- Added `platformdirs` for platform-appropriate user configuration and download paths.

### Changed

- Store settings, browser profile data, scan manifests, and logs in the per-user VSCODL2 configuration directory instead of the working directory.
- Store only downloaded photos and videos in the configured download directory.
- Display and persist VSCO upload timestamps without requiring the optional capture-date field.

### Fixed

- Include the application logo from its current `assets` location in Windows builds.

[2.2.3]: https://github.com/mr-szgz/vscodl2/compare/v2.2.2...v2.2.3
