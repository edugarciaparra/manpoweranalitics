from django.contrib import admin

from .models import ConsultaIA


@admin.register(ConsultaIA)
class ConsultaIAAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "pregunta", "tipo", "filas", "segundos", "proveedor")
    list_filter = ("tipo", "proveedor")
    search_fields = ("pregunta", "sql")
    readonly_fields = [f.name for f in ConsultaIA._meta.fields]
