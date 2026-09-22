"""Qt model for captured VSCO media."""

from dataclasses import asdict

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from .core import MediaItem


class MediaTableModel(QAbstractTableModel):
    HEADERS = ("Type", "Media ID", "Dimensions", "Uploaded", "Description")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self.items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return (
                item.media_type,
                item.media_id,
                f"{item.width} × {item.height}",
                item.captured_text,
                item.description,
            )[index.column()]
        if role == Qt.ItemDataRole.ToolTipRole:
            return item.url
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() in (0, 2):
            return Qt.AlignmentFlag.AlignCenter
        return None

    def replace(self, values):
        self.beginResetModel()
        self.items = [MediaItem.from_dict(value) for value in values]
        self.endResetModel()

    def values(self):
        return [asdict(item) for item in self.items]
