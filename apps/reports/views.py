from django.db.models import Avg, Count, Max, Min
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.builder.models import Form
from apps.responses.models import Answer, AnswerChoice, Submission

from .models import Visit

from rest_framework.exceptions import PermissionDenied


class FormReportView(APIView):
    """
    Return aggregated report data for a form.

    Only the form owner can access the report.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, form_id):
        form = get_object_or_404(Form, pk=form_id)

        if form.owner_id != request.user.id:
            raise PermissionDenied("You do not have permission to view this report.")

        submissions = Submission.objects.filter(form=form)

        report = {
            "form": {
                "id": form.id,
                "title": form.title,
            },
            "summary": {
                "visits": Visit.objects.filter(form=form).count(),
                "submissions": submissions.count(),
            },
            "questions": [],
        }

        questions = form.questions.all().order_by("order", "id")

        for question in questions:
            answers = Answer.objects.filter(
                submission__form=form,
                question=question,
            )

            question_data = {
                "question_id": question.id,
                "text": question.text,
                "type": question.type,
                "responses": answers.count(),
            }

            if question.type == "text":
                pass

            elif question.type == "number":
                statistics = answers.aggregate(
                    average=Avg("number_value"),
                    min=Min("number_value"),
                    max=Max("number_value"),
                )

                question_data["statistics"] = statistics

            elif question.type in {"select", "checkbox"}:
                responses = answers.count()

                options = []

                for choice in question.choices.filter(is_active=True).order_by(
                    "order", "id"
                ):
                    count = AnswerChoice.objects.filter(
                        answer__in=answers,
                        choice=choice,
                    ).count()

                    percentage = (
                        round((count / responses) * 100, 2)
                        if responses
                        else 0
                    )

                    options.append(
                        {
                            "choice_id": choice.id,
                            "label": choice.label,
                            "count": count,
                            "percentage": percentage,
                        }
                    )

                question_data["options"] = options

            report["questions"].append(question_data)

        return Response(report, status=status.HTTP_200_OK)