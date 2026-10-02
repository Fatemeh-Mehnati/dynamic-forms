from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("responses/", views.responses_page, name="responses"),
]
