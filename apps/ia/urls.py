from django.urls import path

from . import views

app_name = "ia"

urlpatterns = [
    path("preguntar/", views.preguntar, name="preguntar"),
]
