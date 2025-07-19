import os
import subprocess
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from utils import load_settings, save_settings

ICON_PATH = "app.ico"


class YTDLLogger:
    def __init__(self, log_callback):
        self.log_callback = log_callback

    def debug(self, msg):
        if msg.startswith("[download]"):
            return
        if msg.startswith("[debug]"):
            if any(
                x in msg.lower()
                for x in [
                    "looking for embeds",
                    "formats sorted by",
                    "downloading format",
                ]
            ):
                return
            clean_msg = msg.replace("[debug]", "").strip()
            self.log_callback(f"Отладка: {clean_msg}", "debug")
        elif "[retry]" in msg.lower() or "retrying" in msg.lower():
            self.log_callback(f"Повторная попытка: {msg}", "warning")
        else:
            self.log_callback(msg, "info")

    def warning(self, msg):
        if "[generic]" in msg:
            clean_msg = msg.replace("[generic]", "").strip()
            if "Falling back on generic information extractor" in clean_msg:
                self.log_callback(
                    "Используем стандартный метод получения информации", "warning"
                )
            elif "Untested major version" in clean_msg:
                self.log_callback(
                    "Внимание: используется новая версия плеера", "warning"
                )
            else:
                self.log_callback(f"Предупреждение: {clean_msg}", "warning")
        else:
            self.log_callback(f"Предупреждение: {msg}", "warning")

    def error(self, msg):
        clean_msg = msg.replace("[error]", "").strip()
        self.log_callback(f"Ошибка: {clean_msg}", "error")


class DownloadWorker(QThread):
    progress = Signal(int, str, int, int)  # добавил downloaded_bytes, total_bytes
    finished = Signal(str)
    error = Signal(str)
    log = Signal(str, str)  # message, type
    file_downloaded = None  # Новый callback

    def __init__(self, url, save_path, format_id=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.format_id = format_id
        self._is_cancelled = False

    def run(self):
        try:
            ydl_opts = {
                "format": self.format_id if self.format_id else "best",
                "outtmpl": os.path.join(self.save_path, "%(title)s.%(ext)s"),
                "progress_hooks": [self._progress_hook],
                "logger": YTDLLogger(self.log.emit),
                "noprogress": False,
                "ignoreerrors": True,
                "no_warnings": False,
                "extract_flat": False,
                "quiet": False,
                "verbose": True,
                "nocheckcertificate": True,
                "geo_bypass": True,
                "geo_bypass_country": "RU",
                "socket_timeout": 30,
                "retries": 10,  # Добавлено: количество попыток
                "fragment_retries": 10,  # Для фрагментированных видео
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-us,en;q=0.5",
                    "Sec-Fetch-Mode": "navigate",
                },
            }
            import yt_dlp

            self.log.emit("Начинаем загрузку...", "info")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log.emit("Получаем информацию о видео...", "info")
                info = ydl.extract_info(self.url, download=False)
                if self._is_cancelled:
                    return
                if not info:
                    raise Exception("Не удалось получить информацию о видео")
                title = info.get("title", "Без названия")
                duration = info.get("duration", 0)
                duration_str = f"{duration // 60}:{duration % 60:02d}"
                self.log.emit(f"Название: {title}", "info")
                self.log.emit(f"Длительность: {duration_str}", "info")
                formats = info.get("formats", [])
                if formats:
                    self.log.emit(f"Доступно форматов: {len(formats)}", "info")
                    best_format = formats[0]
                    if "height" in best_format:
                        self.log.emit(
                            f"Лучшее качество: {best_format['height']}p", "info"
                        )
                self.log.emit("Начинаем скачивание...", "info")
                ydl.download([self.url])
                if self._is_cancelled:
                    return
            self.log.emit("Загрузка завершена успешно!", "success")
            self.finished.emit("Загрузка завершена успешно!")
        except Exception as e:
            if not self._is_cancelled:
                error_msg = str(e)
                self.log.emit(f"Ошибка: {error_msg}", "error")
                self.error.emit(error_msg)

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            try:
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                percent = int(downloaded / total * 100) if total else 0
                speed = d.get("speed")
                eta = d.get("eta")
                speed_str = f"{speed / 1024 / 1024:.2f} МБ/с" if speed else "N/A"
                eta_str = f"{eta // 60}:{eta % 60:02d}" if eta else "N/A"
                filename = d.get("filename", "").split("/")[-1]
                info = f"Файл: {filename}\nПрогресс: {percent}% | Скорость: {speed_str} | Осталось: {eta_str}"
                self.progress.emit(percent, info, downloaded, total or 0)
                if percent % 10 == 0:
                    self.log.emit(
                        f"Прогресс: {percent}% | Скорость: {speed_str} | Осталось: {eta_str}",
                        "info",
                    )
                if "filename" in d and self.file_downloaded:
                    self.file_downloaded(d["filename"])
            except Exception as e:
                self.log.emit(f"Ошибка при обновлении прогресса: {str(e)}", "error")
                self.log.emit(f"Данные прогресса: {d}", "debug")
        elif d["status"] == "finished":
            self.log.emit("Загрузка завершена, обрабатываем файл...", "info")

    def cancel(self):
        """Отменяет выполнение потока"""
        self._is_cancelled = True


class DownloadDialog(QDialog):
    def __init__(self, parent, url, save_path, selected_format):
        super().__init__(parent)
        self.settings = load_settings()
        size = self.settings.get("download_dialog_size")
        if size:
            self.resize(size[0], size[1])
        self.setWindowTitle("Загрузка видео")
        self.setMinimumSize(600, 320)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.url = url
        self.save_path = save_path
        self.selected_format = selected_format
        self.worker = None
        self.last_downloaded_file = None
        self.had_error = False  # Новый флаг
        self.setup_ui()
        self.start_download()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(300)
        layout.addWidget(self.progress_bar)
        self.size_label = QLabel("")
        layout.addWidget(self.size_label)
        self.progress_info = QLabel("")
        layout.addWidget(self.progress_info)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_text)
        self.open_folder_button = QPushButton("Открыть папку")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_folder)
        layout.addWidget(self.open_folder_button, alignment=Qt.AlignmentFlag.AlignRight)

    def start_download(self):
        format_id = (
            self.selected_format.get("format_id") if self.selected_format else None
        )
        self.worker = DownloadWorker(self.url, self.save_path, format_id)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)
        self.worker.log.connect(self.append_log)
        self.worker.file_downloaded = self.set_last_downloaded_file
        self.worker.start()

    def update_progress(self, value, info, downloaded_bytes=0, total_bytes=0):
        self.progress_bar.setValue(value)
        self.progress_info.setText(info)
        if total_bytes:
            if total_bytes > 1024**3:
                downloaded = downloaded_bytes / 1024**3
                total = total_bytes / 1024**3
                unit = "ГБ"
            else:
                downloaded = downloaded_bytes / 1024**2
                total = total_bytes / 1024**2
                unit = "МБ"
            self.size_label.setText(
                f"Скачано: {downloaded:.2f} {unit} из {total:.2f} {unit}"
            )
        else:
            self.size_label.setText("")

    def download_finished(self, message):
        if self.had_error:
            return  # Не показываем успех, если была ошибка
        # Проверяем, не был ли файл уже скачан
        if (
            "already been downloaded" in message.lower()
            or "already downloaded" in message.lower()
        ):
            self.progress_info.setText("Файл уже был скачан.")
            self.append_log("Файл уже был скачан.", "success")
        else:
            self.progress_info.setText(message)
            self.append_log(message, "success")
        self.open_folder_button.setEnabled(True)

    def download_error(self, error_message):
        self.had_error = True
        self.progress_info.setText(f"Ошибка: {error_message}")
        self.append_log(f"[ОШИБКА] {error_message}", "error")
        self.open_folder_button.setEnabled(True)

    def append_log(self, text, log_type="info"):
        if log_type == "success" and any(
            "успешно" in line.lower() or "уже был скачан" in line.lower()
            for line in self.log_text.toPlainText().splitlines()
        ):
            return
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if log_type == "error":
            color = QColor("#ef4444")
        elif log_type == "warning":
            color = QColor("#f59e0b")
        elif log_type == "success":
            color = QColor("#22c55e")
        elif log_type == "debug":
            color = QColor("#94a3b8")
        else:
            color = QColor("#e5e7eb")
        format = cursor.charFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        cursor.insertText(text + "\n")
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
        self.log_text.repaint()

    def set_last_downloaded_file(self, file_path):
        self.last_downloaded_file = file_path

    def open_folder(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            if sys.platform.startswith("win"):
                subprocess.run(
                    [
                        "explorer",
                        "/select,",
                        os.path.normpath(self.last_downloaded_file),
                    ]
                )
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", "-R", self.last_downloaded_file])
            else:
                subprocess.run(["xdg-open", os.path.dirname(self.last_downloaded_file)])
        elif os.path.exists(self.save_path):
            if sys.platform.startswith("win"):
                os.startfile(self.save_path)
            else:
                subprocess.run(["xdg-open", self.save_path])

    def closeEvent(self, event):
        # Завершаем поток загрузки, если он активен
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            if hasattr(self.worker, "cancel"):
                self.worker.cancel()
            self.worker.quit()
            self.worker.wait(3000)  # Ждем до 3 секунд
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(1000)

        self.settings["download_dialog_size"] = [
            self.size().width(),
            self.size().height(),
        ]
        save_settings(self.settings)
        super().closeEvent(event)
