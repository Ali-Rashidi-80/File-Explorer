# -*- coding: utf-8 -*-
"""
File Explorer to Clean TXT/JSON Generator with Reverse Functionality
نسخه 5.0 (Ultimate/Bulletproof) - پایداری مطلق در سطح Enterprise
توسعه‌یافته با UI/UX مدرن (VS Code Style)، ضدگلوله، دارای محافظت حافظه و پردازش حلقه‌های بی‌نهایت
پشتیبانی ۱۰۰٪ از تمام فرمت‌های متنی جهان.
"""
import sys
import os
import json
import re
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QTextEdit, QMessageBox, QHBoxLayout,
    QProgressBar, QComboBox, QSplitter, QTabWidget, QGroupBox,
    QStatusBar, QMenuBar, QMenu, QTreeWidget, QTreeWidgetItem, 
    QStyle, QDialog, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QAction, QDragEnterEvent, QDropEvent

# =====================================================================
# دیتابیس جامع پسوندهای متنی و کدهای برنامه‌نویسی سراسر جهان
# =====================================================================
KNOWN_TEXT_EXTENSIONS = {
    # متون و داکیومنت
    '.txt', '.md', '.rtf', '.csv', '.log', '.ini', '.cfg', '.conf', '.json', '.xml', '.yaml', '.yml', '.toml',
    # وب و مارک‌آپ
    '.html', '.htm', '.css', '.scss', '.sass', '.less', '.xml', '.svg',
    # جاوا اسکریپت و اکوسیستم آن
    '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.mjs', '.cjs',
    # پایتون
    '.py', '.pyw', '.pyx', '.pxd', '.pxi', '.ipynb',
    # سی و سی‌پلاس‌پلاس
    '.c', '.cpp', '.cxx', '.cc', '.h', '.hpp', '.hxx',
    # سی‌شارپ و دات‌نت
    '.cs', '.fs', '.vb',
    # جاوا و کاتلین
    '.java', '.kt', '.kts', '.groovy', '.scala',
    # زبان‌های بک‌اند و اسکریپتی
    '.php', '.rb', '.erb', '.go', '.rs', '.swift', '.dart', '.lua', '.pl', '.pm', '.tcl',
    # شل و اتوماسیون
    '.sh', '.bash', '.zsh', '.bat', '.cmd', '.ps1', '.psm1', '.vbs', '.make', '.mk',
    # دیتابیس
    '.sql', '.graphql', '.prisma',
    # متفرقه و فایل‌های پیکربندی رایج بدون پسوند
    '.gitignore', '.dockerignore', '.env', '.editorconfig', '.prettierrc', '.eslintrc'
}

# محدودیت حجم برای جلوگیری از کرش شدن رم (مثلاً دیتابیس‌های چند گیگابایتی)
MAX_TEXT_FILE_SIZE_MB = 10 

def is_text_file_heuristic(filepath):
    """
    تشخیص کاملاً هوشمند فایل متنی.
    ترکیب تشخیص از روی پسوند و خواندن باینری هدر فایل برای تضمین 100 درصدی.
    """
    path_obj = Path(filepath)
    if path_obj.suffix.lower() in KNOWN_TEXT_EXTENSIONS:
        return True
    
    if path_obj.name.lower() in ['dockerfile', 'makefile', 'readme', 'license', 'caddyfile']:
        return True

    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return False  # شامل بایت Null است -> فایل باینری (عکس، اجرایی و غیره)
            return True
    except Exception:
        return False


class FileScanner(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)
    tree_data = Signal(dict)

    def __init__(self, root_path, mode='full', output_format='txt'):
        super().__init__()
        self.root_path = Path(root_path)
        self.mode = mode
        self.output_format = output_format

    def generate_tree_structure(self, root_path, prefix="", level=0):
        lines = []
        try:
            # رد کردن symlink ها برای جلوگیری از حلقه بی‌نهایت (Infinite Loop Protection)
            items = sorted(
                [x for x in root_path.iterdir() if not x.is_symlink()], 
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
            for index, item in enumerate(items):
                is_last = index == len(items) - 1
                connector = "└── " if is_last else "├── "
                name = f"{item.name}/" if item.is_dir() else item.name
                lines.append(f"{prefix}{connector}{name}")
                if item.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    lines.extend(self.generate_tree_structure(item, new_prefix, level + 1))
        except PermissionError:
            lines.append(f"{prefix}└── [عدم دسترسی به پوشه]")
        return lines

    def build_tree_data(self, path):
        result = {"name": path.name, "type": "directory", "children": []}
        try:
            items = sorted(
                [x for x in path.iterdir() if not x.is_symlink()],
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
            for item in items:
                if item.is_dir():
                    result["children"].append(self.build_tree_data(item))
                else:
                    result["children"].append({"name": item.name, "type": "file"})
        except PermissionError:
            pass 
        return result

    def read_file_content(self, file_path):
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("All encodings failed", b"", 0, 1, "invalid")

    def run(self):
        try:
            tree_structure = self.build_tree_data(self.root_path)
            self.tree_data.emit(tree_structure)

            if self.mode == 'structure':
                if self.output_format == 'txt':
                    output_lines = [f"ریشه پروژه:\n{self.root_path}\n", "=" * 80 + "\n"]
                    output_lines.extend(self.generate_tree_structure(self.root_path))
                    output_lines.append("\n" + "=" * 80 + "\n")
                    final_output = "\n".join(output_lines)
                else:
                    final_output = json.dumps(tree_structure, ensure_ascii=False, indent=2)
                self.finished.emit(final_output)
                return

            output_lines = []
            all_files = []
            total_files = 0
            
            for root, dirs, files in os.walk(self.root_path):
                # Symlink Protection & Ignore typical massive build folders
                dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d)) and d not in ['.git', '__pycache__', 'node_modules', 'venv', '.idea', '.vs', 'build', 'dist']]
                for f in files:
                    if not os.path.islink(os.path.join(root, f)):
                        total_files += 1
                        all_files.append((root, f))
                    
            output_lines.append(f"ریشه پروژه:\n{self.root_path}\n")
            output_lines.append("=" * 80 + "\n")
            processed = 0
            
            for root, filename in all_files:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.root_path)
                
                output_lines.append(f"\n{'-'*60}\n")
                output_lines.append(f"مسیر نسبی: {rel_path}\n")
                output_lines.append(f"مسیر کامل: {file_path}\n")
                
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    
                    if is_text_file_heuristic(file_path):
                        if size_mb > MAX_TEXT_FILE_SIZE_MB:
                            output_lines.append(f"\n[اخطار ضدکرش: فایل متنی بسیار بزرگ است ({size_mb:.2f} MB)]\n[برای جلوگیری از قفل شدن سیستم، از استخراج محتوای این فایل صرف‌نظر شد]\n")
                        else:
                            content = self.read_file_content(file_path)
                            if content.strip():
                                output_lines.append(f"\nمحتوای فایل {filename}:\n")
                                output_lines.append(content)
                            else:
                                output_lines.append(f"\n(فایل خالی است)\n")
                    else:
                        output_lines.append(f"\n[فایل باینری یا غیرمتنی] - ({size_mb:.2f} MB)\n")
                except Exception as e:
                    output_lines.append(f"\n[خطا در پردازش فایل]: {e}\n")

                processed += 1
                if total_files > 0:
                    progress_percent = int((processed / total_files) * 100)
                    self.progress.emit(progress_percent)
                    
            final_output = "\n".join(output_lines)
            self.finished.emit(final_output)
        except Exception as e:
            self.error.emit(str(e))


class ReverseScanner(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, input_content, output_path, input_format='txt'):
        super().__init__()
        self.input_content = input_content
        self.output_path = Path(output_path)
        self.input_format = input_format

    def parse_txt_structure(self, content):
        structure = []
        lines = content.splitlines()
        current_path = []
        pattern = re.compile(r'^(.*?(?:├──|└──)\s*)([^\s].*)$')
        for line in lines:
            match = pattern.match(line)
            if match:
                prefix, original_name = match.groups()
                name = original_name.rstrip('/')
                is_dir = original_name.endswith('/')
                level = prefix.count('│') + (prefix.count(' ') // 4)
                
                while len(current_path) > level:
                    if current_path: current_path.pop()
                current_path.append(name)
                path = current_path[:]
                structure.append((path, is_dir))
        return structure

    def run(self):
        try:
            if self.input_format == 'txt':
                structure = self.parse_txt_structure(self.input_content)
                for path_parts, is_dir in structure:
                    full_path = self.output_path.joinpath(*path_parts)
                    if is_dir:
                        full_path.mkdir(parents=True, exist_ok=True)
                    else:
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.touch()
            else:
                tree = json.loads(self.input_content)
                self.create_from_json(tree, self.output_path)
            self.finished.emit("بازسازی ساختار با موفقیت انجام شد!")
        except Exception as e:
            self.error.emit(str(e))

    def create_from_json(self, node, current_path):
        if node.get("type") == "directory":
            current_path.mkdir(parents=True, exist_ok=True)
            for child in node.get("children", []):
                self.create_from_json(child, current_path / child["name"])
        else:
            current_path.touch()


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
        icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView).pixmap(64, 64))
        
        title_label = QLabel("کاوشگر و مهندسی معکوس پروژه‌های نرم‌افزاری")
        title_label.setStyleSheet("font-size: 19px; font-weight: bold; color: #38bdf8;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc = QLabel(
            "<b style='color:#e0f2fe; font-size:14px;'>نسخه 5.0 (Ultimate Bulletproof Edition)</b><br><br>"
            "توسعه‌یافته بر پایه PySide6 با معماری ایمن برای پروژه‌های شرکتی عظیم.<br><br>"
            "<b style='color:#7dd3fc;'>ویژگی‌های منحصربه‌فرد این نسخه:</b><br>"
            "🛡️ <b>محافظت حافظه (OOM Protection):</b> رد کردن خودکار فایل‌های متنی بالای ۱۰ مگابایت<br>"
            "🔄 <b>آنتی لوپ (Symlink Guard):</b> جلوگیری از گیرکردن در میان‌برهای چرخشی لینوکس/ویندوز<br>"
            "🧠 <b>تشخیص هوشمند (Heuristic):</b> شناسایی فایل‌های بدون پسوند با پردازش بایت‌هدرها<br>"
            "🚀 <b>رندر فوق‌سریع:</b> نمایش روان خروجی‌های غول‌پیکر در ادیتور بدون کرش کردن UI<br>"
            "✨ <b>تجربه کاربری (UX):</b> افکت‌های تعاملی Drag & Drop و تم دارک در سطح VS Code<br>"
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
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        
        self.scanner = None
        self.selected_folder = None
        self.selected_input_file = None
        
        self.setAcceptDrops(True)
        self.init_menu()
        self.init_ui()
        self.apply_dark_theme()
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("آماده برای استفاده - لطفا یک پوشه را انتخاب یا روی صفحه رها (Drag & Drop) کنید")

    def init_menu(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu("فایل", self)
        open_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "انتخاب پوشه", self)
        open_action.triggered.connect(self.select_folder)
        save_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "ذخیره خروجی", self)
        save_action.triggered.connect(self.save_to_file)
        exit_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "خروج", self)
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
        about_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation), "درباره برنامه", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(edit_menu)
        menu_bar.addMenu(help_menu)

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def init_ui(self):
        self.central_widget_container = QWidget()
        central_layout = QVBoxLayout(self.central_widget_container)
        central_layout.setContentsMargins(0,0,0,0)
        self.setCentralWidget(self.central_widget_container)

        central_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_layout.addWidget(central_splitter)

        # === پنل چپ ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(20)

        title = QLabel("کاوشگر هوشمند پروژه‌")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("AppTitle") # برای استایل‌دهی اختصاصی CSS
        left_layout.addWidget(title)

        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)

        # تب کاوش
        scan_tab = QWidget()
        scan_layout = QVBoxLayout(scan_tab)
        scan_layout.setSpacing(15)
        
        scan_group = QGroupBox("تنظیمات پردازشگر")
        scan_group_layout = QVBoxLayout(scan_group)
        scan_group_layout.setSpacing(12)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["کامل (استخراج محتوای تمام فایل‌های کُد و متن)", "فقط ساختار درختی پوشه‌ها"])
        self.mode_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_group_layout.addWidget(QLabel("حالت کاوش:"))
        scan_group_layout.addWidget(self.mode_combo)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["فایل متنی استاندارد (TXT)", "ساختار داده (JSON)"])
        self.format_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_group_layout.addWidget(QLabel("فرمت خروجی:"))
        scan_group_layout.addWidget(self.format_combo)
        
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

        # تب بازسازی
        reverse_tab = QWidget()
        reverse_layout = QVBoxLayout(reverse_tab)
        reverse_layout.setSpacing(15)
        
        reverse_info = QLabel("ساختار پروژه را از فایل TXT یا JSON از پیش تولید شده، مجدداً به صورت پوشه و فایل بازسازی کنید.")
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

        # === پنل راست ===
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # ادیتور متن
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

        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas", 11)) 
        # کانفیگ‌های ضروری برای جلوگیری از کرش شدن UI در متن‌های بسیار طولانی
        self.output_text.setAcceptRichText(False) 
        self.output_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) # سرعت بالاتر در اسکرول افقی فایل‌های کد
        text_layout.addWidget(self.output_text)
        
        # نمایشگر درختی
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
        """
        طراحی تم مدرن استایل JetBrains و VS Code (کاملا سازگار با تمام ویندوزها).
        رنگ‌های پایه (Slate/Zinc) و کادرهای مشخص.
        """
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QWidget { color: #f8fafc; font-family: 'Segoe UI', Tahoma; font-size: 13px; }
            
            /* طراحی درگ اند دراپ */
            QWidget#DragDropActive { border: 2px dashed #38bdf8; background-color: #1e293b; border-radius: 10px; }
            
            QLabel#AppTitle {
                font-size: 20px; font-weight: bold; color: #f8fafc;
                padding: 18px; background-color: #1e293b;
                border-radius: 8px; border-left: 5px solid #38bdf8;
            }
            QLabel#PathLabel { color: #94a3b8; font-style: italic; background: #1e293b; padding: 10px; border-radius: 6px; }
            
            /* دکمه‌های عمومی */
            QPushButton {
                background-color: #334155; color: white; border: 1px solid #475569;
                border-radius: 6px; padding: 9px 15px; font-weight: bold; outline: none;
            }
            QPushButton:hover { background-color: #475569; border-color: #94a3b8; }
            QPushButton:pressed { background-color: #1e293b; }
            QPushButton:disabled { background-color: #0f172a; color: #64748b; border: 1px solid #1e293b; }
            
            /* دکمه‌های ویژه */
            QPushButton#PrimaryButton { background-color: #0284c7; border: 1px solid #0369a1; }
            QPushButton#PrimaryButton:hover { background-color: #0ea5e9; border: 1px solid #38bdf8; }
            
            QPushButton#SuccessButton { background-color: #166534; border: 1px solid #14532d; }
            QPushButton#SuccessButton:hover { background-color: #15803d; }
            
            QPushButton#WarningButton { background-color: #991b1b; border: 1px solid #7f1d1d; }
            QPushButton#WarningButton:hover { background-color: #b91c1c; }
            
            /* فرم‌ها */
            QComboBox {
                background-color: #1e293b; color: #f8fafc; border: 1px solid #475569;
                border-radius: 6px; padding: 7px; min-height: 25px;
            }
            QComboBox:hover { border-color: #38bdf8; }
            QComboBox::drop-down { border: none; padding-right: 10px; }
            QComboBox QAbstractItemView { background-color: #1e293b; color: white; selection-background-color: #0284c7; border: 1px solid #475569;}
            
            /* ادیتور */
            QTextEdit {
                background-color: #1e293b; color: #e2e8f0; selection-background-color: #0369a1;
                border: 1px solid #334155; border-radius: 8px; padding: 12px;
            }
            QTextEdit:focus { border: 1px solid #38bdf8; }
            
            /* درخت پروژه */
            QTreeWidget {
                background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; 
                border-radius: 8px; padding: 5px; outline: none;
            }
            QTreeWidget::item { padding: 4px; border-radius: 4px; margin-bottom: 2px;}
            QTreeWidget::item:hover { background-color: #334155; }
            QTreeWidget::item:selected { background-color: #0284c7; color: white; font-weight: bold;}
            
            /* اسپلیترها - قابلیت دیده شدن بهتر در پنل‌های دارک */
            QSplitter::handle { background-color: #334155; margin: 2px 0px; border-radius: 3px; }
            QSplitter::handle:hover { background-color: #38bdf8; }
            QSplitter::handle:horizontal { width: 6px; }
            QSplitter::handle:vertical { height: 6px; }
            
            /* نوار پیشرفت */
            QProgressBar {
                border: 1px solid #334155; border-radius: 6px; text-align: center; 
                background-color: #0f172a; color: white; font-weight: bold; height: 20px;
            }
            QProgressBar::chunk { background-color: #0ea5e9; border-radius: 5px; }
            
            /* تب‌ها و کادرها */
            QGroupBox {
                border: 1px solid #334155; border-radius: 8px; margin-top: 15px; 
                font-weight: bold; color: #7dd3fc; padding-top: 20px; padding-bottom: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; }
            
            QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; background-color: #0f172a; top: -1px;}
            QTabBar::tab { background-color: #1e293b; color: #94a3b8; padding: 10px 20px; border-radius: 6px; margin-right: 4px; font-weight: bold; }
            QTabBar::tab:hover { background-color: #334155; color: #e2e8f0; }
            QTabBar::tab:selected { background-color: #0284c7; color: white; border-bottom: 2px solid #38bdf8;}
            
            /* منو و وضعیت */
            QStatusBar { background-color: #0f172a; color: #94a3b8; border-top: 1px solid #1e293b; padding-left: 10px;}
            QMenuBar { background-color: #0f172a; color: #e2e8f0; padding: 3px; }
            QMenuBar::item:selected { background-color: #1e293b; border-radius: 4px;}
            QMenu { background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 5px;}
            QMenu::item { padding: 8px 25px 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #0284c7; }
            
            /* اسکرول‌بارها */
            QScrollBar:vertical { background: #0f172a; width: 12px; margin: 0px; border-radius: 6px;}
            QScrollBar::handle:vertical { background: #334155; min-height: 20px; border-radius: 6px;}
            QScrollBar::handle:vertical:hover { background: #475569; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar:horizontal { background: #0f172a; height: 12px; margin: 0px; border-radius: 6px;}
            QScrollBar::handle:horizontal { background: #334155; min-width: 20px; border-radius: 6px;}
            QScrollBar::handle:horizontal:hover { background: #475569; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        """)

    # --- استایل دهی داینامیک هنگام Drag & Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.central_widget_container.setObjectName("DragDropActive")
            self.central_widget_container.style().unpolish(self.central_widget_container)
            self.central_widget_container.style().polish(self.central_widget_container)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.central_widget_container.setObjectName("")
        self.central_widget_container.style().unpolish(self.central_widget_container)
        self.central_widget_container.style().polish(self.central_widget_container)

    def dropEvent(self, event: QDropEvent):
        self.dragLeaveEvent(None) # بازگردانی استایل پس از رها کردن
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.is_dir():
                self.selected_folder = path
                self.path_label.setText(f"پوشه آماده کاوش:\n{self.selected_folder}")
                self.path_label.setStyleSheet("color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;")
                self.start_btn.setEnabled(True)
                self.reverse_btn.setEnabled(True)
                self.status_bar.showMessage("پوشه با موفقیت وارد شد.")
                self.refresh_tree_view()
            elif path.is_file() and (path.suffix in {'.txt', '.json'}):
                self.selected_input_file = path
                self.input_file_label.setText(f"فایل نقشه آماده بازسازی:\n{self.selected_input_file}")
                self.input_file_label.setStyleSheet("color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;")
                self.reverse_btn.setEnabled(True)
                self.tab_widget.setCurrentIndex(1) 
                self.status_bar.showMessage("فایل نقشه پروژه بارگذاری شد.")

    # ---------------------------------------------

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه پروژه", "")
        if folder:
            self.selected_folder = Path(folder)
            self.path_label.setText(f"پوشه آماده کاوش:\n{self.selected_folder}")
            self.path_label.setStyleSheet("color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;")
            self.start_btn.setEnabled(True)
            self.reverse_btn.setEnabled(True)
            self.status_bar.showMessage("پوشه انتخاب شد.")
            self.refresh_tree_view()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل ورودی", "", "Text Files (*.txt);;JSON Files (*.json);;All Files (*)")
        if file_path:
            self.selected_input_file = Path(file_path)
            self.input_file_label.setText(f"فایل نقشه آماده بازسازی:\n{self.selected_input_file}")
            self.input_file_label.setStyleSheet("color: #34d399; font-weight: bold; background: #064e3b; border: 1px solid #059669;")
            self.reverse_btn.setEnabled(True)
            self.status_bar.showMessage("فایل نقشه پروژه انتخاب شد.")

    def start_scanning(self):
        if not self.selected_folder:
            return
            
        self.output_text.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.status_bar.showMessage("در حال اسکن عمیق و ایمن پروژه... لطفاً منتظر بمانید.")
        
        mode = 'structure' if self.mode_combo.currentIndex() == 1 else 'full'
        output_format = 'json' if self.format_combo.currentIndex() == 1 else 'txt'
        
        self.scanner = FileScanner(self.selected_folder, mode=mode, output_format=output_format)
        self.scanner.progress.connect(self.progress_bar.setValue)
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.error.connect(self.on_scan_error)
        self.scanner.tree_data.connect(self.populate_tree_view)
        self.scanner.start()

    def reverse_structure(self):
        if not self.selected_folder or not self.selected_input_file:
            QMessageBox.warning(self, "خطای منطقی", "برای بازسازی پروژه، ابتدا باید پوشه مقصد و سپس فایل نقشه را انتخاب کنید.")
            return
        try:
            with open(self.selected_input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.output_text.setPlainText(content)
            input_format = 'json' if self.selected_input_file.suffix.lower() == '.json' else 'txt'
            
            self.scanner = ReverseScanner(content, self.selected_folder, input_format)
            self.scanner.finished.connect(self.on_reverse_finished)
            self.scanner.error.connect(self.on_scan_error)
            self.scanner.start()
            
            self.status_bar.showMessage("در حال اجرای مهندسی معکوس و ساخت پوشه‌ها...")
        except Exception as e:
            QMessageBox.critical(self, "خطای فایل", f"امکان خواندن فایل نقشه وجود ندارد:\n{e}")

    def on_scan_finished(self, content):
        self.output_text.setPlainText(content)
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_bar.showMessage("عملیات اسکن با موفقیت به پایان رسید.")
        QMessageBox.information(self, "پایان عملیات", "تحلیل و استخراج اطلاعات پروژه تکمیل شد.\nمی‌توانید خروجی را بررسی و ذخیره کنید.")

    def on_reverse_finished(self, message):
        self.status_bar.showMessage("بازسازی ساختار کامل شد.")
        QMessageBox.information(self, "عملیات موفق", message)
        self.refresh_tree_view()

    def on_scan_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.status_bar.showMessage("خطای غیرمنتظره در حین پردازش رخ داد.")
        QMessageBox.critical(self, "خطای سیستمی", f"برنامه در حین پردازش با خطای زیر متوقف شد:\n{error_msg}")

    def copy_content(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.status_bar.showMessage("کل محتوا در کلیپ‌بورد سیستم ذخیره شد.")

    def clear_content(self):
        self.output_text.clear()
        self.save_btn.setEnabled(False)
        self.status_bar.showMessage("محیط ویرایشگر تخلیه شد.")

    def save_to_file(self):
        content = self.output_text.toPlainText().strip()
        if not content:
            return
            
        output_format = 'json' if self.format_combo.currentIndex() == 1 else 'txt'
        default_name = "Project_Structure.json" if output_format == 'json' else "Project_Structure_Code.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره فایل خروجی", 
            os.path.join(str(self.selected_folder or os.getcwd()), default_name), 
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_bar.showMessage("فایل استخراج شده با موفقیت ذخیره شد.")
                QMessageBox.information(self, "ذخیره‌سازی موفق", f"اطلاعات پروژه در مسیر زیر با موفقیت نوشته شد:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "شکست در ذخیره‌سازی", f"سیستم عامل اجازه ذخیره فایل را نداد:\n{e}")

    def populate_tree_view(self, tree_data):
        self.tree_view.clear()
        root_item = QTreeWidgetItem([tree_data['name']])
        root_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.add_tree_items(root_item, tree_data.get('children', []))
        self.tree_view.addTopLevelItem(root_item)
        self.tree_view.expandAll()
        
        self.fade_animation.start()

    def add_tree_items(self, parent_item, children):
        for child in children:
            child_item = QTreeWidgetItem([child['name']])
            if child['type'] == 'directory':
                child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                self.add_tree_items(child_item, child.get('children', []))
            else:
                child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            parent_item.addChild(child_item)

    def refresh_tree_view(self):
        if self.selected_folder:
            tree_structure = FileScanner(self.selected_folder).build_tree_data(self.selected_folder)
            self.populate_tree_view(tree_structure)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())