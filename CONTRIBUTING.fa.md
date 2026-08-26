# راهنمای مشارکت

**زبان‌ها:** [English](CONTRIBUTING.md) · **فارسی**

از کمک شما سپاسگزاریم. این راهنما مشارکت را ایمن، قابل‌تست و صادقانه نگه می‌دارد.

## منشور رفتار

مشارکت تحت [CODE_OF_CONDUCT.fa.md](CODE_OF_CONDUCT.fa.md) است.

## گزارش امنیتی

آسیب‌پذیری را **عمومی** ثبت نکنید. [SECURITY.fa.md](SECURITY.fa.md) را دنبال کنید.

## راه‌اندازی توسعه

```bat
git clone https://github.com/Ali-Rashidi-80/File-Explorer.git
cd "File-Explorer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python file-explorer-pyside6.py
```

## قواعد پروژه

1. **اپ فعال** = `file-explorer-pyside6.py`. مگر برای اصلاح اشارهٔ مستندات، `file_explorer.py` را گسترش ندهید.
2. **بازسازی = اسکلت خالی** مگر PR صریحاً بازگردانی محتوا با سقف و تست اضافه کند.
3. **JSON فقط در حالت ساختار** — قفل UI و تست‌ها هم‌تراز بمانند.
4. منطق قابل تست را در هلپرهای خالص بالای ماژول نگه دارید.
5. بدون secret؛ بدون ریفکتور بی‌ربط به هدف PR.

## دروازه کیفیت

قبل از PR:

```bat
qa.bat
```

## فرایند Pull Request

1. از `main` شاخه بسازید (`feat/…`, `fix/…`, `docs/…`).
2. برای تغییر رفتار تست بنویسید/به‌روز کنید.
3. مستندات EN + FA را در صورت تغییر رفتار کاربر به‌روز کنید.
4. در متن PR روی **چرا** تمرکز کنید.
5. به Issue مرتبط لینک دهید.

### چک‌لیست PR

- [ ] `qa.bat` پاس شده
- [ ] رفتار جدید تست دارد
- [ ] مستندات به‌روز شده
- [ ] دامنه به legacy کشیده نشده

## Issues

- **باگ:** گام‌ها، انتظار/واقعیت، OS، نسخه Python/PySide6
- **ویژگی:** صورت مسئله، UX پیشنهادی، صداقت درباره سقف‌ها و معنای reverse

## پرسش

[GitHub Issues](https://github.com/Ali-Rashidi-80/File-Explorer/issues)
