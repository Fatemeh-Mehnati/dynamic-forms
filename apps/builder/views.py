
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


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            owner=self.request.user
        ).order_by("id")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


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
