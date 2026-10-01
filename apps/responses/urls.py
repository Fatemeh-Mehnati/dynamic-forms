from django.urls import path

from .views import FormSubmitView

urlpatterns = [
    path(
        "public/forms/<slug:slug>/submissions/",
        FormSubmitView.as_view(),
        name="form-submit",
    ),
    # C4 adds the owner-only list/detail routes here.
]
