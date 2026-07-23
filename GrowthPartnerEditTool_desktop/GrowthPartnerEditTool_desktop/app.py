"""
Growth Partner Edit Tool — Desktop App
UI matching the web editor design.
"""
import sys
import os
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTextEdit, QComboBox,
    QProgressBar, QFrame, QStackedWidget, QLineEdit, QScrollArea,
    QSizePolicy, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QUrl, QSize
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent, QPainter, QBrush, QPen, QLinearGradient

STYLESHEET = """
* { box-sizing: border-box; }

QMainWindow, QWidget#root {
    background-color: #080810;
}

QWidget {
    background-color: transparent;
    color: #f0eeff;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}

/* Sidebar */
QWidget#sidebar {
    background-color: rgba(255,255,255,0.02);
    border-right: 1px solid rgba(255,255,255,0.06);
}

QLabel#logo_main {
    font-size: 15px;
    font-weight: 800;
    color: #f0eeff;
}

QPushButton#nav_btn {
    background: transparent;
    border: none;
    color: #8b82a8;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    border-radius: 8px;
    font-weight: 500;
}
QPushButton#nav_btn:hover {
    background: rgba(255,255,255,0.04);
    color: #f0eeff;
}
QPushButton#nav_btn[active=true] {
    background: rgba(155,48,255,0.15);
    color: #c984ff;
}

/* Cards */
QFrame#card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
}

QFrame#card_purple {
    background: rgba(155,48,255,0.08);
    border: 1px solid rgba(155,48,255,0.3);
    border-radius: 14px;
}

QFrame#card_purple[selected=true] {
    background: rgba(155,48,255,0.12);
    border: 1.5px solid rgba(155,48,255,0.6);
}

QFrame#upload_zone {
    background: rgba(155,48,255,0.03);
    border: 1.5px dashed rgba(155,48,255,0.25);
    border-radius: 16px;
}

QFrame#upload_zone:hover {
    background: rgba(155,48,255,0.06);
    border-color: rgba(155,48,255,0.5);
}

QFrame#file_selected {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}

/* Buttons */
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7b2fe0, stop:1 #c040ff);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 14px 28px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #8b3ff0, stop:1 #d050ff);
}
QPushButton#primary:disabled {
    background: rgba(255,255,255,0.06);
    color: #4a4460;
}

QPushButton#secondary {
    background: rgba(255,255,255,0.04);
    color: #f0eeff;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#secondary:hover {
    border-color: rgba(155,48,255,0.4);
    background: rgba(155,48,255,0.06);
}

QPushButton#icon_btn {
    background: transparent;
    border: none;
    color: #4a4460;
    font-size: 16px;
    padding: 4px 6px;
    border-radius: 4px;
}
QPushButton#icon_btn:hover { color: #8b82a8; }

/* Inputs */
QTextEdit#prompt_input {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    color: #f0eeff;
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.6;
    selection-background-color: rgba(155,48,255,0.4);
}
QTextEdit#prompt_input:focus {
    border-color: rgba(155,48,255,0.4);
}

QLineEdit#input_field {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    color: #f0eeff;
    padding: 9px 14px;
    font-size: 13px;
}
QLineEdit#input_field:focus {
    border-color: rgba(155,48,255,0.4);
}

QComboBox {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    color: #f0eeff;
    padding: 8px 12px;
    font-size: 13px;
}
QComboBox:hover { border-color: rgba(155,48,255,0.3); }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #1a1a2e;
    border: 1px solid rgba(155,48,255,0.3);
    color: #f0eeff;
    selection-background-color: rgba(155,48,255,0.25);
    outline: none;
}

/* Progress */
QProgressBar {
    background: rgba(255,255,255,0.06);
    border: none;
    border-radius: 4px;
    height: 4px;
    text-align: center;
    font-size: 0px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7b2fe0, stop:1 #c040ff);
    border-radius: 4px;
}

/* Log */
QTextEdit#log_output {
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    color: #8b82a8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
}

/* Labels */
QLabel#section_label {
    font-size: 11px;
    font-weight: 600;
    color: #8b82a8;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

QLabel#status_ok { color: #22c55e; font-size: 12px; }
QLabel#status_err { color: #ef4444; font-size: 12px; }

/* Scrollbar */
QScrollBar:vertical { background: transparent; width: 5px; margin: 0; }
QScrollBar::handle:vertical { background: rgba(155,48,255,0.3); border-radius: 3px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 0; }
"""


class DropZone(QFrame):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("upload_zone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("↑")
        icon.setStyleSheet("""
            font-size: 28px; color: #c984ff;
            background: rgba(155,48,255,0.1);
            border: 1px solid rgba(155,48,255,0.2);
            border-radius: 12px;
            padding: 10px 14px;
        """)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(52, 52)

        title = QLabel("Drag your video here or click to select")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f0eeff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("MP4 · MOV · AVI · MKV · No size limit")
        subtitle.setStyleSheet("font-size: 12px; color: #8b82a8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video",
            "", "Video (*.mp4 *.mov *.mkv *.avi *.webm *.flv);;All (*)"
        )
        if path:
            self.fileDropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.styleSheet().replace(
                "rgba(155,48,255,0.25)", "rgba(155,48,255,0.6)"
            ))

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet())

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            self.fileDropped.emit(urls[0].toLocalFile())


class ContentTypeCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, emoji: str, title: str, subtitle: str, key: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("card_purple")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)
        self.setMinimumWidth(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.emoji_lbl = QLabel(emoji)
        self.emoji_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        self.emoji_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #f0eeff; background: transparent;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("font-size: 10px; color: #8b82a8; background: transparent; line-height: 1.4;")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_lbl.setWordWrap(True)

        layout.addWidget(self.emoji_lbl)
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.sub_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit(self.key)

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class ProcessWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(dict)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        import asyncio
        from core.processor import process_video

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(process_video(
            video_path=self.params["video_path"],
            prompt=self.params["prompt"],
            output_dir=self.params["output_dir"],
            content_type=self.params["content_type"],
            quality=self.params["quality"],
            progress=lambda msg, pct: self.progress.emit(msg, pct),
        ))
        loop.close()
        self.finished.emit(result)


class ResultItem(QFrame):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("file_selected")
        self.info = info

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        icon = QLabel("🎬")
        icon.setStyleSheet("font-size: 20px; background: rgba(155,48,255,0.1); border-radius: 8px; padding: 6px 8px;")
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        name = QLabel(info["label"])
        name.setStyleSheet("font-size: 13px; font-weight: 600; color: #f0eeff;")
        dur = QLabel(f"{int(info['duration'])}s  ·  {Path(info['path']).name}")
        dur.setStyleSheet("font-size: 11px; color: #8b82a8;")
        text_col.addWidget(name)
        text_col.addWidget(dur)
        layout.addLayout(text_col)
        layout.addStretch()

        open_btn = QPushButton("▶  Play")
        open_btn.setObjectName("secondary")
        open_btn.setFixedWidth(80)
        open_btn.clicked.connect(self._open)
        layout.addWidget(open_btn)

        folder_btn = QPushButton("📁")
        folder_btn.setObjectName("icon_btn")
        folder_btn.setFixedWidth(32)
        folder_btn.clicked.connect(self._folder)
        layout.addWidget(folder_btn)

    def _open(self):
        p = self.info["path"]
        if sys.platform == "win32":
            os.startfile(p)
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", p])

    def _folder(self):
        p = str(Path(self.info["path"]).parent)
        if sys.platform == "win32":
            subprocess.run(["explorer", p])
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", p])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growth Partner Edit Tool")
        self.setMinimumSize(960, 640)
        self.resize(1160, 760)
        self.setStyleSheet(STYLESHEET)

        self.settings = _load_settings()
        self._init_clients()
        self.worker = None
        self.video_path = ""
        self.output_dir = ""
        self.content_type = "video"
        self.ct_cards = {}

        self._build_ui()

    def _init_clients(self):
        from core.processor import init_clients
        init_clients(
            self.settings.get("gemini_key", os.environ.get("GEMINI_API_KEY", "")),
            self.settings.get("anthropic_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        )

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(16, 24, 16, 20)
        sb.setSpacing(2)

        logo = QLabel("Growth Partner\n<span style='color:#c040ff'>Edit Tool</span>")
        logo.setTextFormat(Qt.TextFormat.RichText)
        logo.setObjectName("logo_main")
        logo.setContentsMargins(4, 0, 0, 20)
        sb.addWidget(logo)

        self.nav_edit = self._nav_btn("✦  Edit Video", "edit")
        self.nav_settings = self._nav_btn("⚙  Settings", "settings")
        sb.addWidget(self.nav_edit)
        sb.addWidget(self.nav_settings)
        sb.addStretch()

        has_key = bool(self.settings.get("gemini_key"))
        self.api_status = QLabel("● Gemini ready" if has_key else "● No API key")
        self.api_status.setObjectName("status_ok" if has_key else "status_err")
        sb.addWidget(self.api_status)

        main.addWidget(sidebar)

        # ── Pages ─────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_editor())
        self.stack.addWidget(self._build_settings())
        main.addWidget(self.stack)

        self._nav("edit")

    def _nav_btn(self, label, key):
        btn = QPushButton(label)
        btn.setObjectName("nav_btn")
        btn.setProperty("active", False)
        btn.clicked.connect(lambda: self._nav(key))
        return btn

    def _nav(self, key):
        pages = {"edit": 0, "settings": 1}
        for btn, k in [(self.nav_edit, "edit"), (self.nav_settings, "settings")]:
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.stack.setCurrentIndex(pages[key])

    # ── Editor ────────────────────────────────────────────────────────────

    def _build_editor(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(32, 28, 24, 28)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Left: inputs ──────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(16)
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Edit Video")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #f0eeff;")
        left.addWidget(title)

        # Content type cards
        ct_label = QLabel("CONTENT TYPE")
        ct_label.setObjectName("section_label")
        left.addWidget(ct_label)

        ct_row = QHBoxLayout()
        ct_row.setSpacing(10)
        types = [
            ("✂️", "Short Clip", "Under 10 min\nEffects, format", "short_clip"),
            ("🎬", "Video", "10 min – few hours\nBest moments, splits", "video"),
            ("🎮", "Stream", "Long VOD\nHighlights, clips", "stream"),
        ]
        for emoji, t, sub, key in types:
            card = ContentTypeCard(emoji, t, sub, key)
            card.clicked.connect(self._select_ct)
            self.ct_cards[key] = card
            ct_row.addWidget(card)
        left.addLayout(ct_row)
        self._select_ct("video")

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.fileDropped.connect(self._file_selected)
        left.addWidget(self.drop_zone)

        # File selected indicator (hidden by default)
        self.file_card = QFrame()
        self.file_card.setObjectName("file_selected")
        self.file_card.setVisible(False)
        fc_layout = QHBoxLayout(self.file_card)
        fc_layout.setContentsMargins(14, 12, 14, 12)

        fc_icon = QLabel("🎬")
        fc_icon.setStyleSheet("font-size: 22px;")
        fc_layout.addWidget(fc_icon)

        fc_text = QVBoxLayout()
        self.fc_name = QLabel()
        self.fc_name.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.fc_size = QLabel()
        self.fc_size.setStyleSheet("font-size: 11px; color: #8b82a8;")
        fc_text.addWidget(self.fc_name)
        fc_text.addWidget(self.fc_size)
        fc_layout.addLayout(fc_text)
        fc_layout.addStretch()

        fc_clear = QPushButton("✕")
        fc_clear.setObjectName("icon_btn")
        fc_clear.clicked.connect(self._clear_file)
        fc_layout.addWidget(fc_clear)
        left.addWidget(self.file_card)

        # Prompt
        prompt_card = QFrame()
        prompt_card.setObjectName("card")
        pc_layout = QVBoxLayout(prompt_card)
        pc_layout.setContentsMargins(18, 16, 18, 16)
        pc_layout.setSpacing(10)

        pl = QLabel("INSTRUCTIONS FOR AI")
        pl.setObjectName("section_label")
        pc_layout.addWidget(pl)

        self.prompt_input = QTextEdit()
        self.prompt_input.setObjectName("prompt_input")
        self.prompt_input.setPlaceholderText(
            "Tell AI what to do with your video...\n\n"
            "e.g. Find the 3 funniest moments from this stream\n"
            "or: Add captions and convert to vertical format"
        )
        self.prompt_input.setMinimumHeight(110)
        self.prompt_input.setMaximumHeight(160)
        pc_layout.addWidget(self.prompt_input)

        left.addWidget(prompt_card)

        # Options
        opts_card = QFrame()
        opts_card.setObjectName("card")
        oc_layout = QHBoxLayout(opts_card)
        oc_layout.setContentsMargins(18, 14, 18, 14)
        oc_layout.setSpacing(16)

        for label, items, attr in [
            ("OUTPUT FORMAT", ["MP4 (H.264)", "MP4 (H.265)", "MOV", "WebM"], "fmt_combo"),
            ("EXPORT QUALITY", ["1080p HD", "720p", "4K"], "qual_combo"),
        ]:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("section_label")
            combo = QComboBox()
            combo.addItems(items)
            col.addWidget(lbl)
            col.addWidget(combo)
            oc_layout.addLayout(col)
            setattr(self, attr, combo)

        left.addWidget(opts_card)

        # Output folder
        out_row = QHBoxLayout()
        out_label = QLabel("OUTPUT FOLDER")
        out_label.setObjectName("section_label")
        left.addWidget(out_label)

        self.out_display = QLineEdit()
        self.out_display.setObjectName("input_field")
        self.out_display.setPlaceholderText("Select output folder...")
        self.out_display.setReadOnly(True)
        out_btn = QPushButton("Browse")
        out_btn.setObjectName("secondary")
        out_btn.setFixedWidth(80)
        out_btn.clicked.connect(self._pick_output)
        out_row.addWidget(self.out_display)
        out_row.addWidget(out_btn)
        left.addLayout(out_row)

        # Start button
        self.start_btn = QPushButton("✦  Start Editing")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self._start)
        left.addWidget(self.start_btn)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setMinimumWidth(420)
        layout.addWidget(left_w, stretch=5)

        # ── Right: progress + results ─────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(14)
        right.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Progress card
        prog_card = QFrame()
        prog_card.setObjectName("card")
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setContentsMargins(18, 16, 18, 16)
        prog_layout.setSpacing(10)

        prog_title = QLabel("PROGRESS")
        prog_title.setObjectName("section_label")
        prog_layout.addWidget(prog_title)

        self.status_label = QLabel("Ready to process")
        self.status_label.setStyleSheet("color: #8b82a8; font-size: 13px;")
        self.status_label.setWordWrap(True)
        prog_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        prog_layout.addWidget(self.progress_bar)

        right.addWidget(prog_card)

        # Log
        log_title = QLabel("LOG")
        log_title.setObjectName("section_label")
        right.addWidget(log_title)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("log_output")
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(180)
        right.addWidget(self.log_output)

        # Results
        res_title = QLabel("OUTPUT FILES")
        res_title.setObjectName("section_label")
        right.addWidget(res_title)

        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.results_area.setMinimumHeight(120)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(8)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        no_files = QLabel("No clips yet — start processing to see results here")
        no_files.setStyleSheet("color: #4a4460; font-size: 12px; padding: 20px;")
        no_files.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_files_label = no_files
        self.results_layout.addWidget(no_files)

        self.results_area.setWidget(self.results_container)
        right.addWidget(self.results_area)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setMinimumWidth(360)
        layout.addWidget(right_w, stretch=4)

        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page

    # ── Settings ──────────────────────────────────────────────────────────

    def _build_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #f0eeff;")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(14)

        for label, attr, placeholder, hint, url, url_text in [
            ("GEMINI API KEY", "s_gemini", "AIza...",
             "Get your free key at", "https://aistudio.google.com/app/apikey", "aistudio.google.com"),
            ("ANTHROPIC API KEY", "s_anthropic", "sk-ant-...",
             "Get your key at", "https://console.anthropic.com", "console.anthropic.com"),
        ]:
            lbl = QLabel(label)
            lbl.setObjectName("section_label")
            cl.addWidget(lbl)

            inp = QLineEdit()
            inp.setObjectName("input_field")
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setPlaceholderText(placeholder)
            inp.setText(self.settings.get(attr.replace("s_", "") + "_key", ""))
            cl.addWidget(inp)
            setattr(self, attr, inp)

            hint_lbl = QLabel(f'{hint} <a href="{url}" style="color:#9b30ff">{url_text}</a>')
            hint_lbl.setOpenExternalLinks(True)
            hint_lbl.setStyleSheet("color: #8b82a8; font-size: 12px;")
            cl.addWidget(hint_lbl)
            cl.addSpacing(4)

        save_btn = QPushButton("Save API Keys")
        save_btn.setObjectName("primary")
        save_btn.setMaximumWidth(200)
        save_btn.clicked.connect(self._save_settings)
        cl.addWidget(save_btn)

        layout.addWidget(card)
        return page

    def _save_settings(self):
        self.settings["gemini_key"] = self.s_gemini.text().strip()
        self.settings["anthropic_key"] = self.s_anthropic.text().strip()
        _save_settings(self.settings)
        self._init_clients()
        has_key = bool(self.settings.get("gemini_key"))
        self.api_status.setText("● Gemini ready" if has_key else "● No API key")
        self.api_status.setObjectName("status_ok" if has_key else "status_err")
        self.api_status.style().unpolish(self.api_status)
        self.api_status.style().polish(self.api_status)
        QMessageBox.information(self, "Saved", "API keys saved.")

    # ── Actions ───────────────────────────────────────────────────────────

    def _select_ct(self, key: str):
        self.content_type = key
        for k, card in self.ct_cards.items():
            card.set_selected(k == key)

    def _file_selected(self, path: str):
        self.video_path = path
        size_mb = Path(path).stat().st_size / (1024 * 1024)
        self.fc_name.setText(Path(path).name)
        self.fc_size.setText(f"{size_mb:.1f} MB")
        self.drop_zone.setVisible(False)
        self.file_card.setVisible(True)
        if not self.output_dir:
            self.output_dir = str(Path(path).parent / "gpe_output")
            self.out_display.setText(self.output_dir)

    def _clear_file(self):
        self.video_path = ""
        self.drop_zone.setVisible(True)
        self.file_card.setVisible(False)

    def _pick_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_dir = path
            self.out_display.setText(path)

    def _start(self):
        if not self.video_path:
            QMessageBox.warning(self, "No Video", "Please select a video file first.")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "No Output Folder", "Please select an output folder.")
            return
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "No Instructions", "Please describe what you want to do.")
            return

        quality_map = {"1080p HD": "1080p", "720p": "720p", "4K": "4k"}

        self._clear_results()
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Processing...")

        self.worker = ProcessWorker({
            "video_path": self.video_path,
            "prompt": prompt,
            "output_dir": self.output_dir,
            "content_type": self.content_type,
            "quality": quality_map.get(self.qual_combo.currentText(), "1080p"),
        })
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
            n = len(result["files"])
            self.status_label.setText(f"Done! {n} clip{'s' if n != 1 else ''} ready.")
            self._clear_results()
            for info in result["files"]:
                self.results_layout.addWidget(ResultItem(info))
        else:
            self.status_label.setText(f"Error: {result.get('error', 'Unknown error')}")
            self.log_output.append(f"\n✗ {result.get('error', '')}")

    def _clear_results(self):
        for i in reversed(range(self.results_layout.count())):
            w = self.results_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        if hasattr(self, "no_files_label"):
            self.no_files_label = None


# ── Settings persistence ──────────────────────────────────────────────────

def _settings_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "GrowthPartnerEditTool" / "settings.json"


def _load_settings():
    p = _settings_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def _save_settings(settings):
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings, indent=2))


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Growth Partner Edit Tool")

    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
