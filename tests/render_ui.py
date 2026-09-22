"""Render the VSCODL2 window with local fixture data for visual review."""

import sys

from PySide6.QtWidgets import QApplication

from vscodl2.app import MainWindow
from vscodl2.theme import ThemeManager


app = QApplication([])
theme = ThemeManager(app)
theme.apply()
window = MainWindow()
window.handle_event(
    {
        "type": "scanned",
        "scan_path": "data/scans/-evalee.json",
        "items": [
            {
                "media_id": f"fixture-{number:02d}",
                "media_type": "Video" if number == 3 else "Image",
                "url": f"https://media.test/fixture-{number:02d}.jpg",
                "preview_url": f"https://media.test/fixture-{number:02d}.jpg",
                "filename": f"fixture-{number:02d}.jpg",
                "width": 2048,
                "height": 1365,
                "captured_at": 1700000000000 + number * 1000,
                "description": f"Captured gallery item {number}",
            }
            for number in range(1, 7)
        ],
    }
)
window.show()
app.processEvents()
window.grab().save(sys.argv[1])
