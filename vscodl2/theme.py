"""Central semantic palette and generated application style sheet."""

from PySide6.QtCore import QObject, QTimer, Slot, Qt
from PySide6.QtGui import QColor, QFontDatabase, QPalette


LIGHT = {
    "window_background": "#f5f5f5",
    "canvas_background": "#ffffff",
    "surface_secondary": "#fafafa",
    "surface_tertiary": "#f0f0f0",
    "text_primary": "#242424",
    "text_secondary": "#616161",
    "text_disabled": "#a0a0a0",
    "border_primary": "#d1d1d1",
    "border_subtle": "#e5e5e5",
    "focus_border": "#005fb8",
    "brand_background": "#0f6cbd",
    "brand_hover": "#115ea3",
    "brand_pressed": "#0c3b5e",
    "brand_foreground": "#ffffff",
    "selection_background": "#e7f3ff",
    "success_background": "#f1faf1",
    "success_border": "#107c10",
    "warning_background": "#fff8e6",
    "warning_border": "#8a5d00",
    "danger_background": "#fdf3f4",
    "danger_border": "#c50f1f",
}

DARK = {
    "window_background": "#202020",
    "canvas_background": "#292929",
    "surface_secondary": "#242424",
    "surface_tertiary": "#333333",
    "text_primary": "#ffffff",
    "text_secondary": "#d6d6d6",
    "text_disabled": "#777777",
    "border_primary": "#5a5a5a",
    "border_subtle": "#3d3d3d",
    "focus_border": "#75b6e7",
    "brand_background": "#479ef5",
    "brand_hover": "#62abf5",
    "brand_pressed": "#2886de",
    "brand_foreground": "#0f1419",
    "selection_background": "#17324d",
    "success_background": "#183b1d",
    "success_border": "#54b054",
    "warning_background": "#45361d",
    "warning_border": "#f2c661",
    "danger_background": "#4a1f24",
    "danger_border": "#f1707b",
}


QSS = """
QWidget { color: @text_primary; background: transparent; font-size: 14px; }
QMainWindow { background: @window_background; }
QFrame[fluentRole="card"] {
    background: @canvas_background; border: 1px solid @border_subtle; border-radius: 8px;
}
QFrame[fluentRole="messageBar"] {
    background: @surface_tertiary; border: 1px solid @border_primary; border-radius: 6px;
}
QFrame[fluentRole="messageBar"][fluentSeverity="success"] {
    background: @success_background; border-color: @success_border;
}
QFrame[fluentRole="messageBar"][fluentSeverity="warning"] {
    background: @warning_background; border-color: @warning_border;
}
QFrame[fluentRole="messageBar"][fluentSeverity="danger"] {
    background: @danger_background; border-color: @danger_border;
}
QLabel#title { font-size: 28px; font-weight: 600; }
QLabel#sectionTitle { font-size: 16px; font-weight: 600; }
QLabel#subtitle, QLabel#secondary { color: @text_secondary; }
QLineEdit {
    background: @canvas_background; border: 1px solid @border_primary; border-radius: 6px;
    padding: 9px 11px; selection-background-color: @brand_background;
}
QLineEdit:hover { border-color: @text_secondary; }
QLineEdit:focus { border: 2px solid @focus_border; padding: 8px 10px; }
QLineEdit:disabled { color: @text_disabled; background: @surface_tertiary; }
QPushButton {
    background: @canvas_background; border: 1px solid @border_primary; border-radius: 6px;
    padding: 8px 14px; min-height: 20px;
}
QPushButton:hover { background: @surface_tertiary; }
QPushButton:pressed { background: @border_subtle; }
QPushButton:focus { border: 2px solid @focus_border; padding: 7px 13px; }
QPushButton:disabled { color: @text_disabled; background: @surface_tertiary; }
QPushButton[fluentAppearance="primary"] {
    color: @brand_foreground; background: @brand_background;
    border-color: @brand_background; font-weight: 600;
}
QPushButton[fluentAppearance="primary"]:hover {
    background: @brand_hover; border-color: @brand_hover;
}
QPushButton[fluentAppearance="primary"]:pressed {
    background: @brand_pressed; border-color: @brand_pressed;
}
QPushButton[fluentAppearance="subtle"] { background: transparent; border-color: transparent; }
QTableView {
    background: @canvas_background; alternate-background-color: @surface_secondary;
    border: 1px solid @border_subtle; border-radius: 6px; gridline-color: @border_subtle;
    selection-background-color: @selection_background; selection-color: @text_primary;
}
QTableView::item { padding: 7px; border-bottom: 1px solid @border_subtle; }
QTableView::item:hover { background: @surface_tertiary; }
QTableView::item:focus { border: 2px solid @focus_border; }
QHeaderView::section {
    background: @surface_secondary; border: 0; border-bottom: 1px solid @border_primary;
    padding: 8px; font-weight: 600;
}
QProgressBar {
    background: @surface_tertiary; border: 0; border-radius: 3px;
    min-height: 6px; max-height: 6px; text-align: center;
}
QProgressBar::chunk { background: @brand_background; border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: @border_primary; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class ThemeManager(QObject):
    def __init__(self, application):
        super().__init__(application)
        self.application = application
        application.styleHints().colorSchemeChanged.connect(self._schedule_apply)

    @Slot()
    def _schedule_apply(self):
        QTimer.singleShot(0, self.apply)

    @Slot()
    def apply(self):
        dark = self.application.styleHints().colorScheme() == Qt.ColorScheme.Dark
        tokens = DARK if dark else LIGHT
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(tokens["window_background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens["text_primary"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(tokens["canvas_background"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens["surface_secondary"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(tokens["text_primary"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(tokens["canvas_background"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens["text_primary"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens["brand_background"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens["brand_foreground"]))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(tokens["text_secondary"]))
        self.application.setPalette(palette)
        qss = QSS
        for name, value in tokens.items():
            qss = qss.replace("@" + name, value)
        self.application.setStyleSheet(qss)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        if font.pointSizeF() < 10:
            font.setPointSize(10)
        self.application.setFont(font)
