from django.urls import path

from .views import (
    ProcessDetailView,
    ProcessListCreateView,
    ProcessRunStartView,
    ProcessRunStatusView,
    ProcessRunStepSubmitView,
    ProcessStepCreateView,
    ProcessStepDeleteView,
    ProcessStepReorderView,
)

urlpatterns = [
    path("processes/", ProcessListCreateView.as_view(), name="process-list"),
    path("processes/<int:pk>/", ProcessDetailView.as_view(), name="process-detail"),
    path(
        "processes/<int:process_id>/steps/",
        ProcessStepCreateView.as_view(),
        name="process-step-create",
    ),
    path(
        "processes/<int:process_id>/steps/<int:step_id>/",
        ProcessStepDeleteView.as_view(),
        name="process-step-delete",
    ),
    path(
        "processes/<int:process_id>/steps/reorder/",
        ProcessStepReorderView.as_view(),
        name="process-step-reorder",
    ),
    path(
        "public/processes/<slug:slug>/runs/",
        ProcessRunStartView.as_view(),
        name="process-run-start",
    ),
    path(
        "public/processes/<slug:slug>/runs/<slug:token>/",
        ProcessRunStatusView.as_view(),
        name="process-run-status",
    ),
    path(
        "public/processes/<slug:slug>/runs/<slug:token>/steps/<int:step_id>/submit/",
        ProcessRunStepSubmitView.as_view(),
        name="process-run-step-submit",
    ),
]
