"""
Growth Partner Edit Tool — Desktop App
PyQt6 UI matching the web dark/purple design.
"""
import sys
import os
import asyncio
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTextEdit, QComboBox,
    QProgressBar, QFrame, QStackedWidget, QLineEdit, QScrollArea,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QLinearGradient, QGradient,
    QPixmap, QPainter, QBrush, QPen, QIcon
)

# ── Color palette (matches index.html) ───────────────────────────────────

COLORS = {
    "bg":           "#080810",
    "white":        "#f0eeff",
    "purple":       "#9b30ff",
    "purple_mid":   "#7b2fe0",
    "purple_dark":  "#4a0fa3",
    "purple_wrap":  "#c040ff",
    "gray_400":     "#8b82a8",
    "gray_600":     "#4a4460",
    "glass_bg":     "rgba(255,255,255,0.04)",
    "glass_border": "rgba(255,255,255,0.09)",
    "success":      "#22c55e",
    "error":        "#ef4444",
}

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #080810;
    color: #f0eeff;
    font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
}

/* Cards / glass panels */
QFrame#card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
}

QFrame#card_purple {
    background: rgba(155,48,255,0.08);
    border: 1px solid rgba(155,48,255,0.3);
    border-radius: 16px;
}

/* Buttons */
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #9b30ff, stop:1 #c040ff);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 28px;
    font-size: 14px;
    font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #a840ff, stop:1 #d050ff);
}
QPushButton#primary:disabled {
    background: #4a4460;
    color: #8b82a8;
}

QPushButton#secondary {
    background: rgba(255,255,255,0.04);
    color: #f0eeff;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 13px;
}
QPushButton#secondary:hover {
    border-color: rgba(155,48,255,0.4);
    background: rgba(155,48,255,0.06);
}

QPushButton#icon_btn {
    background: transparent;
    border: none;
    color: #8b82a8;
    font-size: 18px;
    padding: 4px 8px;
    border-radius: 6px;
}
QPushButton#icon_btn:hover { color: #f0eeff; background: rgba(255,255,255,0.06); }

/* Inputs */
QTextEdit, QLineEdit {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    color: #f0eeff;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: rgba(155,48,255,0.4);
}
QTextEdit:focus, QLineEdit:focus {
    border-color: rgba(155,48,255,0.5);
    background: rgba(155,48,255,0.05);
}

QComboBox {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    color: #f0eeff;
    padding: 10px 14px;
    font-size: 13px;
    min-width: 140px;
}
QComboBox:hover { border-color: rgba(155,48,255,0.4); }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView {
    background: #1a1a2e;
    border: 1px solid rgba(155,48,255,0.3);
    color: #f0eeff;
    selection-background-color: rgba(155,48,255,0.3);
}

/* Progress bar */
QProgressBar {
    background: rgba(255,255,255,0.06);
    border: none;
    border-radius: 6px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #9b30ff, stop:1 #c040ff);
    border-radius: 6px;
}

/* Log area */
QTextEdit#log {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    color: #8b82a8;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    padding: 10px;
}

/* Scrollbar */
QScrollBar:vertical {
    background: transparent; width: 6px;
}
QScrollBar::handle:vertical {
    background: rgba(155,48,255,0.4); border-radius: 3px; min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QLabel#section_title {
    font-size: 11px;
    font-weight: 600;
    color: #8b82a8;
    letter-spacing: 1.5px;
}

QLabel#logo {
    font-size: 16px;
    font-weight: 800;
    color: #f0eeff;
}

QLabel#status_ok { color: #22c55e; font-size: 12px; }
QLabel#status_err { color: #ef4444; font-size: 12px; }
"""


# ── Worker thread for processing ──────────────────────────────────────────

class ProcessWorker(QThread):
    progress = pyqtSignal(str, int)   # message, percent
    finished = pyqtSignal(dict)       # result dict

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self):
        import asyncio
        from core.processor import process_video

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def on_progress(msg, pct):
            self.progress.emit(msg, pct)

        result = loop.run_until_complete(process_video(
            video_path=self.params["video_path"],
            prompt=self.params["prompt"],
            output_dir=self.params["output_dir"],
            content_type=self.params["content_type"],
            quality=self.params["quality"],
            progress=on_progress,
        ))
        loop.close()
        self.finished.emit(result)


# ── Settings dialog ───────────────────────────────────────────────────────

class SettingsDialog(QWidget):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Settings")
        self.setFixedSize(480, 360)
        self.setStyleSheet(STYLESHEET)
        self.settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("API Keys")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #f0eeff;")
        layout.addWidget(title)

        sub = QLabel("Required for Gemini video analysis and Claude clip selection.")
        sub.setStyleSheet("color: #8b82a8; font-size: 13px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        layout.addSpacing(8)

        # Gemini key
        gem_label = QLabel("GEMINI API KEY")
        gem_label.setObjectName("section_title")
        layout.addWidget(gem_label)
        self.gemini_input = QLineEdit()
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("AIza...")
        self.gemini_input.setText(settings.get("gemini_key", ""))
        layout.addWidget(self.gemini_input)

        # Anthropic key
        ant_label = QLabel("ANTHROPIC API KEY (optional)")
        ant_label.setObjectName("section_title")
        layout.addWidget(ant_label)
        self.anthropic_input = QLineEdit()
        self.anthropic_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_input.setPlaceholderText("sk-ant-...")
        self.anthropic_input.setText(settings.get("anthropic_key", ""))
        layout.addWidget(self.anthropic_input)

        layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _save(self):
        self.settings["gemini_key"] = self.gemini_input.text().strip()
        self.settings["anthropic_key"] = self.anthropic_input.text().strip()
        _save_settings(self.settings)
        self.close()


# ── Result panel ──────────────────────────────────────────────────────────

class ResultCard(QFrame):
    def __init__(self, file_info: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.file_info = file_info

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)

        left = QVBoxLayout()
        name = QLabel(file_info["label"])
        name.setStyleSheet("color: #f0eeff; font-size: 14px; font-weight: 600;")
        dur = QLabel(f"{int(file_info['duration'])}s  ·  {Path(file_info['path']).name}")
        dur.setStyleSheet("color: #8b82a8; font-size: 12px;")
        left.addWidget(name)
        left.addWidget(dur)

        layout.addLayout(left)
        layout.addStretch()

        open_btn = QPushButton("▶  Open")
        open_btn.setObjectName("secondary")
        open_btn.setFixedWidth(90)
        open_btn.clicked.connect(self._open)
        layout.addWidget(open_btn)

        folder_btn = QPushButton("📁")
        folder_btn.setObjectName("icon_btn")
        folder_btn.setFixedWidth(36)
        folder_btn.setToolTip("Show in folder")
        folder_btn.clicked.connect(self._show_in_folder)
        layout.addWidget(folder_btn)

    def _open(self):
        path = self.file_info["path"]
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def _show_in_folder(self):
        path = Path(self.file_info["path"]).parent
        if sys.platform == "win32":
            subprocess.run(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])


# ── Main window ───────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growth Partner Edit Tool")
        self.setMinimumSize(900, 680)
        self.resize(1100, 740)
        self.setStyleSheet(STYLESHEET)

        self.settings = _load_settings()
        self._init_clients()
        self.worker = None
        self.video_path = ""
        self.output_dir = ""

        self._build_ui()

    def _init_clients(self):
        from core.processor import init_clients
        init_clients(
            self.settings.get("gemini_key", os.environ.get("GEMINI_API_KEY", "")),
            self.settings.get("anthropic_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        )

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.02);
                border-right: 1px solid rgba(255,255,255,0.06);
            }
        """)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(20, 24, 20, 20)
        sb_layout.setSpacing(4)

        # Logo
        logo = QLabel("Growth Partner\n<span style='color:#c040ff'>Edit Tool</span>")
        logo.setTextFormat(Qt.TextFormat.RichText)
        logo.setStyleSheet("font-size: 15px; font-weight: 800; color: #f0eeff; border: none; background: transparent;")
        logo.setContentsMargins(0, 0, 0, 16)
        sb_layout.addWidget(logo)

        # Nav items
        nav_items = [
            ("✦  Edit Video", "edit"),
            ("⚙  Settings", "settings"),
        ]
        self.nav_btns = {}
        for label, key in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("secondary")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #8b82a8;
                    text-align: left;
                    padding: 10px 12px;
                    font-size: 13px;
                    border-radius: 8px;
                }
                QPushButton:hover { background: rgba(255,255,255,0.04); color: #f0eeff; }
                QPushButton:checked { background: rgba(155,48,255,0.15); color: #c984ff; }
            """)
            btn.clicked.connect(lambda checked, k=key: self._nav(k))
            sb_layout.addWidget(btn)
            self.nav_btns[key] = btn

        sb_layout.addStretch()

        # API status indicator
        self.api_status = QLabel("● Gemini connected" if self.settings.get("gemini_key") else "● No API key")
        self.api_status.setObjectName("status_ok" if self.settings.get("gemini_key") else "status_err")
        sb_layout.addWidget(self.api_status)

        root.addWidget(sidebar)

        # ── Main content (stacked) ────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_edit_page())   # index 0
        self.stack.addWidget(self._build_settings_page())  # index 1
        root.addWidget(self.stack)

        self._nav("edit")

    def _nav(self, key: str):
        pages = {"edit": 0, "settings": 1}
        for k, btn in self.nav_btns.items():
            btn.setChecked(k == key)
        self.stack.setCurrentIndex(pages.get(key, 0))

    # ── Edit page ─────────────────────────────────────────────────────────

    def _build_edit_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("Edit Video")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #f0eeff;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Two-column layout
        cols = QHBoxLayout()
        cols.setSpacing(16)

        # ── Left column: inputs ───────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(14)

        # Video file picker
        file_label = QLabel("VIDEO FILE")
        file_label.setObjectName("section_title")
        left.addWidget(file_label)

        file_row = QHBoxLayout()
        self.file_display = QLineEdit()
        self.file_display.setPlaceholderText("Select video file...")
        self.file_display.setReadOnly(True)
        file_row.addWidget(self.file_display)

        pick_btn = QPushButton("Browse")
        pick_btn.setObjectName("secondary")
        pick_btn.setFixedWidth(80)
        pick_btn.clicked.connect(self._pick_file)
        file_row.addWidget(pick_btn)
        left.addLayout(file_row)

        # Output folder
        out_label = QLabel("OUTPUT FOLDER")
        out_label.setObjectName("section_title")
        left.addWidget(out_label)

        out_row = QHBoxLayout()
        self.out_display = QLineEdit()
        self.out_display.setPlaceholderText("Select output folder...")
        self.out_display.setReadOnly(True)
        out_row.addWidget(self.out_display)

        out_btn = QPushButton("Browse")
        out_btn.setObjectName("secondary")
        out_btn.setFixedWidth(80)
        out_btn.clicked.connect(self._pick_output)
        out_row.addWidget(out_btn)
        left.addLayout(out_row)

        # Prompt
        prompt_label = QLabel("WHAT DO YOU WANT?")
        prompt_label.setObjectName("section_title")
        left.addWidget(prompt_label)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "e.g. Find the 3 funniest moments from this stream\n"
            "or: Add captions and convert to vertical format\n"
            "or: Split into 5 equal parts"
        )
        self.prompt_input.setFixedHeight(100)
        left.addWidget(self.prompt_input)

        # Options row
        opts_label = QLabel("OPTIONS")
        opts_label.setObjectName("section_title")
        left.addWidget(opts_label)

        opts_row = QHBoxLayout()
        opts_row.setSpacing(10)

        type_combo = QComboBox()
        type_combo.addItems(["Short Clip", "Video", "Stream"])
        type_combo.setToolTip("Content type")
        self.content_type_combo = type_combo
        opts_row.addWidget(type_combo)

        qual_combo = QComboBox()
        qual_combo.addItems(["720p", "1080p", "4K"])
        qual_combo.setCurrentIndex(1)
        self.quality_combo = qual_combo
        opts_row.addWidget(qual_combo)

        left.addLayout(opts_row)

        # Start button
        self.start_btn = QPushButton("✦  Start Editing")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.start_btn.clicked.connect(self._start)
        left.addWidget(self.start_btn)

        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        cols.addWidget(left_widget, stretch=4)

        # ── Right column: progress + results ─────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(14)

        # Progress card
        prog_card = QFrame()
        prog_card.setObjectName("card")
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setContentsMargins(18, 16, 18, 16)
        prog_layout.setSpacing(10)

        prog_title = QLabel("PROGRESS")
        prog_title.setObjectName("section_title")
        prog_layout.addWidget(prog_title)

        self.status_label = QLabel("Ready to process")
        self.status_label.setStyleSheet("color: #8b82a8; font-size: 13px;")
        self.status_label.setWordWrap(True)
        prog_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        prog_layout.addWidget(self.progress_bar)

        right.addWidget(prog_card)

        # Log
        log_label = QLabel("LOG")
        log_label.setObjectName("section_title")
        right.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("log")
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(160)
        right.addWidget(self.log_output)

        # Results
        results_label = QLabel("OUTPUT FILES")
        results_label.setObjectName("section_title")
        right.addWidget(results_label)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(8)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.addStretch()

        self.results_scroll.setWidget(self.results_container)
        right.addWidget(self.results_scroll, stretch=1)

        right_widget = QWidget()
        right_widget.setLayout(right)
        cols.addWidget(right_widget, stretch=5)

        layout.addLayout(cols)
        return page

    # ── Settings page ─────────────────────────────────────────────────────

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #f0eeff;")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        # Gemini key
        gem_label = QLabel("GEMINI API KEY")
        gem_label.setObjectName("section_title")
        card_layout.addWidget(gem_label)
        self.settings_gemini = QLineEdit()
        self.settings_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.settings_gemini.setPlaceholderText("AIza...")
        self.settings_gemini.setText(self.settings.get("gemini_key", ""))
        card_layout.addWidget(self.settings_gemini)

        gem_hint = QLabel("Get your key at <a href='https://aistudio.google.com/app/apikey' style='color:#9b30ff'>aistudio.google.com</a>")
        gem_hint.setOpenExternalLinks(True)
        gem_hint.setStyleSheet("color: #8b82a8; font-size: 12px;")
        card_layout.addWidget(gem_hint)

        card_layout.addSpacing(8)

        # Anthropic key
        ant_label = QLabel("ANTHROPIC API KEY")
        ant_label.setObjectName("section_title")
        card_layout.addWidget(ant_label)
        self.settings_anthropic = QLineEdit()
        self.settings_anthropic.setEchoMode(QLineEdit.EchoMode.Password)
        self.settings_anthropic.setPlaceholderText("sk-ant-...")
        self.settings_anthropic.setText(self.settings.get("anthropic_key", ""))
        card_layout.addWidget(self.settings_anthropic)

        ant_hint = QLabel("Get your key at <a href='https://console.anthropic.com' style='color:#9b30ff'>console.anthropic.com</a>")
        ant_hint.setOpenExternalLinks(True)
        ant_hint.setStyleSheet("color: #8b82a8; font-size: 12px;")
        card_layout.addWidget(ant_hint)

        card_layout.addSpacing(8)

        save_btn = QPushButton("Save API Keys")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_settings)
        card_layout.addWidget(save_btn)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _save_settings(self):
        self.settings["gemini_key"] = self.settings_gemini.text().strip()
        self.settings["anthropic_key"] = self.settings_anthropic.text().strip()
        _save_settings(self.settings)
        self._init_clients()

        has_key = bool(self.settings.get("gemini_key"))
        self.api_status.setText("● Gemini connected" if has_key else "● No API key")
        self.api_status.setObjectName("status_ok" if has_key else "status_err")
        self.api_status.setStyleSheet("")
        self.api_status.style().unpolish(self.api_status)
        self.api_status.style().polish(self.api_status)

        QMessageBox.information(self, "Saved", "API keys saved successfully.")

    # ── File pickers ──────────────────────────────────────────────────────

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm *.flv);;All Files (*)"
        )
        if path:
            self.video_path = path
            self.file_display.setText(path)
            # Auto-set output dir next to video
            if not self.output_dir:
                self.output_dir = str(Path(path).parent / "gpe_output")
                self.out_display.setText(self.output_dir)

    def _pick_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_dir = path
            self.out_display.setText(path)

    # ── Processing ────────────────────────────────────────────────────────

    def _start(self):
        if not self.video_path:
            QMessageBox.warning(self, "No Video", "Please select a video file first.")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "No Output", "Please select an output folder.")
            return
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "No Prompt", "Please describe what you want to do.")
            return
        if not self.settings.get("gemini_key"):
            reply = QMessageBox.question(
                self, "No API Key",
                "No Gemini API key set. Video analysis will be limited.\nContinue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        content_map = {"Short Clip": "short_clip", "Video": "video", "Stream": "stream"}
        quality_map = {"720p": "720p", "1080p": "1080p", "4K": "4k"}

        params = {
            "video_path": self.video_path,
            "prompt": prompt,
            "output_dir": self.output_dir,
            "content_type": content_map[self.content_type_combo.currentText()],
            "quality": quality_map[self.quality_combo.currentText()],
        }

        # Clear results
        for i in reversed(range(self.results_layout.count())):
            w = self.results_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.results_layout.addStretch()

        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Processing...")

        self.worker = ProcessWorker(params)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, msg: str, pct: int):
        self.status_label.setText(msg)
        self.log_output.append(f"→ {msg}")
        if pct >= 0:
            self.progress_bar.setValue(pct)

    def _on_finished(self, result: dict):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("✦  Start Editing")

        if result["success"]:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Done! {len(result['files'])} clip(s) created.")
            self.log_output.append(f"\n✓ {result.get('description', 'Processing complete')}")

            # Show result cards
            for i in reversed(range(self.results_layout.count())):
                w = self.results_layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

            for file_info in result["files"]:
                card = ResultCard(file_info)
                self.results_layout.insertWidget(0, card)
        else:
            self.status_label.setText(f"Error: {result.get('error', 'Unknown error')}")
            self.log_output.append(f"\n✗ Error: {result.get('error', '')}")
            self.progress_bar.setValue(0)


# ── Settings persistence ──────────────────────────────────────────────────

def _settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "GrowthPartnerEditTool" / "settings.json"


def _load_settings() -> dict:
    path = _settings_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save_settings(settings: dict):
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2))


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Growth Partner Edit Tool")
    app.setApplicationVersion("1.0.0")

    # Load .env if present (for development)
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
