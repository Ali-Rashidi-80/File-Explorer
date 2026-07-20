"""
File Explorer to Clean TXT/JSON Generator with Reverse Functionality
نسخه 5.1 — پولیش نهایی: امنیت مسیر، چرخه عمر ترد، پارس درخت، سقف حافظه
"""

import json
import os
import re
import sys
import warnings
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, Signal
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QStyle,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# =====================================================================
# ثابت‌ها و helperهای خالص (قابل تست بدون GUI)
# =====================================================================
KNOWN_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".rtf",
    ".csv",
    ".log",
    ".ini",
    ".cfg",
    ".conf",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".svg",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".mjs",
    ".cjs",
    ".py",
    ".pyw",
    ".pyx",
    ".pxd",
    ".pxi",
    ".ipynb",
    ".c",
    ".cpp",
    ".cxx",
    ".cc",
    ".h",
    ".hpp",
    ".hxx",
    ".cs",
    ".fs",
    ".vb",
    ".java",
    ".kt",
    ".kts",
    ".groovy",
    ".scala",
    ".php",
    ".rb",
    ".erb",
    ".go",
    ".rs",
    ".swift",
    ".dart",
    ".lua",
    ".pl",
    ".pm",
    ".tcl",
    ".sh",
    ".bash",
    ".zsh",
    ".bat",
    ".cmd",
    ".ps1",
    ".psm1",
    ".vbs",
    ".make",
    ".mk",
    ".sql",
    ".graphql",
    ".prisma",
}

KNOWN_TEXT_FILENAMES = {
    "dockerfile",
    "makefile",
    "readme",
    "license",
    "caddyfile",
    ".gitignore",
    ".dockerignore",
    ".env",
    ".editorconfig",
    ".prettierrc",
    ".eslintrc",
}

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".idea",
    ".vs",
    "build",
    "dist",
}

MAX_TEXT_FILE_SIZE_MB = 10
MAX_TOTAL_OUTPUT_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_TREE_EXPAND_NODES = 2000
NULL_BYTE_CHECK_MIN_BYTES = 1024

_WINDOWS_RESERVED = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$",
    re.IGNORECASE,
)
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_TREE_CONNECTOR_RE = re.compile(r"^(.*?)(├──|└──)\s*(.+)$")
_META_BRACKET_RE = re.compile(r"^\[.+\]$")


def is_ignored_dir_name(name: str) -> bool:
    return name in IGNORED_DIRS


def is_valid_path_segment(name: str) -> bool:
    if not name or name in {".", ".."}:
        return False
    if name.endswith(" ") or name.endswith("."):
        return False
    # Reject absolute / drive-anchored segments before pathlib joinpath can escape root
    try:
        if Path(name).is_absolute():
            return False
    except (OSError, ValueError):
        return False
    if _INVALID_NAME_CHARS.search(name):
        return False
    if os.name == "nt" and _WINDOWS_RESERVED.match(name):
        return False
    return True


def safe_join_under(root, *parts):
    """Join path parts under root; raise ValueError on traversal / reserved names."""
    base = Path(root).resolve()
    if not parts:
        return base
    candidate = base
    for part in parts:
        part_str = str(part)
        if not is_valid_path_segment(part_str):
            raise ValueError(f"نام مسیر نامعتبر یا خطرناک رد شد: {part!r}")
        # Join one segment at a time; never use bare joinpath(*parts) with absolute parts
        candidate = (candidate / part_str).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError(f"تلاش برای نوشتن خارج از پوشه مقصد رد شد: {candidate}")
    return candidate


def win_long_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    s = str(path.resolve())
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s.lstrip("\\"))
    return Path("\\\\?\\" + s)


def mkdir_safe(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        win_long_path(path).mkdir(parents=True, exist_ok=True)


def touch_safe(path: Path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    except OSError:
        lp = win_long_path(path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.touch()


def is_text_file_heuristic(filepath):
    path_obj = Path(filepath)
    name_lower = path_obj.name.lower()
    suffix_known = path_obj.suffix.lower() in KNOWN_TEXT_EXTENSIONS
    name_known = name_lower in KNOWN_TEXT_FILENAMES

    try:
        size = path_obj.stat().st_size
    except OSError:
        return False

    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
    except OSError:
        return False

    if b"\0" in chunk:
        return False

    if suffix_known or name_known:
        return True

    if size < NULL_BYTE_CHECK_MIN_BYTES:
        return bool(chunk) and b"\0" not in chunk

    return True


def parse_txt_structure(content: str) -> list[tuple[list[str], bool]]:
    """Parse tree lines produced by generate_tree_structure. Pure helper."""
    structure: list[tuple[list[str], bool]] = []
    current_path: list[str] = []
    for line in content.splitlines():
        match = _TREE_CONNECTOR_RE.match(line)
        if not match:
            continue
        prefix, _connector, original_name = match.groups()
        original_name = original_name.strip()
        if _META_BRACKET_RE.match(original_name.rstrip("/")):
            continue
        name = original_name.rstrip("/")
        is_dir = original_name.endswith("/")
        # Level from connector column index (4 spaces / box unit per level)
        level = match.start(2) // 4
        while len(current_path) > level:
            current_path.pop()
        current_path.append(name)
        structure.append((current_path[:], is_dir))
    return structure


def count_tree_nodes(node: dict) -> int:
    n = 1
    for child in node.get("children", []):
        n += count_tree_nodes(child)
    return n


def iter_dir_sorted(path: Path):
    try:
        items = [
            x
            for x in path.iterdir()
            if not x.is_symlink() and not (x.is_dir() and is_ignored_dir_name(x.name))
        ]
        return sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return None


def generate_tree_structure(root_path, prefix=""):
    lines = []
    items = iter_dir_sorted(root_path)
    if items is None:
        lines.append(f"{prefix}└── [عدم دسترسی به پوشه]")
        return lines
    for index, item in enumerate(items):
        is_last = index == len(items) - 1
        connector = "└── " if is_last else "├── "
        name = f"{item.name}/" if item.is_dir() else item.name
        lines.append(f"{prefix}{connector}{name}")
        if item.is_dir():
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(generate_tree_structure(item, new_prefix))
    return lines


def build_tree_data(path: Path) -> dict:
    children: list[dict] = []
    result: dict = {"name": path.name, "type": "directory", "children": children}
    items = iter_dir_sorted(path)
    if items is None:
        return result
    for item in items:
        if item.is_dir():
            children.append(build_tree_data(item))
        else:
            children.append({"name": item.name, "type": "file"})
    return result


def read_file_content(file_path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    last_err: BaseException | None = None
    for enc in encodings:
        try:
            with open(file_path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_err = e
            continue
        except OSError as e:
            last_err = e
            # Retry once with Windows long-path prefix; never let a second OSError escape raw
            try:
                with open(win_long_path(Path(file_path)), encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError as e2:
                last_err = e2
                continue
            except OSError as e2:
                last_err = e2
                continue
    if isinstance(last_err, UnicodeDecodeError):
        raise last_err
    raise OSError(f"خواندن فایل ممکن نشد: {file_path}") from last_err


def create_from_json(node, output_root: Path, current_rel=()):
    if not isinstance(node, dict):
        raise ValueError("ساختار JSON نامعتبر است: هر گره باید شیء باشد.")
    if "type" not in node or "name" not in node:
        raise ValueError("ساختار JSON نامعتبر است: فیلدهای name و type الزامی‌اند.")

    node_type = node["type"]
    if node_type == "directory":
        target = (
            safe_join_under(output_root, *current_rel)
            if current_rel
            else Path(output_root).resolve()
        )
        mkdir_safe(target)
        for child in node.get("children", []):
            if not isinstance(child, dict) or "name" not in child:
                raise ValueError("فرزند JSON نامعتبر است.")
            child_rel = current_rel + (child["name"],)
            create_from_json(child, output_root, child_rel)
    elif node_type == "file":
        target = safe_join_under(output_root, *current_rel)
        touch_safe(target)
    else:
        raise ValueError(f"نوع گره ناشناخته در JSON: {node_type!r}")


class FileScanner(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)
    tree_data = Signal(dict)

    def __init__(self, root_path, mode="full", output_format="txt"):
        super().__init__()
        self.root_path = Path(root_path)
        self.mode = mode
        self.output_format = output_format

    def run(self):
        try:
            tree_structure = build_tree_data(self.root_path)
            if self.isInterruptionRequested():
                return
            self.tree_data.emit(tree_structure)

            if self.mode == "structure":
                if self.output_format == "txt":
                    output_lines = [f"ریشه پروژه:\n{self.root_path}\n", "=" * 80 + "\n"]
                    output_lines.extend(generate_tree_structure(self.root_path))
                    output_lines.append("\n" + "=" * 80 + "\n")
                    final_output = "\n".join(output_lines)
                else:
                    final_output = json.dumps(tree_structure, ensure_ascii=False, indent=2)
                if not self.isInterruptionRequested():
                    self.finished.emit(final_output)
                return

            output_lines = []
            all_files = []

            for root, dirs, files in os.walk(self.root_path):
                if self.isInterruptionRequested():
                    return
                dirs[:] = [
                    d
                    for d in dirs
                    if not os.path.islink(os.path.join(root, d)) and not is_ignored_dir_name(d)
                ]
                for f in files:
                    if not os.path.islink(os.path.join(root, f)):
                        all_files.append((root, f))

            output_lines.append(f"ریشه پروژه:\n{self.root_path}\n")
            output_lines.append("=" * 80 + "\n")
            processed = 0
            total_files = len(all_files)
            last_percent = -1
            total_bytes = sum(len(x.encode("utf-8")) for x in output_lines)
            capped = False

            for root, filename in all_files:
                if self.isInterruptionRequested():
                    return
                if capped:
                    break

                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.root_path)

                chunk_parts = [
                    f"\n{'-' * 60}\n",
                    f"مسیر نسبی: {rel_path}\n",
                    f"مسیر کامل: {file_path}\n",
                ]

                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)

                    if is_text_file_heuristic(file_path):
                        if size_mb > MAX_TEXT_FILE_SIZE_MB:
                            chunk_parts.append(
                                f"\n[اخطار ضدکرش: فایل متنی بسیار بزرگ است ({size_mb:.2f} MB)]\n"
                                f"[برای جلوگیری از قفل شدن سیستم، از استخراج محتوای این فایل صرف‌نظر شد]\n"
                            )
                        else:
                            content = read_file_content(file_path)
                            if content.strip():
                                chunk_parts.append(f"\nمحتوای فایل {filename}:\n")
                                chunk_parts.append(content)
                            else:
                                chunk_parts.append("\n(فایل خالی است)\n")
                    else:
                        chunk_parts.append(f"\n[فایل باینری یا غیرمتنی] - ({size_mb:.2f} MB)\n")
                except Exception as e:
                    chunk_parts.append(f"\n[خطا در پردازش فایل]: {e}\n")

                chunk_text = "".join(chunk_parts)
                chunk_size = len(chunk_text.encode("utf-8"))
                if total_bytes + chunk_size > MAX_TOTAL_OUTPUT_BYTES:
                    output_lines.append(
                        "\n\n[سقف ۵۰ مگابایت خروجی رسید — استخراج محتوا متوقف شد]\n"
                    )
                    capped = True
                else:
                    output_lines.append(chunk_text)
                    total_bytes += chunk_size

                processed += 1
                if total_files > 0:
                    progress_percent = int((processed / total_files) * 100)
                    if progress_percent != last_percent:
                        last_percent = progress_percent
                        self.progress.emit(progress_percent)

            if not self.isInterruptionRequested():
                self.finished.emit("\n".join(output_lines))
        except Exception as e:
            self.error.emit(str(e))


class ReverseScanner(QThread):
    finished = Signal(str)
    error = Signal(str)
    preview = Signal(str)

    def __init__(self, map_file_path, output_path, input_format="txt"):
        super().__init__()
        self.map_file_path = Path(map_file_path)
        self.output_path = Path(output_path)
        self.input_format = input_format

    def run(self):
        try:
            try:
                with open(self.map_file_path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                try:
                    with open(win_long_path(self.map_file_path), encoding="utf-8") as f:
                        content = f.read()
                except OSError as e:
                    raise OSError(f"خواندن فایل نقشه ممکن نشد: {self.map_file_path}") from e

            if self.isInterruptionRequested():
                return

            preview = (
                content
                if len(content) <= 2_000_000
                else content[:2_000_000] + "\n\n[پیش‌نمایش کوتاه شد]\n"
            )
            self.preview.emit(preview)

            if self.input_format == "txt":
                structure = parse_txt_structure(content)
                for path_parts, is_dir in structure:
                    if self.isInterruptionRequested():
                        return
                    full_path = safe_join_under(self.output_path, *path_parts)
                    if is_dir:
                        mkdir_safe(full_path)
                    else:
                        touch_safe(full_path)
            else:
                try:
                    tree = json.loads(content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"فایل JSON نامعتبر است: {e}") from e
                if not isinstance(tree, dict) or "type" not in tree or "name" not in tree:
                    raise ValueError("ریشه JSON باید شامل name و type باشد.")
                if tree.get("type") != "directory":
                    raise ValueError("ریشه JSON باید از نوع directory باشد.")
                create_from_json(tree, self.output_path, ())

            if not self.isInterruptionRequested():
                self.finished.emit("بازسازی ساختار با موفقیت انجام شد!")
        except Exception as e:
            self.error.emit(str(e))


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("درباره کاوشگر هوشمند پروژه")
        self.setFixedSize(550, 420)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView).pixmap(64, 64)
        )

        title_label = QLabel("کاوشگر و مهندسی معکوس پروژه‌های نرم‌افزاری")
        title_label.setStyleSheet("font-size: 19px; font-weight: bold; color: #38bdf8;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        desc = QLabel(
            "<b style='color:#e0f2fe; font-size:14px;'>نسخه 5.1 (Bulletproof Polish)</b><br><br>"
            "توسعه‌یافته بر پایه PySide6 با محافظت مسیر، سقف حافظه و توقف ایمن ترد.<br><br>"
            "<b style='color:#7dd3fc;'>ویژگی‌های این نسخه:</b><br>"
            "• <b>سقف خروجی:</b> حداکثر ۵۰ مگابایت متن تجمعی + رد فایل متنی بالای ۱۰ مگابایت<br>"
            "• <b>نگهبان مسیر:</b> جلوگیری از path traversal در بازسازی TXT/JSON<br>"
            "• <b>آنتی‌لوپ:</b> رد symlink و پوشه‌های سنگین (.git، node_modules، …)<br>"
            "• <b>بازسازی:</b> فقط ساختار خالی پوشه/فایل (بدون بازگردانی محتوا)<br>"
            "• <b>UX:</b> Drag & Drop، تم تیره، ادیتور بهینه‌شده برای متن ساده<br>"
        )
        desc.setStyleSheet("font-size: 13px; color: #cbd5e1; line-height: 1.6;")
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(desc)

        layout.addStretch()

        close_btn = QPushButton("بستن")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.close)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setStyleSheet("""
            QDialog { background-color: #0f172a; border: 1px solid #0ea5e9; border-radius: 10px; }
            QLabel { font-family: 'Segoe UI', Tahoma; }
            QPushButton {
                background-color: #0284c7; color: white; border: none;
                border-radius: 6px; padding: 10px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #0369a1; }
            QPushButton:pressed { background-color: #075985; }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("کاوشگر هوشمند پروژه - Enterprise Edition")
        self.setGeometry(150, 80, 1300, 850)

        # Portable/onefile: PyInstaller extracts datas next to the frozen script (_MEIPASS)
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            icon_path = Path(sys._MEIPASS) / "icon.ico"
        else:
            icon_path = Path(__file__).with_name("icon.ico")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))

        self.scan_thread = None
        self.reverse_thread = None
        self.selected_folder = None
        self.selected_input_file = None
        self.last_output_format = "txt"
        self._busy = False

        self.setAcceptDrops(True)
        self.init_menu()
        self.init_ui()
        self.apply_dark_theme()
        self.on_mode_changed(self.mode_combo.currentIndex())

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "آماده برای استفاده - لطفا یک پوشه را انتخاب یا روی صفحه رها (Drag & Drop) کنید"
        )

    def init_menu(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu("فایل", self)
        open_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "انتخاب پوشه", self
        )
        open_action.triggered.connect(self.select_folder)
        save_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "ذخیره خروجی",
            self,
        )
        save_action.triggered.connect(self.save_to_file)
        exit_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "خروج", self
        )
        exit_action.triggered.connect(self.close)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        edit_menu = QMenu("ویرایش", self)
        copy_action = QAction("کپی کل محتوا", self)
        copy_action.triggered.connect(self.copy_content)
        clear_action = QAction("پاکسازی ادیتور", self)
        clear_action.triggered.connect(self.clear_content)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(clear_action)

        help_menu = QMenu("کمک", self)
        about_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation),
            "درباره برنامه",
            self,
        )
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(edit_menu)
        menu_bar.addMenu(help_menu)

    def show_about_dialog(self):
        AboutDialog(self).exec()

    def init_ui(self):
        self.central_widget_container = QWidget()
        central_layout = QVBoxLayout(self.central_widget_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.central_widget_container)

        central_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_layout.addWidget(central_splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(20)

        title = QLabel("کاوشگر هوشمند پروژه‌")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("AppTitle")
        left_layout.addWidget(title)

        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)

        scan_tab = QWidget()
        scan_layout = QVBoxLayout(scan_tab)
        scan_layout.setSpacing(15)

        scan_group = QGroupBox("تنظیمات پردازشگر")
        scan_group_layout = QVBoxLayout(scan_group)
        scan_group_layout.setSpacing(12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                "کامل (استخراج محتوای تمام فایل‌های کُد و متن)",
                "فقط ساختار درختی پوشه‌ها",
            ]
        )
        self.mode_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        scan_group_layout.addWidget(QLabel("حالت کاوش:"))
        scan_group_layout.addWidget(self.mode_combo)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["فایل متنی استاندارد (TXT)", "ساختار داده (JSON)"])
        self.format_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_group_layout.addWidget(QLabel("فرمت خروجی:"))
        scan_group_layout.addWidget(self.format_combo)

        self.format_hint = QLabel("JSON فقط در حالت «فقط ساختار» در دسترس است.")
        self.format_hint.setWordWrap(True)
        self.format_hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        scan_group_layout.addWidget(self.format_hint)

        scan_layout.addWidget(scan_group)

        self.folder_btn = QPushButton("انتخاب پوشه پروژه")
        self.folder_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_btn.clicked.connect(self.select_folder)
        scan_layout.addWidget(self.folder_btn)

        self.path_label = QLabel("هیچ پوشه‌ای انتخاب نشده است.\nمیتوانید پوشه را درگ و دراپ کنید.")
        self.path_label.setWordWrap(True)
        self.path_label.setObjectName("PathLabel")
        scan_layout.addWidget(self.path_label)

        self.start_btn = QPushButton("شروع اسکن و تولید خروجی")
        self.start_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setEnabled(False)
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self.start_scanning)
        scan_layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        scan_layout.addWidget(self.progress_bar)
        scan_layout.addStretch()
        self.tab_widget.addTab(scan_tab, "کاوش (Scan)")

        reverse_tab = QWidget()
        reverse_layout = QVBoxLayout(reverse_tab)
        reverse_layout.setSpacing(15)

        reverse_info = QLabel(
            "ساختار پروژه را از فایل TXT یا JSON از پیش تولید شده، "
            "مجدداً به صورت پوشه و فایل خالی بازسازی کنید. "
            "(محتوای فایل‌ها بازگردانی نمی‌شود.)"
        )
        reverse_info.setWordWrap(True)
        reverse_layout.addWidget(reverse_info)

        self.input_file_btn = QPushButton("انتخاب فایل نقشه (TXT/JSON)")
        self.input_file_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.input_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.input_file_btn.clicked.connect(self.select_input_file)
        reverse_layout.addWidget(self.input_file_btn)

        self.input_file_label = QLabel("فایلی انتخاب نشده است.")
        self.input_file_label.setWordWrap(True)
        self.input_file_label.setObjectName("PathLabel")
        reverse_layout.addWidget(self.input_file_label)

        self.reverse_btn = QPushButton("اجرای مهندسی معکوس (بازسازی)")
        self.reverse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reverse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reverse_btn.setEnabled(False)
        self.reverse_btn.setObjectName("WarningButton")
        self.reverse_btn.clicked.connect(self.reverse_structure)
        reverse_layout.addWidget(self.reverse_btn)
        reverse_layout.addStretch()
        self.tab_widget.addTab(reverse_tab, "بازسازی (Reverse)")

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 20, 20, 0)

        output_header = QHBoxLayout()
        output_label = QLabel("ویرایشگر هوشمند خروجی")
        output_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e2e8f0;")

        self.copy_btn = QPushButton("کپی")
        self.copy_btn.setFixedWidth(80)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self.copy_content)

        self.save_btn = QPushButton("ذخیره")
        self.save_btn.setFixedWidth(80)
        self.save_btn.setEnabled(False)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setObjectName("SuccessButton")
        self.save_btn.clicked.connect(self.save_to_file)

        output_header.addWidget(output_label)
        output_header.addStretch()
        output_header.addWidget(self.copy_btn)
        output_header.addWidget(self.save_btn)
        text_layout.addLayout(output_header)

        self.output_text = QPlainTextEdit()
        self.output_text.setFont(QFont("Consolas", 11))
        self.output_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.output_text.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        text_layout.addWidget(self.output_text)

        tree_widget_container = QWidget()
        tree_layout = QVBoxLayout(tree_widget_container)
        tree_layout.setContentsMargins(0, 10, 20, 20)

        tree_label = QLabel("نمای زنده ساختار درختی پروژه")
        tree_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e2e8f0;")
        tree_layout.addWidget(tree_label)

        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderHidden(True)
        tree_layout.addWidget(self.tree_view)

        self.tree_opacity = QGraphicsOpacityEffect(self.tree_view)
        self.tree_view.setGraphicsEffect(self.tree_opacity)
        self.fade_animation = QPropertyAnimation(self.tree_opacity, b"opacity")
        self.fade_animation.setDuration(700)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        right_splitter.addWidget(text_widget)
        right_splitter.addWidget(tree_widget_container)
        right_splitter.setSizes([600, 400])
        right_splitter.setHandleWidth(6)

        central_splitter.addWidget(left_widget)
        central_splitter.addWidget(right_splitter)
        central_splitter.setSizes([380, 920])
        central_splitter.setHandleWidth(6)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QWidget { color: #f8fafc; font-family: 'Segoe UI', Tahoma; font-size: 13px; }
            QWidget#DragDropActive { border: 2px dashed #38bdf8; background-color: #1e293b; border-radius: 10px; }
            QLabel#AppTitle {
                font-size: 20px; font-weight: bold; color: #f8fafc;
                padding: 18px; background-color: #1e293b;
                border-radius: 8px; border-left: 5px solid #38bdf8;
            }
            QLabel#PathLabel { color: #94a3b8; font-style: italic; background: #1e293b; padding: 10px; border-radius: 6px; }
            QPushButton {
                background-color: #334155; color: white; border: 1px solid #475569;
                border-radius: 6px; padding: 9px 15px; font-weight: bold; outline: none;
            }
            QPushButton:hover { background-color: #475569; border-color: #94a3b8; }
            QPushButton:pressed { background-color: #1e293b; }
            QPushButton:disabled { background-color: #0f172a; color: #64748b; border: 1px solid #1e293b; }
            QPushButton#PrimaryButton { background-color: #0284c7; border: 1px solid #0369a1; }
            QPushButton#PrimaryButton:hover { background-color: #0ea5e9; border: 1px solid #38bdf8; }
            QPushButton#SuccessButton { background-color: #166534; border: 1px solid #14532d; }
            QPushButton#SuccessButton:hover { background-color: #15803d; }
            QPushButton#WarningButton { background-color: #991b1b; border: 1px solid #7f1d1d; }
            QPushButton#WarningButton:hover { background-color: #b91c1c; }
            QComboBox {
                background-color: #1e293b; color: #f8fafc; border: 1px solid #475569;
                border-radius: 6px; padding: 7px; min-height: 25px;
            }
            QComboBox:hover { border-color: #38bdf8; }
            QComboBox:disabled { color: #64748b; }
            QComboBox::drop-down { border: none; padding-right: 10px; }
            QComboBox QAbstractItemView {
                background-color: #1e293b; color: white;
                selection-background-color: #0284c7; border: 1px solid #475569;
            }
            QPlainTextEdit {
                background-color: #1e293b; color: #e2e8f0; selection-background-color: #0369a1;
                border: 1px solid #334155; border-radius: 8px; padding: 12px;
            }
            QPlainTextEdit:focus { border: 1px solid #38bdf8; }
            QTreeWidget {
                background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155;
                border-radius: 8px; padding: 5px; outline: none;
            }
            QTreeWidget::item { padding: 4px; border-radius: 4px; margin-bottom: 2px;}
            QTreeWidget::item:hover { background-color: #334155; }
            QTreeWidget::item:selected { background-color: #0284c7; color: white; font-weight: bold;}
            QSplitter::handle { background-color: #334155; margin: 2px 0px; border-radius: 3px; }
            QSplitter::handle:hover { background-color: #38bdf8; }
            QSplitter::handle:horizontal { width: 6px; }
            QSplitter::handle:vertical { height: 6px; }
            QProgressBar {
                border: 1px solid #334155; border-radius: 6px; text-align: center;
                background-color: #0f172a; color: white; font-weight: bold; height: 20px;
            }
            QProgressBar::chunk { background-color: #0ea5e9; border-radius: 5px; }
            QGroupBox {
                border: 1px solid #334155; border-radius: 8px; margin-top: 15px;
                font-weight: bold; color: #7dd3fc; padding-top: 20px; padding-bottom: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; }
            QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; background-color: #0f172a; top: -1px;}
            QTabBar::tab {
                background-color: #1e293b; color: #94a3b8; padding: 10px 20px;
                border-radius: 6px; margin-right: 4px; font-weight: bold;
            }
            QTabBar::tab:hover { background-color: #334155; color: #e2e8f0; }
            QTabBar::tab:selected { background-color: #0284c7; color: white; border-bottom: 2px solid #38bdf8;}
            QStatusBar { background-color: #0f172a; color: #94a3b8; border-top: 1px solid #1e293b; padding-left: 10px;}
            QMenuBar { background-color: #0f172a; color: #e2e8f0; padding: 3px; }
            QMenuBar::item:selected { background-color: #1e293b; border-radius: 4px;}
            QMenu { background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 5px;}
            QMenu::item { padding: 8px 25px 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #0284c7; }
            QScrollBar:vertical { background: #0f172a; width: 12px; margin: 0px; border-radius: 6px;}
            QScrollBar::handle:vertical { background: #334155; min-height: 20px; border-radius: 6px;}
            QScrollBar::handle:vertical:hover { background: #475569; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar:horizontal { background: #0f172a; height: 12px; margin: 0px; border-radius: 6px;}
            QScrollBar::handle:horizontal { background: #334155; min-width: 20px; border-radius: 6px;}
            QScrollBar::handle:horizontal:hover { background: #475569; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        """)

    def _any_thread_running(self):
        for t in (self.scan_thread, self.reverse_thread):
            if t is not None and t.isRunning():
                return True
        return False

    def _disconnect_thread(self, thread):
        if thread is None:
            return
        for sig_name in ("progress", "finished", "error", "tree_data", "preview"):
            sig = getattr(thread, sig_name, None)
            if sig is None:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    sig.disconnect()
                except (TypeError, RuntimeError):
                    pass

    def set_busy(self, busy: bool):
        self._busy = busy
        self.folder_btn.setEnabled(not busy)
        self.input_file_btn.setEnabled(not busy)
        self.mode_combo.setEnabled(not busy)
        if not busy:
            self.on_mode_changed(self.mode_combo.currentIndex())
        else:
            self.format_combo.setEnabled(False)
        self.start_btn.setEnabled(not busy and self.selected_folder is not None)
        self.update_reverse_enabled()

    def update_reverse_enabled(self):
        ready = (
            not self._busy
            and self.selected_folder is not None
            and self.selected_input_file is not None
        )
        self.reverse_btn.setEnabled(ready)

    def on_mode_changed(self, index):
        structure_mode = index == 1
        self.format_combo.setEnabled(structure_mode and not self._busy)
        if not structure_mode:
            self.format_combo.setCurrentIndex(0)
        self.format_hint.setVisible(not structure_mode)

    def _reset_drop_style(self):
        self.central_widget_container.setObjectName("")
        self.central_widget_container.style().unpolish(self.central_widget_container)
        self.central_widget_container.style().polish(self.central_widget_container)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.central_widget_container.setObjectName("DragDropActive")
            self.central_widget_container.style().unpolish(self.central_widget_container)
            self.central_widget_container.style().polish(self.central_widget_container)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._reset_drop_style()

    def dropEvent(self, event: QDropEvent):
        self._reset_drop_style()
        urls = event.mimeData().urls()
        if not urls or not urls[0].isLocalFile():
            self.status_bar.showMessage("فقط فایل/پوشه محلی قابل رها کردن است.")
            return
        path = Path(urls[0].toLocalFile())
        if path.is_dir():
            self.selected_folder = path
            self.path_label.setText(f"پوشه آماده کاوش:\n{self.selected_folder}")
            self.path_label.setStyleSheet(
                "color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;"
            )
            self.start_btn.setEnabled(not self._busy)
            self.update_reverse_enabled()
            self.tab_widget.setCurrentIndex(0)
            self.status_bar.showMessage("پوشه با موفقیت وارد شد.")
            self.refresh_tree_view()
        elif path.is_file() and path.suffix.lower() in {".txt", ".json"}:
            self.selected_input_file = path
            self.input_file_label.setText(f"فایل نقشه آماده بازسازی:\n{self.selected_input_file}")
            self.input_file_label.setStyleSheet(
                "color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;"
            )
            self.update_reverse_enabled()
            self.tab_widget.setCurrentIndex(1)
            self.status_bar.showMessage("فایل نقشه پروژه بارگذاری شد.")
        else:
            self.status_bar.showMessage("نوع رها شده پشتیبانی نمی‌شود (پوشه یا TXT/JSON).")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه پروژه", "")
        if folder:
            self.selected_folder = Path(folder)
            self.path_label.setText(f"پوشه آماده کاوش:\n{self.selected_folder}")
            self.path_label.setStyleSheet(
                "color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;"
            )
            self.start_btn.setEnabled(not self._busy)
            self.update_reverse_enabled()
            self.status_bar.showMessage("پوشه انتخاب شد.")
            self.refresh_tree_view()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل ورودی",
            "",
            "Text Files (*.txt);;JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.selected_input_file = Path(file_path)
            self.input_file_label.setText(f"فایل نقشه آماده بازسازی:\n{self.selected_input_file}")
            self.input_file_label.setStyleSheet(
                "color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;"
            )
            self.update_reverse_enabled()
            self.status_bar.showMessage("فایل نقشه پروژه انتخاب شد.")

    def start_scanning(self):
        if not self.selected_folder:
            return
        if self._any_thread_running():
            self.status_bar.showMessage("یک عملیات در حال اجراست؛ لطفاً صبر کنید.")
            return

        self.output_text.clear()
        mode = "structure" if self.mode_combo.currentIndex() == 1 else "full"
        output_format = (
            "json" if (mode == "structure" and self.format_combo.currentIndex() == 1) else "txt"
        )
        self.last_output_format = output_format

        self.progress_bar.setVisible(True)
        if mode == "structure":
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

        self.set_busy(True)
        self.save_btn.setEnabled(False)
        self.status_bar.showMessage("در حال اسکن عمیق و ایمن پروژه... لطفاً منتظر بمانید.")

        self._disconnect_thread(self.scan_thread)
        self.scan_thread = FileScanner(self.selected_folder, mode=mode, output_format=output_format)
        self.scan_thread.progress.connect(self.progress_bar.setValue)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.error.connect(self.on_job_error)
        self.scan_thread.tree_data.connect(self.populate_tree_view)
        self.scan_thread.start()

    def reverse_structure(self):
        if not self.selected_folder or not self.selected_input_file:
            QMessageBox.warning(
                self,
                "خطای منطقی",
                "برای بازسازی پروژه، ابتدا باید پوشه مقصد و سپس فایل نقشه را انتخاب کنید.",
            )
            return
        if self._any_thread_running():
            self.status_bar.showMessage("یک عملیات در حال اجراست؛ لطفاً صبر کنید.")
            return

        input_format = "json" if self.selected_input_file.suffix.lower() == ".json" else "txt"
        self.set_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("در حال اجرای مهندسی معکوس و ساخت پوشه‌ها...")

        self._disconnect_thread(self.reverse_thread)
        self.reverse_thread = ReverseScanner(
            self.selected_input_file, self.selected_folder, input_format
        )
        self.reverse_thread.preview.connect(self.output_text.setPlainText)
        self.reverse_thread.finished.connect(self.on_reverse_finished)
        self.reverse_thread.error.connect(self.on_job_error)
        self.reverse_thread.start()

    def on_scan_finished(self, content):
        self.output_text.setPlainText(content)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.set_busy(False)
        self.save_btn.setEnabled(True)
        self.status_bar.showMessage("عملیات اسکن با موفقیت به پایان رسید.")
        QMessageBox.information(
            self,
            "پایان عملیات",
            "تحلیل و استخراج اطلاعات پروژه تکمیل شد.\nمی‌توانید خروجی را بررسی و ذخیره کنید.",
        )

    def on_reverse_finished(self, message):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.set_busy(False)
        self.status_bar.showMessage("بازسازی ساختار کامل شد.")
        QMessageBox.information(self, "عملیات موفق", message)
        self.refresh_tree_view()

    def on_job_error(self, error_msg):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.set_busy(False)
        self.status_bar.showMessage("خطای غیرمنتظره در حین پردازش رخ داد.")
        QMessageBox.critical(
            self,
            "خطای سیستمی",
            f"برنامه در حین پردازش با خطای زیر متوقف شد:\n{error_msg}",
        )

    def copy_content(self):
        QApplication.clipboard().setText(self.output_text.toPlainText())
        self.status_bar.showMessage("کل محتوا در کلیپ‌بورد سیستم ذخیره شد.")

    def clear_content(self):
        self.output_text.clear()
        self.save_btn.setEnabled(False)
        self.status_bar.showMessage("محیط ویرایشگر تخلیه شد.")

    def save_to_file(self):
        content = self.output_text.toPlainText().strip()
        if not content:
            return

        output_format = self.last_output_format
        default_name = (
            "Project_Structure.json" if output_format == "json" else "Project_Structure_Code.txt"
        )
        if output_format == "json":
            filters = "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        else:
            filters = "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل خروجی",
            os.path.join(str(self.selected_folder or os.getcwd()), default_name),
            filters,
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.status_bar.showMessage("فایل استخراج شده با موفقیت ذخیره شد.")
                QMessageBox.information(
                    self,
                    "ذخیره‌سازی موفق",
                    f"اطلاعات پروژه در مسیر زیر با موفقیت نوشته شد:\n{file_path}",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "شکست در ذخیره‌سازی",
                    f"سیستم عامل اجازه ذخیره فایل را نداد:\n{e}",
                )

    def populate_tree_view(self, tree_data):
        self.tree_view.clear()
        root_item = QTreeWidgetItem([tree_data["name"]])
        root_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.add_tree_items(root_item, tree_data.get("children", []))
        self.tree_view.addTopLevelItem(root_item)
        if count_tree_nodes(tree_data) <= MAX_TREE_EXPAND_NODES:
            self.tree_view.expandAll()
        else:
            root_item.setExpanded(True)
        self.fade_animation.start()

    def add_tree_items(self, parent_item, children):
        for child in children:
            child_item = QTreeWidgetItem([child["name"]])
            if child["type"] == "directory":
                child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                self.add_tree_items(child_item, child.get("children", []))
            else:
                child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            parent_item.addChild(child_item)

    def refresh_tree_view(self):
        if self.selected_folder:
            tree_structure = build_tree_data(self.selected_folder)
            self.populate_tree_view(tree_structure)

    def closeEvent(self, event: QCloseEvent):
        for t in (self.scan_thread, self.reverse_thread):
            if t is not None and t.isRunning():
                t.requestInterruption()
                t.wait(3000)
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
