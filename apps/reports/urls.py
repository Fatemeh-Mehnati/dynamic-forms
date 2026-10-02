from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FormReportView, ProcessReportView, ReportScheduleViewSet

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

router = DefaultRouter()
router.register(
    "report-schedules",
    ReportScheduleViewSet,
    basename="report-schedule",
)

urlpatterns += router.urls