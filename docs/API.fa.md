# API — هلپرهای خالص

**زبان‌ها:** [English](API.md) · **فارسی**

هلپرها در `file-explorer-pyside6.py` هستند و تست‌ها آن‌ها را با `importlib` بار می‌کنند.

## ایمنی مسیر

- `is_valid_path_segment` — رد سگمنت خطرناک / رزرو
- `safe_join_under` — اتصال امن زیر ریشه؛ `ValueError` در صورت فرار
- `win_long_path` — پیشوند مسیر بلند ویندوز
- `mkdir_safe` / `touch_safe` — ساخت با fallback

## درخت و متن

- `is_ignored_dir_name` — عضویت در `IGNORED_DIRS`
- `is_text_file_heuristic` — تشخیص متن
- `generate_tree_structure` — خطوط درخت TXT
- `build_tree_data` — درخت JSON/UI
- `parse_txt_structure` — پارس `├──`/`└──` با سطح از ایندکس کانکتور
- `count_tree_nodes` — شمارش گره
- `read_file_content` — چند encoding + long-path
- `create_from_json` — مادّی‌سازی اسکلت خالی

## Workers

| کلاس | سیگنال‌های کلیدی |
|------|------------------|
| `FileScanner` | `progress`, `finished`, `error`, `tree_data` |
| `ReverseScanner` | `finished`, `error`, `preview` |

## ثابت‌ها

`MAX_TEXT_FILE_SIZE_MB=10`، `MAX_TOTAL_OUTPUT_BYTES=50MiB`، `MAX_TREE_EXPAND_NODES=2000`، به‌همراه allow-listها و `IGNORED_DIRS`.

در v5.1 بستهٔ pip عمومی برای API کتابخانه‌ای منتشر نشده — محصول همان اپ دسکتاپ است.
