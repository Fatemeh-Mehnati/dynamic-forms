from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    FormDetailView,
    FormListCreateView,
    PrivateFormAccessView,
    PublicFormView,
    QuestionDetailView,
    QuestionListCreateView,
)

urlpatterns = [
    path("categories/", CategoryListCreateView.as_view(), name="category-list-create"),
    path(
        "categories/<int:pk>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("forms/", FormListCreateView.as_view(), name="form-list-create"),
    path("forms/<int:pk>/", FormDetailView.as_view(), name="form-detail"),
    path(
        "forms/<int:form_id>/questions/",
        QuestionListCreateView.as_view(),
        name="question-list-create",
    ),
    path(
        "forms/<int:form_id>/questions/<int:question_id>/",
        QuestionDetailView.as_view(),
        name="question-detail",
    ),
    path(
        "public/forms/<slug:slug>/",
        PublicFormView.as_view(),
        name="public-form-detail",
    ),
    path(
        "public/forms/<slug:slug>/access/",
        PrivateFormAccessView.as_view(),
        name="private-form-access",
    ),
]