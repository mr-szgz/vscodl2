"""Qt desktop interface for VSCODL2."""

import json
from pathlib import Path
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from platformdirs import user_config_path, user_downloads_path

from .core import gallery_name
from .model import MediaTableModel
from .theme import ThemeManager


def set_fluent_property(widget, name, value):
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_dir = user_config_path("VSCODL2", appauthor=False, ensure_exists=True)
        self.settings_path = self.config_dir / "settings.json"
        if self.settings_path.is_file():
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.download_dir = Path(settings["download_directory"])
        else:
            self.download_dir = user_downloads_path() / "VSCODL2"
            self.save_settings()
        self.worker = QProcess(self)
        self.worker.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.worker.readyReadStandardOutput.connect(self._read_stdout)
        self.worker.readyReadStandardError.connect(self._read_stderr)
        self.worker.finished.connect(self._worker_finished)
        self.stdout_buffer = ""
        self.stderr_buffer = ""
        self.operation = None

        self.setWindowTitle("VSCODL2")
        self.resize(1180, 760)
        self.setMinimumSize(820, 560)
        logo = Path(__file__).resolve().parents[1] / "Logo.png"
        if logo.is_file():
            self.setWindowIcon(QIcon(str(logo)))

        self.model = MediaTableModel(self)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("VSCODL2")
        title.setObjectName("title")
        subtitle = QLabel("User-controlled Google Chrome scanning for VSCO galleries")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        session_card = QFrame()
        session_card.setProperty("fluentRole", "card")
        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(18, 16, 18, 16)
        session_layout.setSpacing(12)
        step = QLabel("1  Open a persistent browser session")
        step.setObjectName("sectionTitle")
        session_layout.addWidget(step)

        source_row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setAccessibleName("VSCO gallery URL")
        self.url.setPlaceholderText("https://vsco.co/username/gallery")
        self.url.returnPressed.connect(self.open_browser)
        self.open_button = QPushButton("Open browser session")
        self.open_button.setAccessibleDescription(
            "Open Google Chrome with the saved VSCODL2 browser session"
        )
        self.open_button.clicked.connect(self.open_browser)
        set_fluent_property(self.open_button, "fluentAppearance", "primary")
        source_row.addWidget(self.url, 1)
        source_row.addWidget(self.open_button)
        session_layout.addLayout(source_row)

        download_row = QHBoxLayout()
        download_label = QLabel("Download folder")
        self.download_directory = QLineEdit(str(self.download_dir))
        self.download_directory.setReadOnly(True)
        self.download_directory.setAccessibleName("Download folder")
        self.download_directory.setAccessibleDescription(
            "Folder where downloaded VSCO galleries are saved"
        )
        download_label.setBuddy(self.download_directory)
        self.browse_downloads_button = QPushButton("Browse…")
        self.browse_downloads_button.setAccessibleDescription(
            "Choose the folder where downloaded VSCO galleries are saved"
        )
        self.browse_downloads_button.clicked.connect(self.choose_download_directory)
        download_row.addWidget(download_label)
        download_row.addWidget(self.download_directory, 1)
        download_row.addWidget(self.browse_downloads_button)
        session_layout.addLayout(download_row)

        self.message_bar = QFrame()
        self.message_bar.setProperty("fluentRole", "messageBar")
        message_layout = QHBoxLayout(self.message_bar)
        message_layout.setContentsMargins(12, 10, 12, 10)
        self.message = QLabel(
            "Open the browser, complete login or verification, then start scanning. The scan clicks Load more and scrolls automatically."
        )
        self.message.setWordWrap(True)
        self.message.setAccessibleName("Application status")
        message_layout.addWidget(self.message, 1)
        session_layout.addWidget(self.message_bar)

        self.error_details = QPlainTextEdit()
        self.error_details.setReadOnly(True)
        self.error_details.setAccessibleName("Browser and application diagnostics")
        self.error_details.setMaximumHeight(self.fontMetrics().lineSpacing() * 8)
        self.error_details.hide()
        session_layout.addWidget(self.error_details)
        self.copy_error_button = QPushButton("Copy diagnostics")
        self.copy_error_button.clicked.connect(
            lambda: QApplication.clipboard().setText(self.error_details.toPlainText())
        )
        self.copy_error_button.hide()
        session_layout.addWidget(self.copy_error_button)

        confirm_row = QHBoxLayout()
        self.captured_label = QLabel("No active browser session")
        self.captured_label.setObjectName("secondary")
        self.confirm_button = QPushButton("Start full gallery scan")
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.confirm_gallery)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_operation)
        set_fluent_property(self.cancel_button, "fluentAppearance", "subtle")
        confirm_row.addWidget(self.captured_label, 1)
        confirm_row.addWidget(self.cancel_button)
        confirm_row.addWidget(self.confirm_button)
        session_layout.addLayout(confirm_row)
        layout.addWidget(session_card)

        results_header = QHBoxLayout()
        self.results_title = QLabel("2  Captured media")
        self.results_title.setObjectName("sectionTitle")
        self.result_count = QLabel("0 items")
        self.result_count.setObjectName("secondary")
        results_header.addWidget(self.results_title)
        results_header.addWidget(self.result_count)
        results_header.addStretch()
        layout.addLayout(results_header)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 150)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setAccessibleName("Captured gallery media")
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setAccessibleName("Download progress")
        self.download_button = QPushButton("Download all")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download_all)
        set_fluent_property(self.download_button, "fluentAppearance", "primary")
        self.open_downloads_button = QPushButton("Open downloads")
        self.open_downloads_button.clicked.connect(self.open_downloads)
        footer.addWidget(self.progress, 1)
        footer.addWidget(self.open_downloads_button)
        footer.addWidget(self.download_button)
        layout.addLayout(footer)

        self.setCentralWidget(root)
        QWidget.setTabOrder(self.url, self.open_button)
        QWidget.setTabOrder(self.open_button, self.download_directory)
        QWidget.setTabOrder(self.download_directory, self.browse_downloads_button)
        QWidget.setTabOrder(self.browse_downloads_button, self.confirm_button)
        QWidget.setTabOrder(self.confirm_button, self.cancel_button)
        QWidget.setTabOrder(self.cancel_button, self.table)
        QWidget.setTabOrder(self.table, self.download_button)
        QWidget.setTabOrder(self.download_button, self.open_downloads_button)

    def job(self):
        return {
            "gallery_url": self.url.text().strip(),
            "config_dir": str(self.config_dir),
            "download_dir": str(self.download_dir),
        }

    def save_settings(self):
        self.settings_path.write_text(
            json.dumps({"download_directory": str(self.download_dir)}, indent=2) + "\n",
            encoding="utf-8",
        )

    def choose_download_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Choose download folder",
            str(self.download_dir),
        )
        if directory:
            self.download_dir = Path(directory)
            self.download_directory.setText(directory)
            self.save_settings()

    def start_worker(self, request):
        self.stdout_buffer = ""
        self.stderr_buffer = ""
        self.error_details.clear()
        self.error_details.hide()
        self.copy_error_button.hide()
        if request["operation"] == "scan":
            (self.config_dir / "browser-console.log").write_text("", encoding="utf-8")
        if getattr(sys, "frozen", False):
            self.worker.setProgram(str(Path(sys.executable).with_name("VSCODL2-worker.exe")))
            self.worker.setArguments([])
        else:
            self.worker.setProgram(sys.executable)
            self.worker.setArguments(["-m", "vscodl2.worker"])
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        environment.insert("PYTHONIOENCODING", "utf-8")
        self.worker.setProcessEnvironment(environment)
        self.worker.start()
        self.worker.waitForStarted()
        self.worker.write((json.dumps(request) + "\n").encode())

    def open_browser(self):
        self.operation = "scan"
        self.download_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.url.setEnabled(False)
        self.download_directory.setEnabled(False)
        self.browse_downloads_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.confirm_button.setEnabled(False)
        self.set_status("Opening Google Chrome and navigating to the gallery…", "info")
        self.captured_label.setText("Waiting for browser")
        self.start_worker({"operation": "scan", "job": self.job(), "items": None})

    def confirm_gallery(self):
        self.confirm_button.setEnabled(False)
        self.set_status("Scanning the gallery automatically…", "info")
        self.worker.write(b"resume\n")

    def download_all(self):
        items = self.model.values()
        self.operation = "download"
        self.download_button.setEnabled(False)
        self.table.setEnabled(False)
        self.open_button.setEnabled(False)
        self.download_directory.setEnabled(False)
        self.browse_downloads_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, len(items))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.set_status(f"Downloading all {len(items)} items…", "info")
        self.start_worker({"operation": "download", "job": self.job(), "items": items})

    def cancel_operation(self):
        self.cancel_button.setEnabled(False)
        self.worker.write(b"stop\n")
        self.set_status("Stopping the active operation…", "warning")

    def _read_stdout(self):
        self.stdout_buffer += bytes(self.worker.readAllStandardOutput()).decode("utf-8")
        lines = self.stdout_buffer.split("\n")
        self.stdout_buffer = lines.pop()
        for line in lines:
            if line:
                self.handle_event(json.loads(line))

    def _read_stderr(self):
        self.stderr_buffer += bytes(self.worker.readAllStandardError()).decode("utf-8")

    def handle_event(self, event):
        event_type = event["type"]
        if event_type == "stage":
            self.captured_label.setText(event["message"])
            self.set_status(event["message"], "info")
        elif event_type == "manual":
            self.confirm_button.setEnabled(True)
            self.captured_label.setText("Browser session active")
            self.set_status(event["message"], "warning")
        elif event_type == "browser_log":
            entry = f"[{event['level'].upper()}] {event['message']}"
            self.error_details.appendPlainText(entry)
            self.error_details.show()
            self.copy_error_button.show()
            with (self.config_dir / "browser-console.log").open("a", encoding="utf-8") as log:
                log.write(entry + "\n")
            if event["level"] == "error":
                self.set_status(entry, "danger")
        elif event_type == "captured":
            self.captured_label.setText(f"{event['total']} media items captured from loaded gallery pages")
        elif event_type == "scanned":
            self.model.replace(event["items"])
            count = len(event["items"])
            self.result_count.setText(f"{count} items")
            self.download_button.setEnabled(bool(count))
            self.set_status(f"Scan complete: {count} items saved to {event['scan_path']}", "success")
            if "completion" in event:
                self.set_status(f"{count} items captured. {event['completion']}", "info")
        elif event_type == "progress":
            self.progress.setRange(0, event["total"])
            self.progress.setValue(event["current"])
        elif event_type == "downloaded":
            self.progress.setValue(event["current"])
            action = "Already present" if event["skipped"] else "Saved"
            self.set_status(f"{action}: {event['path']}", "success")
        elif event_type == "done" and self.operation == "download":
            self.set_status(f"Downloads complete: {self.download_path()}", "success")

    def _worker_finished(self, exit_code, _exit_status):
        self._read_stdout()
        self._read_stderr()
        self.confirm_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.open_button.setEnabled(True)
        self.url.setEnabled(True)
        self.download_directory.setEnabled(True)
        self.browse_downloads_button.setEnabled(True)
        self.table.setEnabled(True)
        if exit_code:
            self.error_details.setPlainText(self.stderr_buffer)
            self.error_details.show()
            self.copy_error_button.show()
            log_path = self.config_dir / "last-error.log"
            log_path.write_text(self.stderr_buffer, encoding="utf-8")
            self.set_status(f"Operation failed (exit {exit_code}). Full error below; saved to {log_path}", "danger")
            self.captured_label.setText("Operation stopped")
        self.operation = None
        self.download_button.setEnabled(bool(self.model.items))

    def set_status(self, text, severity):
        self.message.setText(text)
        self.message.setAccessibleDescription(text)
        set_fluent_property(self.message_bar, "fluentSeverity", severity)

    def download_path(self):
        return self.download_dir / gallery_name(self.url.text().strip())

    def open_downloads(self):
        path = self.download_path()
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event):
        if self.worker.state() != QProcess.ProcessState.NotRunning:
            self.worker.write(b"stop\n")
            self.worker.waitForFinished(3000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VSCODL2")
    app.setOrganizationName("VSCODL2")
    theme = ThemeManager(app)
    theme.apply()
    window = MainWindow()
    window.show()
    return app.exec()
