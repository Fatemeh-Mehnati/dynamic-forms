from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from common.views import HealthView, WhoAmIView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("whoami/", WhoAmIView.as_view(), name="whoami"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Each app adds its routes here, e.g.:
    # path("forms/", include("apps.builder.urls")),
]