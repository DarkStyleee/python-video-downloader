import sys
import os
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLineEdit, QPushButton, QLabel,
                            QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QDragEnterEvent, QDropEvent
import yt_dlp

from utils import load_settings, save_settings
from styles import APP_STYLE
from downloader import DownloadDialog
from video_info import VideoInfoDialog
from loading import LoadingDialog, VideoInfoWorker

ICON_PATH = "app.ico"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Видео Загрузчик")
        self.setMinimumSize(600, 220)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.settings = load_settings()
        size = self.settings.get('main_window_size')
        if size:
            self.resize(size[0], size[1])
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(18)
        layout.setContentsMargins(32, 32, 32, 32)

        self.title_label = QLabel("Видео Загрузчик")
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте ссылку на видео")
        url_layout.addWidget(self.url_input, stretch=2)
        self.info_button = QPushButton("Найти")
        self.info_button.clicked.connect(self.show_video_info)
        url_layout.addWidget(self.info_button)
        layout.addLayout(url_layout)

        folder_layout = QHBoxLayout()
        self.folder_button = QPushButton("Папка…")
        self.folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_button)
        self.folder_label = QLabel("")
        self.folder_label.setObjectName("StatusLabel")
        folder_layout.addWidget(self.folder_label)
        folder_layout.addStretch(1)
        layout.addLayout(folder_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

        self.save_path = self.settings.get('save_path', os.path.expanduser("~/Downloads"))
        self.selected_format = None
        self.worker = None
        self.setStyleSheet(APP_STYLE)
        self.update_folder_label()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения", self.save_path)
        if folder:
            self.save_path = folder
            self.settings['save_path'] = folder
            save_settings(self.settings)
            self.update_folder_label()

    def update_folder_label(self):
        self.folder_label.setText(f"Папка сохранения: {self.save_path}")

    def show_video_info(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите URL видео")
            return
        self.info_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.info_button.setText("Поиск...")
        QApplication.processEvents()
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.append_log("Запрос к YouTube...")
        self.loading_dialog.show()
        QApplication.processEvents()
        self.worker = VideoInfoWorker(url)
        self.worker.log.connect(self.loading_dialog.append_log)
        self.worker.finished.connect(self.on_video_info_ready)
        self.worker.start()

    def on_video_info_ready(self, info, error):
        self.loading_dialog.close()
        self.info_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.info_button.setText("Найти")
        if error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить информацию о видео:\n{error}")
            return
        dialog = VideoInfoDialog(self)
        dialog.load_video_info_from_info(info)
        dialog.format_selected.connect(self.on_format_selected)
        dialog.exec()

    def on_format_selected(self, format_info):
        self.selected_format = format_info
        self.open_download_dialog()

    def open_download_dialog(self):
        dialog = DownloadDialog(self, self.url_input.text().strip(), self.save_path, self.selected_format)
        dialog.exec()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                self.url_input.setText(urls[0].toString())
        elif event.mimeData().hasText():
            self.url_input.setText(event.mimeData().text())

    def closeEvent(self, event):
        self.settings['main_window_size'] = [self.size().width(), self.size().height()]
        save_settings(self.settings)
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 