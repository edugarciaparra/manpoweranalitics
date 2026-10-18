from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ia/", include("apps.ia.urls")),
    # Va al final: /<modulo>/ y /<modulo>/<analisis>/ los resuelve core
    path("", include("apps.core.urls")),
]
