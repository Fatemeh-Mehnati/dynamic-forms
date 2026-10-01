from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.builder.models import Form

from .models import Submission
from .serializers import (
    SubmissionCreatedSerializer,
    SubmissionCreateSerializer,
    SubmissionDetailSerializer,
    SubmissionListSerializer,
)
from .services import submit_form


def has_private_access(form, request):
    """Can this request submit to a private form?

    TODO(B6): verify the short-lived access token issued by the public-form API
    (TimestampSigner) here, e.g. from the X-Form-Access-Token header.
    Until B6 is merged, private forms reject every submission.
    """
    return False


class FormSubmitView(APIView):
    """Submit answers to a form (public forms, or private forms with a token)."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=SubmissionCreateSerializer,
        responses={201: SubmissionCreatedSerializer},
    )
    def post(self, request, slug):
        form = get_object_or_404(Form, slug=slug)
        if not form.is_public and not has_private_access(form, request):
            raise PermissionDenied("This form is private.")

        serializer = SubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        submission = submit_form(form, serializer.validated_data["answers"], user=user)
        return Response(
            SubmissionCreatedSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )


class OwnerFormMixin:
    """Shared lookup: the form must exist and belong to request.user."""

    permission_classes = [IsAuthenticated]

    def get_form(self):
        return get_object_or_404(
            Form, pk=self.kwargs["form_id"], owner=self.request.user
        )


class SubmissionListView(OwnerFormMixin, generics.ListAPIView):
    """Paginated list of submissions for a form, owner only."""

    serializer_class = SubmissionListSerializer

    @extend_schema(responses={200: SubmissionListSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        form = self.get_form()
        return Submission.objects.filter(form=form)


class SubmissionDetailView(OwnerFormMixin, generics.RetrieveAPIView):
    """A single submission with its answers, owner only."""

    serializer_class = SubmissionDetailSerializer

    @extend_schema(responses={200: SubmissionDetailSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        form = self.get_form()
        return Submission.objects.filter(form=form).prefetch_related(
            "answers__question", "answers__selected_choices__choice"
        )
