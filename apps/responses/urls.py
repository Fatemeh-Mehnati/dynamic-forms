from django.urls import path

from .views import FormSubmitView, SubmissionDetailView, SubmissionListView

urlpatterns = [
    path(
        "public/forms/<slug:slug>/submissions/",
        FormSubmitView.as_view(),
        name="form-submit",
    ),
    path(
        "forms/<int:form_id>/submissions/",
        SubmissionListView.as_view(),
        name="submission-list",
    ),
    path(
        "forms/<int:form_id>/submissions/<int:pk>/",
        SubmissionDetailView.as_view(),
        name="submission-detail",
    ),
]
