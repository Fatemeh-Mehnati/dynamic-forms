from django.urls import path

from .views import FormReportView

urlpatterns = [
    path(
        "forms/<int:form_id>/report/",
        FormReportView.as_view(),
        name="form-report",
    ),
]