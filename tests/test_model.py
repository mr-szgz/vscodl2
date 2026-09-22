from dataclasses import asdict

from PySide6.QtCore import Qt

from vscodl2.core import MediaItem
from vscodl2.model import MediaTableModel


def item(media_id, media_type):
    return MediaItem(
        media_id=media_id,
        media_type=media_type,
        url=f"https://media.test/{media_id}",
        filename=f"{media_id}.jpg",
        width=100,
        height=200,
        captured_at=1700000000000,
        description="Fixture",
    )


def test_media_model_is_read_only_and_returns_every_item(qtbot):
    model = MediaTableModel()
    model.replace([asdict(item("image", "Image")), asdict(item("video", "Video"))])

    assert model.rowCount() == 2
    assert model.columnCount() == 5
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Type"
    assert not model.flags(model.index(0, 0)) & Qt.ItemFlag.ItemIsEditable
    assert not model.flags(model.index(0, 0)) & Qt.ItemFlag.ItemIsUserCheckable
    assert [value["media_id"] for value in model.values()] == ["image", "video"]
