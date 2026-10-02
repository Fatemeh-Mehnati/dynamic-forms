
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.services import record_visit

from .models import Category, Form, Question
from .serializers import (
    CategorySerializer,
    FormSerializer,
    PublicFormSerializer,
    QuestionSerializer,
)
from .token_utils import (
    create_form_access_token,
    verify_form_access_token,
)

from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,
    extend_schema_view,
)

@extend_schema_view(
    get=extend_schema(
        summary="List categories",
        description="Retrieve all categories belonging to the authenticated user.",
        responses={200: CategorySerializer(many=True)},
        examples=[
            OpenApiExample(
                "Category list response",
                value=[
                    {
                        "id": 1,
                        "name": "Education",
                        "created_at": "2026-10-02T10:00:00Z",
                        "updated_at": "2026-10-02T10:00:00Z",
                    }
                ],
                response_only=True,
                status_codes=["200"],
            )
        ],
    ),
    post=extend_schema(
        summary="Create category",
        description="Create a category for the authenticated user.",
        request=CategorySerializer,
        responses={201: CategorySerializer},
        examples=[
            OpenApiExample(
                "Create category request",
                value={"name": "Education"},
                request_only=True,
            ),
            OpenApiExample(
                "Create category response",
                value={
                    "id": 1,
                    "name": "Education",
                    "created_at": "2026-10-02T10:00:00Z",
                    "updated_at": "2026-10-02T10:00:00Z",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    ),
)
class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            owner=self.request.user
        ).order_by("id")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve category",
        responses={200: CategorySerializer},
    ),
    put=extend_schema(
        summary="Update category",
        request=CategorySerializer,
        responses={200: CategorySerializer},
        examples=[
            OpenApiExample(
                "Update category request",
                value={"name": "Science"},
                request_only=True,
            )
        ],
    ),
    patch=extend_schema(
        summary="Partially update category",
        request=CategorySerializer,
        responses={200: CategorySerializer},
        examples=[
            OpenApiExample(
                "Partial update request",
                value={"name": "Science"},
                request_only=True,
            )
        ],
    ),
    delete=extend_schema(
        summary="Delete category",
        responses={204: None},
    ),
)
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)


class FormListCreateView(generics.ListCreateAPIView):
    serializer_class = FormSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Form.objects.filter(
            owner=self.request.user
        ).order_by("-created_at")

        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")

        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(description__icontains=search)
            )

        if category:
            queryset = queryset.filter(category_id=category)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FormDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FormSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Form.objects.filter(owner=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class QuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_form(self):
        return get_object_or_404(
            Form,
            pk=self.kwargs["form_id"],
            owner=self.request.user,
        )

    def get_queryset(self):
        return Question.objects.filter(
            form=self.get_form(),
        ).order_by("order", "id")

    def perform_create(self, serializer):
        serializer.save(form=self.get_form())


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "question_id"

    def get_queryset(self):
        return Question.objects.filter(
            form__owner=self.request.user,
            form_id=self.kwargs["form_id"],
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

        instance.choices.filter(is_active=True).update(is_active=False)

@extend_schema(
    summary="Retrieve public form",
    description="Retrieve a public form or access a private form using a valid token.",
    responses={
        200: PublicFormSerializer,
        403: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"},
            },
        },
    },
)
class PublicFormView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        form = get_object_or_404(Form, slug=slug)

        if not form.is_public:
            token = request.headers.get("X-Form-Access-Token")

            if not verify_form_access_token(form, token):
                return Response(
                    {"detail": "This form is private. Password required."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        record_visit(request, form=form)
        return Response(PublicFormSerializer(form).data)


class PrivateFormAccessView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Access private form",
        request=None,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "token_type": {"type": "string"},
                },
            },
            400: {"type": "object"},
            403: {"type": "object"},
        },
    )
    def post(self, request, slug):
        form = get_object_or_404(Form, slug=slug)

        if form.is_public:
            return Response(
                {"detail": "This form is public."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = request.data.get("password")

        if not password or not form.check_password(password):
            return Response(
                {"detail": "Invalid password."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token = create_form_access_token(form)

        return Response(
            {
                "access_token": token,
                "token_type": "Bearer",
            },
            status=status.HTTP_200_OK,
        )
