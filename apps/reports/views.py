from django.db.models import Avg, Max, Min
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.builder.models import Form
from apps.processes.models import Process
from apps.responses.models import Answer, AnswerChoice, Submission

from .models import ReportSchedule, Visit
from .serializers import ReportScheduleSerializer


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


class ProcessReportView(APIView):
    """
    Return aggregated report data for a process.

    Only the process owner can access the report.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, process_id):
        process = get_object_or_404(Process, pk=process_id)

        if process.owner_id != request.user.id:
            raise PermissionDenied(
                "You do not have permission to view this report."
            )

        runs = process.runs.all()
        steps = process.steps.all().select_related("form")

        report = {
            "process": {
                "id": process.id,
                "title": process.title,
            },
            "summary": {
                "visits": Visit.objects.filter(process=process).count(),
                "runs_started": runs.count(),
                "runs_completed": runs.filter(
                    completed_at__isnull=False
                ).count(),
            },
            "steps": [],
        }

        runs_started = runs.count()

        for step in steps:
            submissions = Submission.objects.filter(
                form=step.form,
                process_run__process=process,
            )

            submissions_count = submissions.count()

            completion_percentage = (
                round((submissions_count / runs_started) * 100, 2)
                if runs_started
                else 0
            )

            report["steps"].append(
                {
                    "step_id": step.id,
                    "form_id": step.form_id,
                    "order": step.order,
                    "submissions": submissions_count,
                    "completion_percentage": completion_percentage,
                }
            )

        return Response(report, status=status.HTTP_200_OK)


class ReportScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ReportSchedule.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
