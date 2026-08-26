# راهنمای ساخت (EXE قابل حمل)

**زبان‌ها:** [English](BUILD.md) · **فارسی**

## هدف

ساخت یک فایل اجرایی ویندوز تک‌فایلی:

`dist\FileExplorer_Portable.exe`

## یک فرمان

```bat
build_portable.bat
```

(`build_portable.bat` به `build.bat` واگذار می‌کند.)

## مراحل `build.bat`

1. بررسی Python  
2. نصب PySide6 + PyInstaller  
3. یافتن یا دانلود UPX (اختیاری)  
4. پاک‌سازی خروجی portable قبلی  
5. PyInstaller با `FileExplorer.portable.spec`  
6. تأیید وجود EXE و نمایش تقریبی حجم  

## نکات spec

- ورودی: `file-explorer-pyside6.py`
- نام: `FileExplorer_Portable`، بدون کنسول
- جاسازی `icon.ico` در صورت وجود
- حذف بسته‌های سنگین بلااستفاده
- UPX با exclude برای DLLهای حساس Qt/Python

## دستی

```bat
python -m PyInstaller --noconfirm FileExplorer.portable.spec
```

همچنین: [`../pyinstaller.txt`](../pyinstaller.txt).

## خطاهای رایج

| مشکل | کاهش اثر |
|------|-----------|
| Python پیدا نشد | نصب ۳.۱۰+ و باز کردن دوباره شل |
| WinError 32 | اسکریپت از `--clean` سراسری پرهیز می‌کند |
| نبود icon | بیلد ادامه می‌یابد |
| حجم زیاد EXE | با Qt طبیعی است |

خروجی‌های `build/`، `dist/` و `tools/upx/` در gitignore هستند.
