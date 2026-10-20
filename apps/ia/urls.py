from django.urls import path

from . import views

app_name = "ia"

urlpatterns = [
    path("", views.consultar_pagina, name="consultar"),
    path("consultar/", views.consultar, name="consultar_api"),
    path("preguntar/", views.preguntar, name="preguntar"),
    path("nueva/", views.nueva_conversacion, name="nueva"),
    path("continuar/", views.continuar_conversacion, name="continuar"),
    path("consulta/<int:id_consulta>/", views.consulta_guardada, name="consulta"),
]
