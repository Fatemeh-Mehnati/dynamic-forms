from django.contrib import admin

from .models import Answer, AnswerChoice, Submission

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "form", "user", "process_run", "submitted_at")
    list_filter = ("submitted_at",)
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "question", "text_value", "number_value")


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "answer", "choice")
