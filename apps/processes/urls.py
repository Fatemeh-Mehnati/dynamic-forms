from django.urls import path

from .views import (
    ProcessDetailView,
    ProcessListCreateView,
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
]
