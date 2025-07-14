import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QProgressBar
from PySide6.QtCore import Qt, QTimer, QTime, QThread, Signal
from PySide6.QtGui import QIcon
from utils import load_settings, save_settings
from styles import APP_STYLE
import yt_dlp

ICON_PATH = "app.ico"

class VideoInfoWorker(QThread):
    finished = Signal(object, str)  # info, error
    log = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': False,
                'extract_flat': False,
                'ignoreerrors': True,
                'verbose': True,
                'logger': YTDLSearchLogger(self.log.emit)
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    raise Exception("Не удалось получить информацию о видео")
                self.finished.emit(info, None)
        except Exception as e:
            self.finished.emit(None, str(e))

class YTDLSearchLogger:
    def __init__(self, log_callback):
        self.log_callback = log_callback
    def debug(self, msg):
        self.log_callback(f"[debug] {msg}")
    def warning(self, msg):
        self.log_callback(f"[warning] {msg}")
    def error(self, msg):
        self.log_callback(f"[error] {msg}")

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        size = self.settings.get('loading_dialog_size')
        if size:
            self.resize(size[0], size[1])
        self.setWindowTitle("Загрузка информации")
        self.setMinimumSize(400, 180)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        layout = QVBoxLayout(self)
        self.label = QLabel("Идет загрузка информации...")
        layout.addWidget(self.label)
        self.time_label = QLabel("Время поиска: 00:00")
        layout.addWidget(self.time_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(60)
        layout.addWidget(self.log_text)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        self._elapsed = QTime(0, 0, 0)
        self._timer.start(1000)

    def _update_time(self):
        self._elapsed = self._elapsed.addSecs(1)
        self.time_label.setText(f"Время поиска: {self._elapsed.toString('mm:ss')}")

    def append_log(self, text):
        self.log_text.append(text)

    def closeEvent(self, event):
        self.settings['loading_dialog_size'] = [self.size().width(), self.size().height()]
        save_settings(self.settings)
        self._timer.stop()
        super().closeEvent(event) 