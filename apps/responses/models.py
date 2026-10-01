from django.conf import settings
from django.db import models


class Submission(models.Model):
    form = models.ForeignKey(
        "builder.Form",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    # null = anonymous respondent
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
    )
    # set only when the submission was made as a step of a process run
    process_run = models.ForeignKey(
        "processes.ProcessRun",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]

    def __str__(self):
        return f"Submission {self.pk} of form {self.form_id}"


class Answer(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        "builder.Question",
        on_delete=models.PROTECT,
        related_name="answers",
    )
    text_value = models.TextField(null=True, blank=True)
    number_value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="unique_answer_submission_question",
            ),
        ]

    def __str__(self):
        return f"Answer {self.pk}"


class AnswerChoice(models.Model):
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="selected_choices",
    )
    choice = models.ForeignKey(
        "builder.Choice",
        on_delete=models.PROTECT,
        related_name="answer_choices",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "choice"],
                name="unique_answerchoice_answer_choice",
            ),
        ]

    def __str__(self):
        return f"{self.answer_id}:{self.choice_id}"
