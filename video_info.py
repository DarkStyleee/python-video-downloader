import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QTextEdit, QScrollArea,
                             QWidget, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import yt_dlp
from utils import load_settings, save_settings

ICON_PATH = "app.ico"

class YTDLSearchLogger:
    def __init__(self, log_callback):
        self.log_callback = log_callback
    def debug(self, msg):
        self.log_callback(f"[debug] {msg}")
    def warning(self, msg):
        self.log_callback(f"[warning] {msg}")
    def error(self, msg):
        self.log_callback(f"[error] {msg}")

class VideoInfoDialog(QDialog):
    format_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        size = self.settings.get('video_info_size')
        if size:
            self.resize(size[0], size[1])
        self.setWindowTitle("Информация о видео")
        self.setMinimumSize(600, 400)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Основная информация
        self.info_label = QLabel("Загрузка информации...")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Форматы
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(300)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Детальная информация
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)

        # Кнопки
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Скачать выбранный формат")
        self.download_button.clicked.connect(self.accept_selection)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def load_video_info(self, url, log_callback=None):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': False,
                'extract_flat': False,
                'ignoreerrors': True,
                'verbose': True,
            }
            if log_callback:
                ydl_opts['logger'] = YTDLSearchLogger(log_callback)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Не удалось получить информацию о видео")
                
                # Основная информация
                title = info.get('title', 'Без названия')
                duration = info.get('duration', 0)
                duration_str = f"{duration // 60}:{duration % 60:02d}"
                
                self.info_label.setText(f"Название: {title}\nДлительность: {duration_str}")
                
                # Форматы
                formats = info.get('formats', [])
                if not formats:
                    raise Exception("Не найдены доступные форматы")
                
                self.format_combo.clear()
                
                # Сортируем форматы по качеству
                formats.sort(key=lambda x: (
                    x.get('height', 0) or 0,
                    x.get('filesize', 0) or 0
                ), reverse=True)
                
                # Убираем дублирующиеся форматы
                seen = set()
                unique_formats = []
                for f in formats:
                    height = f.get('height', 0)
                    resolution = f.get('resolution', '')
                    ext = f.get('ext', '').upper()
                    filesize = f.get('filesize', 0)
                    filesize_mb = round(filesize / (1024 * 1024), 1) if filesize else 0
                    key = (height, resolution, ext, filesize_mb)
                    if key in seen:
                        continue
                    seen.add(key)
                    unique_formats.append(f)
                
                for f in unique_formats:
                    format_id = f.get('format_id', '')
                    ext = f.get('ext', '')
                    resolution = f.get('resolution', '')
                    height = f.get('height', 0)
                    filesize = f.get('filesize', 0)
                    filesize_mb = filesize / (1024 * 1024) if filesize else 0
                    format_desc = []
                    if height:
                        format_desc.append(f"{height}p")
                    if resolution:
                        format_desc.append(resolution)
                    format_desc.append(ext.upper())
                    if filesize_mb:
                        format_desc.append(f"{filesize_mb:.1f}MB")
                    format_str = " | ".join(format_desc)
                    self.format_combo.addItem(format_str, f)
                
                # Детальная информация
                details = []
                details.append(f"Заголовок: {title}")
                details.append(f"Длительность: {duration_str}")
                details.append(f"Автор: {info.get('uploader', 'Неизвестно')}")
                details.append(f"Просмотры: {info.get('view_count', 'Неизвестно')}")
                details.append(f"Доступно форматов: {len(unique_formats)}")
                
                # Добавляем информацию о качестве
                if unique_formats:
                    best_format = unique_formats[0]
                    details.append(f"\nЛучшее качество: {best_format.get('height', '?')}p")
                    if best_format.get('filesize'):
                        details.append(f"Размер: {best_format['filesize'] / (1024*1024):.1f}MB")
                
                self.details_text.setText("\n".join(details))
                
                return True
        except Exception as e:
            error_msg = str(e)
            self.info_label.setText(f"Ошибка при загрузке информации: {error_msg}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить информацию о видео:\n{error_msg}")
            return False

    def load_video_info_from_info(self, info):
        try:
            if not info:
                raise Exception("Не удалось получить информацию о видео")
            # Основная информация
            title = info.get('title', 'Без названия')
            duration = info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            self.info_label.setText(f"Название: {title}\nДлительность: {duration_str}")
            # Форматы
            formats = info.get('formats', [])
            if not formats:
                raise Exception("Не найдены доступные форматы")
            self.format_combo.clear()
            formats.sort(key=lambda x: (
                x.get('height', 0) or 0,
                x.get('filesize', 0) or 0
            ), reverse=True)
            seen = set()
            unique_formats = []
            for f in formats:
                height = f.get('height', 0)
                resolution = f.get('resolution', '')
                ext = f.get('ext', '').upper()
                filesize = f.get('filesize', 0)
                filesize_mb = round(filesize / (1024 * 1024), 1) if filesize else 0
                key = (height, resolution, ext, filesize_mb)
                if key in seen:
                    continue
                seen.add(key)
                unique_formats.append(f)
            for f in unique_formats:
                format_id = f.get('format_id', '')
                ext = f.get('ext', '')
                resolution = f.get('resolution', '')
                height = f.get('height', 0)
                filesize = f.get('filesize', 0)
                filesize_mb = filesize / (1024 * 1024) if filesize else 0
                format_desc = []
                if height:
                    format_desc.append(f"{height}p")
                if resolution:
                    format_desc.append(resolution)
                format_desc.append(ext.upper())
                if filesize_mb:
                    format_desc.append(f"{filesize_mb:.1f}MB")
                format_str = " | ".join(format_desc)
                self.format_combo.addItem(format_str, f)
            details = []
            details.append(f"Заголовок: {title}")
            details.append(f"Длительность: {duration_str}")
            details.append(f"Автор: {info.get('uploader', 'Неизвестно')}")
            details.append(f"Просмотры: {info.get('view_count', 'Неизвестно')}")
            details.append(f"Доступно форматов: {len(unique_formats)}")
            if unique_formats:
                best_format = unique_formats[0]
                details.append(f"\nЛучшее качество: {best_format.get('height', '?')}p")
                if best_format.get('filesize'):
                    details.append(f"Размер: {best_format['filesize'] / (1024*1024):.1f}MB")
            self.details_text.setText("\n".join(details))
            return True
        except Exception as e:
            error_msg = str(e)
            self.info_label.setText(f"Ошибка при загрузке информации: {error_msg}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить информацию о видео:\n{error_msg}")
            return False

    def accept_selection(self):
        current_format = self.format_combo.currentData()
        if current_format:
            self.format_selected.emit(current_format)
            self.accept()

    def closeEvent(self, event):
        self.settings['video_info_size'] = [self.size().width(), self.size().height()]
        save_settings(self.settings)
        super().closeEvent(event) 