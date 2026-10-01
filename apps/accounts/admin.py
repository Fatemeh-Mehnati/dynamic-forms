from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Contact", {"fields": ("phone",)}),)
    list_display = ("username", "email", "phone", "is_staff")
    search_fields = ("username", "email", "phone")


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("target", "purpose", "attempts", "is_used", "expires_at", "created_at")
    list_filter = ("purpose", "is_used")
    search_fields = ("target",)
    readonly_fields = ("code_hash",)