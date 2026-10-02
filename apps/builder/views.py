# Create your views here.
from django.db import models
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Category, Form
from .serializers import CategorySerializer, FormSerializer


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