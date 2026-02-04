# -*- coding: utf-8 -*-
"""
File Explorer to Clean TXT/JSON Generator with Reverse Functionality
با PyQt6 - تم دارک آبی - پشتیبانی کامل از فارسی (RTL)
نسخه بهبودیافته با UI/UX حرفه‌ای و جذاب
وظیفه:
- انتخاب پوشه پروژه (با پشتیبانی از درگ اند دراپ)
- کاوش بازگشتی در تمام فایل‌ها و زیرپوشه‌ها بدون محدودیت پسوند فایل
- تولید فایل TXT یا JSON با دو حالت: کامل (شامل محتوا تمام فایل‌ها اگر ممکن) یا فقط ساختار
- معکوس کردن عملیات: بازسازی ساختار از فایل TXT یا JSON
- تشخیص هوشمند ساختار درختی از فایل TXT
- امکان ویرایش دستی، کپی، حذف و وارد کردن محتوا
- نمایش بصری ساختار درختی با QTreeWidget برای جذابیت بیشتر
- فاصله‌گذاری مناسب و نمایش مسیرها
- تم دارک آبی حرفه‌ای با سایه‌ها، آیکون‌ها و انیمیشن‌های ساده
- منوبار، استاتوس بار، اسپلیتر و درخت فایل برای UX بهتر
نصب پیش‌نیاز:
pip install PyQt6
"""
import sys
import os
import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QTextEdit, QMessageBox, QHBoxLayout,
    QProgressBar, QComboBox, QSplitter, QTabWidget, QGroupBox,
    QStatusBar, QMenuBar, QGraphicsDropShadowEffect, QMenu, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QIcon, QClipboard, QDragEnterEvent, QDropEvent, QColor, QAction

class FileScanner(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    tree_data = pyqtSignal(dict)  # برای ارسال داده درخت به UI

    def __init__(self, root_path, mode='full', output_format='txt'):
        super().__init__()
        self.root_path = Path(root_path)
        self.mode = mode  # 'full' یا 'structure'
        self.output_format = output_format  # 'txt' یا 'json'

    def generate_tree_structure(self, root_path, prefix="", level=0):
        """تولید ساختار درختی برای نمایش پوشه‌ها و فایل‌ها"""
        lines = []
        items = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for index, item in enumerate(items):
            is_last = index == len(items) - 1
            connector = "└── " if is_last else "├── "
            name = f"{item.name}/" if item.is_dir() else item.name
            lines.append(f"{prefix}{connector}{name}")
            if item.is_dir():
                new_prefix = prefix + ("    " if is_last else "│   ")
                lines.extend(self.generate_tree_structure(item, new_prefix, level + 1))
        return lines

    def build_tree_data(self, path):
        """ساخت داده برای QTreeWidget"""
        result = {"name": path.name, "type": "directory", "children": []}
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.is_dir():
                result["children"].append(self.build_tree_data(item))
            else:
                result["children"].append({"name": item.name, "type": "file"})
        return result

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
                else:  # JSON
                    final_output = json.dumps(tree_structure, ensure_ascii=False, indent=2)
                self.finished.emit(final_output)
                return

            # حالت کامل (شامل محتوا) بدون محدودیت پسوند
            output_lines = []
            all_files = []
            total_files = 0
            for root, dirs, files in os.walk(self.root_path):
                for f in files:
                    total_files += 1
                    all_files.append((root, f))
            output_lines.append(f"ریشه پروژه:\n{self.root_path}\n")
            output_lines.append("=" * 80 + "\n")
            processed = 0
            for root, filename in all_files:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.root_path)
                output_lines.append(f"مسیر نسبی: {rel_path}\n")
                output_lines.append(f"مسیر کامل: {file_path}\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if content.strip():
                        output_lines.append(f"محتوای فایل {filename}:\n")
                        # برای جذابیت، محتوا را با فرمت مناسب نمایش دهید (مثلاً کد با highlighting اگر ممکن)
                        output_lines.append(content.strip())
                        output_lines.append("\n")
                except UnicodeDecodeError:
                    output_lines.append(f"فایل باینری یا غیرقابل نمایش: {filename} ({file_path.stat().st_size} بایت)\n")
                except Exception as e:
                    output_lines.append(f"خطا در خواندن فایل: {e}\n")
                output_lines.append("-" * 60 + "\n")
                processed += 1
                progress_percent = int((processed / total_files) * 100)
                self.progress.emit(progress_percent)
            final_output = "\n".join(output_lines)
            self.finished.emit(final_output)
        except Exception as e:
            self.error.emit(str(e))

class ReverseScanner(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, input_content, output_path, input_format='txt'):
        super().__init__()
        self.input_content = input_content
        self.output_path = Path(output_path)
        self.input_format = input_format

    def parse_txt_structure(self, content):
        """تجزیه ساختار درختی از فایل TXT"""
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
                level = prefix.count('│')
                while len(current_path) > level:
                    current_path.pop()
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
            else:  # JSON
                tree = json.loads(self.input_content)
                self.create_from_json(tree, self.output_path)
            self.finished.emit("بازسازی ساختار با موفقیت انجام شد!")
        except Exception as e:
            self.error.emit(str(e))

    def create_from_json(self, node, current_path):
        """بازسازی ساختار از JSON"""
        if node["type"] == "directory":
            current_path.mkdir(parents=True, exist_ok=True)
            for child in node.get("children", []):
                self.create_from_json(child, current_path / child["name"])
        else:
            current_path.touch()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("کاوشگر هوشمند پروژه - نسخه جامع")
        self.setGeometry(200, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder"))
        self.scanner = None
        self.selected_folder = None
        self.selected_input_file = None
        self.setAcceptDrops(True)
        self.init_menu()
        self.init_ui()
        self.apply_dark_blue_theme()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("آماده برای استفاده")

    def init_menu(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu("فایل", self)
        open_action = QAction(QIcon.fromTheme("folder-open"), "انتخاب پوشه", self)
        open_action.triggered.connect(self.select_folder)
        save_action = QAction(QIcon.fromTheme("document-save"), "ذخیره خروجی", self)
        save_action.triggered.connect(self.save_to_file)
        exit_action = QAction(QIcon.fromTheme("application-exit"), "خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        edit_menu = QMenu("ویرایش", self)
        copy_action = QAction(QIcon.fromTheme("edit-copy"), "کپی محتوا", self)
        copy_action.triggered.connect(self.copy_content)
        clear_action = QAction(QIcon.fromTheme("edit-clear"), "حذف محتوا", self)
        clear_action.triggered.connect(self.clear_content)
        import_action = QAction(QIcon.fromTheme("document-open"), "وارد کردن محتوا", self)
        import_action.triggered.connect(self.import_content)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(clear_action)
        edit_menu.addAction(import_action)

        view_menu = QMenu("نمایش", self)
        refresh_tree = QAction(QIcon.fromTheme("view-refresh"), "به‌روزرسانی درخت فایل", self)
        refresh_tree.triggered.connect(self.refresh_tree_view)
        view_menu.addAction(refresh_tree)

        help_menu = QMenu("کمک", self)
        about_action = QAction(QIcon.fromTheme("help-about"), "درباره برنامه", self)
        about_action.triggered.connect(lambda: QMessageBox.about(self, "درباره", "کاوشگر پروژه حرفه‌ای و جامع\nنسخه 3.0\nساخته شده با PyQt6 - بدون محدودیت فایل"))
        help_menu.addAction(about_action)

        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(edit_menu)
        menu_bar.addMenu(view_menu)
        menu_bar.addMenu(help_menu)

    def init_ui(self):
        central_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(central_splitter)

        # پنل چپ: کنترل‌ها با تب‌ها
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("کاوشگر هوشمند پروژه - جامع و جذاب")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 20px; font-weight: bold; color: #a5d8ff;
            padding: 10px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a8a, stop:1 #1e40af);
            border-radius: 12px;
        """)
        left_layout.addWidget(title)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1e40af; border-radius: 8px; background: #0f172a; }
            QTabBar::tab { background: #1e40af; color: white; padding: 8px 16px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background: #2563eb; }
        """)
        left_layout.addWidget(self.tab_widget)

        # تب اسکن
        scan_tab = QWidget()
        scan_layout = QVBoxLayout(scan_tab)
        scan_group = QGroupBox("گزینه‌های کاوش (بدون محدودیت فایل)")
        scan_group_layout = QVBoxLayout(scan_group)
        options_layout = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["کامل (شامل محتوا تمام فایل‌ها)", "فقط ساختار پوشه‌ها"])
        self.mode_combo.setToolTip("انتخاب حالت کاوش - کامل بدون محدودیت پسوند")
        options_layout.addWidget(self.mode_combo)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["فایل متنی (TXT)", "فایل JSON"])
        self.format_combo.setToolTip("انتخاب فرمت خروجی")
        options_layout.addWidget(self.format_combo)
        scan_group_layout.addLayout(options_layout)
        scan_layout.addWidget(scan_group)

        self.folder_btn = QPushButton(QIcon.fromTheme("folder-open"), "انتخاب پوشه پروژه")
        self.folder_btn.setToolTip("انتخاب پوشه برای کاوش (یا درگ کنید)")
        self.folder_btn.clicked.connect(self.select_folder)
        scan_layout.addWidget(self.folder_btn)

        self.path_label = QLabel("هیچ پوشه‌ای انتخاب نشده")
        self.path_label.setWordWrap(True)
        scan_layout.addWidget(self.path_label)

        self.start_btn = QPushButton(QIcon.fromTheme("system-run"), "شروع کاوش")
        self.start_btn.setToolTip("شروع تولید خروجی بدون محدودیت")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_scanning)
        scan_layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        scan_layout.addWidget(self.progress_bar)
        scan_layout.addStretch()
        self.tab_widget.addTab(scan_tab, QIcon.fromTheme("edit-find"), "کاوش")

        # تب بازسازی
        reverse_tab = QWidget()
        reverse_layout = QVBoxLayout(reverse_tab)
        self.input_file_btn = QPushButton(QIcon.fromTheme("document-open"), "انتخاب فایل ورودی")
        self.input_file_btn.setToolTip("انتخاب فایل TXT یا JSON برای بازسازی")
        self.input_file_btn.clicked.connect(self.select_input_file)
        reverse_layout.addWidget(self.input_file_btn)

        self.input_file_label = QLabel("هیچ فایلی انتخاب نشده")
        self.input_file_label.setWordWrap(True)
        reverse_layout.addWidget(self.input_file_label)

        self.reverse_btn = QPushButton(QIcon.fromTheme("view-refresh"), "شروع بازسازی")
        self.reverse_btn.setToolTip("بازسازی ساختار در پوشه انتخاب‌شده")
        self.reverse_btn.setEnabled(False)
        self.reverse_btn.clicked.connect(self.reverse_structure)
        reverse_layout.addWidget(self.reverse_btn)
        reverse_layout.addStretch()
        self.tab_widget.addTab(reverse_tab, QIcon.fromTheme("view-refresh"), "بازسازی")

        # تب ویرایش
        edit_tab = QWidget()
        edit_layout = QVBoxLayout(edit_tab)
        self.copy_btn = QPushButton(QIcon.fromTheme("edit-copy"), "کپی محتوا")
        self.copy_btn.setToolTip("کپی محتوای خروجی به کلیپ‌بورد")
        self.copy_btn.clicked.connect(self.copy_content)
        edit_layout.addWidget(self.copy_btn)

        self.clear_btn = QPushButton(QIcon.fromTheme("edit-clear"), "حذف محتوا")
        self.clear_btn.setToolTip("پاک کردن محتوای خروجی")
        self.clear_btn.clicked.connect(self.clear_content)
        edit_layout.addWidget(self.clear_btn)

        self.import_btn = QPushButton(QIcon.fromTheme("document-open"), "وارد کردن محتوا")
        self.import_btn.setToolTip("وارد کردن محتوا از فایل")
        self.import_btn.clicked.connect(self.import_content)
        edit_layout.addWidget(self.import_btn)

        self.save_btn = QPushButton(QIcon.fromTheme("document-save"), "ذخیره خروجی")
        self.save_btn.setToolTip("ذخیره محتوای خروجی در فایل")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_to_file)
        edit_layout.addWidget(self.save_btn)
        edit_layout.addStretch()
        self.tab_widget.addTab(edit_tab, QIcon.fromTheme("document-edit"), "ویرایش")

        # پنل راست: خروجی و درخت فایل
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        output_label = QLabel("خروجی متن")
        output_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        output_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #a5d8ff;")
        right_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(False)
        self.output_text.setFont(QFont("Tahoma", 10))
        self.output_text.setToolTip("ویرایش دستی خروجی ممکن است - محتوای تمام فایل‌ها")
        right_layout.addWidget(self.output_text)

        tree_label = QLabel("نمایش ساختار درختی")
        tree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tree_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #a5d8ff;")
        right_layout.addWidget(tree_label)

        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setStyleSheet("""
            QTreeWidget {
                background: #0f172a; color: #bfdbfe; border: 1px solid #1e40af; border-radius: 10px;
            }
        """)
        right_layout.addWidget(self.tree_view)

        # اضافه کردن انیمیشن برای گسترش درخت
        self.animation = QPropertyAnimation(self.tree_view, b"geometry")

        # اضافه کردن سایه به پنل‌ها
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        left_widget.setGraphicsEffect(shadow)
        right_shadow = QGraphicsDropShadowEffect()
        right_shadow.setBlurRadius(15)
        right_shadow.setColor(QColor(0, 0, 0, 80))
        right_shadow.setOffset(2, 2)
        right_widget.setGraphicsEffect(right_shadow)

        central_splitter.addWidget(left_widget)
        central_splitter.addWidget(right_widget)
        central_splitter.setSizes([400, 800])
        central_splitter.setCollapsible(0, False)

        # تنظیمات RTL
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def apply_dark_blue_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f172a, stop:1 #1e293b);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e40af, stop:1 #1d4ed8);
                color: white; border: none; border-radius: 10px; padding: 10px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8); }
            QPushButton:pressed { background: #1e3a8a; }
            QPushButton:disabled { background: #374151; color: #6b7280; }
            QComboBox {
                background: #1e40af; color: white; border-radius: 8px; padding: 8px; font-size: 14px;
            }
            QComboBox::drop-down { border: none; }
            QLabel {
                color: #bfdbfe; font-family: 'Tahoma', 'Segoe UI';
            }
            QTextEdit {
                background: #0f172a; color: #bfdbfe; border: 1px solid #1e40af; border-radius: 10px; padding: 12px;
            }
            QProgressBar {
                border: 1px solid #1e40af; border-radius: 8px; text-align: center; background: #172554; color: #dbeafe; font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #1d4ed8); border-radius: 7px;
            }
            QGroupBox {
                border: 1px solid #1e40af; border-radius: 8px; margin-top: 10px; color: #a5d8ff; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px;
            }
            QStatusBar {
                background: #0f172a; color: #bfdbfe;
            }
            QTreeWidget::item:hover {
                background: #1e40af;
            }
            QTreeWidget::item:selected {
                background: #2563eb;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.is_dir():
                self.selected_folder = path
                self.path_label.setText(f"پوشه انتخاب‌شده:\n{self.selected_folder}")
                self.start_btn.setEnabled(True)
                self.reverse_btn.setEnabled(True)
                self.status_bar.showMessage("پوشه با موفقیت درگ شد")
                self.refresh_tree_view()
            elif path.is_file() and (path.suffix in {'.txt', '.json'}):
                self.selected_input_file = path
                self.input_file_label.setText(f"فایل ورودی:\n{self.selected_input_file}")
                self.reverse_btn.setEnabled(True)
                self.status_bar.showMessage("فایل با موفقیت درگ شد")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه پروژه", "")
        if folder:
            self.selected_folder = Path(folder)
            self.path_label.setText(f"پوشه انتخاب‌شده:\n{self.selected_folder}")
            self.start_btn.setEnabled(True)
            self.reverse_btn.setEnabled(True)
            self.status_bar.showMessage("پوشه انتخاب شد")
            self.refresh_tree_view()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل ورودی", "", "Text Files (*.txt);;JSON Files (*.json);;All Files (*)")
        if file_path:
            self.selected_input_file = Path(file_path)
            self.input_file_label.setText(f"فایل ورودی:\n{self.selected_input_file}")
            self.reverse_btn.setEnabled(True)
            self.status_bar.showMessage("فایل ورودی انتخاب شد")

    def start_scanning(self):
        if not self.selected_folder:
            return
        self.output_text.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)
        self.status_bar.showMessage("در حال کاوش کامل بدون محدودیت...")
        mode = 'structure' if self.mode_combo.currentText() == "فقط ساختار پوشه‌ها" else 'full'
        output_format = 'json' if self.format_combo.currentText() == "فایل JSON" else 'txt'
        self.scanner = FileScanner(self.selected_folder, mode=mode, output_format=output_format)
        self.scanner.progress.connect(self.progress_bar.setValue)
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.error.connect(self.on_scan_error)
        self.scanner.tree_data.connect(self.populate_tree_view)
        self.scanner.start()

    def reverse_structure(self):
        if not self.selected_folder or not self.selected_input_file:
            return
        try:
            with open(self.selected_input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.output_text.setPlainText(content)
            input_format = 'json' if self.selected_input_file.suffix == '.json' else 'txt'
            self.scanner = ReverseScanner(content, self.selected_folder, input_format)
            self.scanner.finished.connect(self.on_reverse_finished)
            self.scanner.error.connect(self.on_scan_error)
            self.scanner.start()
            self.status_bar.showMessage("در حال بازسازی...")
            self.refresh_tree_view()  # به‌روزرسانی درخت پس از بازسازی
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در خواندن فایل:\n{e}")

    def on_scan_finished(self, content):
        self.output_text.setPlainText(content)
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_bar.showMessage("کاوش کامل شد - محتوای تمام فایل‌ها خوانده شد")
        mode_text = "ساختار پوشه‌ها" if self.mode_combo.currentText() == "فقط ساختار پوشه‌ها" else "کامل بدون محدودیت"
        QMessageBox.information(self, "موفقیت", f"کاوش با موفقیت انجام شد!\nحالت: {mode_text}\nفرمت: {self.format_combo.currentText()}")

    def on_reverse_finished(self, message):
        self.status_bar.showMessage("بازسازی کامل شد")
        QMessageBox.information(self, "موفقیت", message)
        self.refresh_tree_view()

    def on_scan_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.status_bar.showMessage("خطا رخ داد")
        QMessageBox.critical(self, "خطا", f"خطا در عملیات:\n{error_msg}")

    def copy_content(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.status_bar.showMessage("محتوا کپی شد")
        QMessageBox.information(self, "موفقیت", "محتوا در کلیپ‌بورد کپی شد!")

    def clear_content(self):
        self.output_text.clear()
        self.save_btn.setEnabled(False)
        self.status_bar.showMessage("محتوا پاک شد")
        QMessageBox.information(self, "موفقیت", "محتوا پاک شد!")

    def import_content(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "وارد کردن فایل متنی یا JSON", "", "Text Files (*.txt);;JSON Files (*.json);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.output_text.setPlainText(content)
                self.save_btn.setEnabled(True)
                self.selected_input_file = Path(file_path)
                self.input_file_label.setText(f"فایل ورودی:\n{self.selected_input_file}")
                self.reverse_btn.setEnabled(True)
                self.status_bar.showMessage("محتوا وارد شد")
                QMessageBox.information(self, "موفقیت", "محتوا با موفقیت وارد شد!")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در وارد کردن فایل:\n{e}")

    def save_to_file(self):
        if not self.output_text.toPlainText().strip():
            return
        output_format = 'json' if self.format_combo.currentText() == "فایل JSON" else 'txt'
        default_name = "Project_Structure.json" if output_format == 'json' else "Project_Structure_Clean.txt"
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل", os.path.join(str(self.selected_folder or os.getcwd()), default_name), "JSON Files (*.json);;Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.output_text.toPlainText())
                self.status_bar.showMessage("فایل ذخیره شد")
                QMessageBox.information(self, "ذخیره شد", f"فایل با موفقیت ذخیره شد:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ذخیره فایل:\n{e}")

    def populate_tree_view(self, tree_data):
        self.tree_view.clear()
        root_item = QTreeWidgetItem([tree_data['name']])
        root_item.setIcon(0, QIcon.fromTheme("folder"))
        self.add_tree_items(root_item, tree_data['children'])
        self.tree_view.addTopLevelItem(root_item)
        self.tree_view.expandAll()
        # انیمیشن گسترش
        self.animation.setDuration(500)
        self.animation.setStartValue(QRect(0, 0, 0, 0))
        self.animation.setEndValue(self.tree_view.geometry())
        self.animation.start()

    def add_tree_items(self, parent_item, children):
        for child in children:
            child_item = QTreeWidgetItem([child['name']])
            if child['type'] == 'directory':
                child_item.setIcon(0, QIcon.fromTheme("folder"))
                self.add_tree_items(child_item, child.get('children', []))
            else:
                child_item.setIcon(0, QIcon.fromTheme("text-x-generic"))
            parent_item.addChild(child_item)

    def refresh_tree_view(self):
        if self.selected_folder:
            tree_structure = FileScanner(self.selected_folder).build_tree_data(self.selected_folder)
            self.populate_tree_view(tree_structure)
            self.status_bar.showMessage("درخت فایل به‌روزرسانی شد")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setFont(QFont("Tahoma", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())