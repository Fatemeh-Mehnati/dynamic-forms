from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Public endpoint to check that the API is up."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response({"status": "ok"})


class WhoAmIView(APIView):
    """Returns the current user and which auth method was used (JWT or session)."""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "auth_method": type(request.successful_authenticator).__name__,
            }
        )