from django.contrib import admin

from .models import Category, Form, Choice, Question


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("created_at",)


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "category",
        "is_public",
        "created_at",
    )
    search_fields = ("title", "slug")
    list_filter = ("type", "is_required", "is_active",)
    ordering = ("form", "order",)


    