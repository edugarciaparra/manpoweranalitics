from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("<slug:modulo>/", views.modulo, name="modulo"),
    path("<slug:modulo>/rafa/", views.rafa, name="rafa"),
    path("<slug:modulo>/<slug:analisis>/", views.analisis, name="analisis"),
    path("<slug:modulo>/<slug:analisis>/detalle/", views.detalle, name="detalle"),
]
