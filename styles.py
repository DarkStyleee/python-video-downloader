APP_STYLE = """
QWidget {
    font-size: 16px;
    background: #181a20;
    color: #e5e7eb;
}
QLineEdit, QTextEdit {
    background: #23272f;
    border-radius: 10px;
    padding: 10px;
    color: #e5e7eb;
    border: 1px solid #23272f;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1.5px solid #3b82f6;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #06b6d4);
    color: white;
    border-radius: 10px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 16px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #0ea5e9);
}
QPushButton:disabled {
    background: #334155;
    color: #94a3b8;
}
QProgressBar {
    border-radius: 10px;
    background: #23272f;
    height: 28px;
    text-align: center;
    font-size: 16px;
    color: #22d3ee;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22d3ee, stop:1 #3b82f6);
    border-radius: 10px;
}
QLabel#TitleLabel {
    font-size: 28px;
    font-weight: bold;
    color: #22d3ee;
    margin-bottom: 18px;
    letter-spacing: 1px;
}
QLabel#StatusLabel {
    color: #a3e635;
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 8px;
}
QLabel#ErrorLabel {
    color: #ef4444;
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 8px;
}
QTextEdit {
    font-family: 'Consolas', monospace;
    background: #181a20;
    border: 1.5px solid #23272f;
    border-radius: 10px;
    padding: 10px;
    font-size: 15px;
    color: #e5e7eb;
}
""" 