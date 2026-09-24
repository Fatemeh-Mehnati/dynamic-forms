# قوانین همکاری

## branchها
- `main`: نسخه‌ی پایدار. فقط از `dev` و با PR به‌روز می‌شود.
- `dev`: شاخه‌ی اصلی کار. push مستقیم بسته است.
- هر تسک در یک branch جدا که از `dev` ساخته می‌شود:
  - `feature/<نام>` برای قابلیت جدید، مثل `feature/otp-auth`
  - `fix/<نام>` برای رفع خطا
  - `chore/<نام>` برای تنظیمات و کارهای جانبی
  - `docs/<نام>` برای مستندات

## روال کار
```bash
git checkout dev
git pull
git checkout -b feature/<نام>
# ... کد ...
git add .
git commit -m "feat: ..."
git push -u origin feature/<نام>
```
بعد در GitHub یک PR به `dev` باز کنید.

## commitها
قالب: `<نوع>: <توضیح کوتاه به انگلیسی>`
- `feat:` قابلیت جدید
- `fix:` رفع خطا
- `docs:` مستندات
- `test:` تست
- `refactor:` بازنویسی بدون تغییر رفتار
- `chore:` تنظیمات و وابستگی‌ها

مثال: `feat: add OTP verification endpoint`

## Pull Request
- هر PR به `dev` باز می‌شود و حداقل یک approve از یک عضو دیگر لازم دارد.
- PR کوچک باشد و فقط یک کار انجام دهد.
- قبل از باز کردن PR، `dev` را روی branch خود merge کنید و conflictها را خودتان حل کنید.
- در توضیح PR شماره‌ی Issue را با `Closes #شماره` بنویسید.
- همه‌ی PRها با **Create a merge commit** ادغام می‌شوند. branchها بعد از merge پاک نمی‌شوند.

## migrationها
- فقط مسئول هر اپ برای مدل‌های آن اپ migration می‌سازد.
- اگر به مدل اپ دیگری نیاز دارید، با مسئولش هماهنگ کنید.

## امنیت
- فایل `.env` هرگز commit نمی‌شود. متغیر جدید را بدون مقدار به `.env.example` اضافه کنید.