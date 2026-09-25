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

### دستورهای پرکاربرد
```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py shell
docker compose down        # خاموش کردن
docker compose down -v     # خاموش کردن و پاک کردن داده‌های دیتابیس
```