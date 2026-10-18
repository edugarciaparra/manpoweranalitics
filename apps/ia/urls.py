from django.urls import path

from . import views

app_name = "ia"

urlpatterns = [
    path("", views.consultar_pagina, name="consultar"),
    path("consultar/", views.consultar, name="consultar_api"),
    path("preguntar/", views.preguntar, name="preguntar"),
]
