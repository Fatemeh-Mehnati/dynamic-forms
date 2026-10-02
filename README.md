# dynamic-forms
سامانه‌ی ایجاد و مدیریت فرم‌ها و فرایندهای پویا — پروژه‌ی نهایی، با Django REST Framework.

قوانین همکاری: [CONTRIBUTING.md](CONTRIBUTING.md)

## اجرای پروژه (محیط توسعه)

پیش‌نیاز: [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
cp .env.example .env
```
در `.env` یک `SECRET_KEY` قرار دهید:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```
اگر پورت 5432 یا 6379 روی سیستم شما اشغال است، `DB_PORT` یا `REDIS_PORT` را در `.env` عوض کنید.

```bash
docker compose up --build
```
پروژه روی `http://127.0.0.1:8000` در دسترس است. migrationها خودکار اجرا می‌شوند.

- مستندات API (Swagger): `http://127.0.0.1:8000/api/docs/`
- پنل مدیریت: `http://127.0.0.1:8000/admin/`

### دستورهای پرکاربرد
```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py shell
docker compose exec web pytest -v              # اجرای تست‌ها
docker compose exec web ruff check . --fix     # بررسی و اصلاح کد
docker compose down        # خاموش کردن
docker compose down -v     # خاموش کردن و پاک کردن داده‌های دیتابیس
```

## اجرا در حالت production

```bash
cp .env.prod.example .env.prod
```
در `.env.prod`، مقدار `SECRET_KEY` و رمز دیتابیس را تنظیم کنید. رمز باید در `POSTGRES_PASSWORD` و `DATABASE_URL` یکسان باشد. اگر پورت 80 اشغال است، `HTTP_PORT` را عوض کنید.

```bash
docker compose down
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```
پروژه روی `http://localhost` در دسترس است:
- **Nginx** فایل‌های static و media را مستقیم سرو می‌کند و بقیه‌ی درخواست‌ها را به Gunicorn می‌فرستد.
- **Gunicorn** با ۳ worker اجرا می‌شود و از بیرون مستقیم در دسترس نیست.
- migrationها و `collectstatic` قبل از شروع سرور خودکار اجرا می‌شوند.

محیط توسعه و production هر دو از پورت‌های مشترک استفاده می‌کنند، پس هم‌زمان روشن نشوند.

**روی سرور واقعی با HTTPS**، این مقادیر را در `.env.prod` تنظیم کنید:
```
ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com
SECURE_COOKIES=True
SECURE_SSL_REDIRECT=True
```

برای خاموش کردن:
```bash
docker compose -f docker-compose.prod.yml down
```