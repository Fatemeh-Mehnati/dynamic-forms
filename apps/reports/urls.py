from django.urls import path

from .views import FormReportView

from .views import ProcessReportView

urlpatterns = [
    path(
        "forms/<int:form_id>/report/",
        FormReportView.as_view(),
        name="form-report",
    ),
    path(
        "processes/<int:process_id>/report/",
        ProcessReportView.as_view(),
        name="process-report",
    ),
]