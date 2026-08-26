# عیب‌یابی

**زبان‌ها:** [English](TROUBLESHOOTING.md) · **فارسی**

## اجرا

### `ModuleNotFoundError: PySide6`

```bat
pip install -r requirements.txt
python -c "import PySide6; print(PySide6.__version__)"
```

### پنجره باز و بسته می‌شود / خطای پلاگین Qt

- نصب مجدد PySide6
- در CI بدون نمایشگر: `QT_QPA_PLATFORM=offscreen`
- درایور GPU / ریموت دسکتاپ را بررسی کنید

### Drag & Drop کار نمی‌کند

- هدف باید **پوشه** باشد
- برنامه نباید مشغول اسکن/بازسازی باشد

### اسکن روی ریپوی بزرگ کند است

- نوار پیشرفت را ببینید
- سقف **۵۰ مگ** ممکن است استخراج را متوقف کند (عمدی)
- ریشهٔ اشتباه را اسکن نکنید

### JSON غیرفعال است

در حالت **کامل** عمدی است — به **فقط ساختار** بروید.

### بازسازی فایل خالی ساخت

عمدی است؛ بازگردانی محتوا در v5.1 نیست.

### مسیر در بازسازی رد شد

نقشه احتمالاً `..`، مسیر مطلق، کاراکتر غیرمجاز یا نام رزرو ویندوز دارد.

## بیلد

### Python پیدا نشد

پایتون ۳.۱۰+ نصب و به PATH اضافه شود؛ شل را دوباره باز کنید.

### EXE ساخته نشد

اولین traceback را بخوانید؛ خروجی portable قبلی را پاک و دوباره بسازید؛ قفل آنتی‌ویروس را در نظر بگیرید.

### حجم زیاد EXE

با Qt onefile طبیعی است.

## تست / QA

### شکست فرمت

```bat
python -m isort file-explorer-pyside6.py tests
python -m black file-explorer-pyside6.py tests
qa.bat
```

## هنوز گیر کرده‌اید؟

Issue با OS، نسخه Python/PySide6، فرمان دقیق و لاگ باز کنید:
https://github.com/Ali-Rashidi-80/File-Explorer/issues
