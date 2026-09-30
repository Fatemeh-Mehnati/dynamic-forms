from django.contrib import admin
from .models import Process, ProcessRun, ProcessStep


class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 0


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "category", "mode", "is_public", "created_at")
    search_fields = ("title", "slug")
    list_filter = ("mode", "is_public", "created_at")
    inlines = [ProcessStepInline]


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ("id", "process", "form", "order")
    list_filter = ("process",)
    ordering = ("process", "order")


@admin.register(ProcessRun)
class ProcessRunAdmin(admin.ModelAdmin):
    list_display = ("id", "process", "user", "started_at", "completed_at")
    list_filter = ("process",)
    readonly_fields = ("respondent_token",)
