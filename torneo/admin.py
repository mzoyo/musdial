from django.contrib import admin
from django.utils.html import format_html

from .models import Juego, Pareja, Partida, Ronda


class JuegoInline(admin.TabularInline):
    model = Juego
    extra = 0
    readonly_fields = ("timestamp_subida", "timestamp_confirmacion")


@admin.register(Pareja)
class ParejaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "jugador1", "jugador2", "activa", "enlace_pareja")
    list_filter = ("activa",)
    search_fields = ("nombre", "jugador1", "jugador2")
    readonly_fields = ("token", "fecha_registro")

    @admin.display(description="Enlace")
    def enlace_pareja(self, obj):
        return format_html(
            '<a href="/pareja/{}" target="_blank">/pareja/{}</a>',
            obj.token,
            obj.token,
        )


@admin.register(Ronda)
class RondaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "fase", "estado", "fecha_inicio", "fecha_limite")
    list_filter = ("fase", "estado")


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "marcador",
        "ganador",
        "estado",
        "duracion_partida",
    )
    list_filter = ("estado", "ronda")
    inlines = [JuegoInline]

    @admin.display(description="Duración")
    def duracion_partida(self, obj):
        if obj.fecha_inicio and obj.fecha_fin:
            delta = obj.fecha_fin - obj.fecha_inicio
            minutos = int(delta.total_seconds() // 60)
            return f"{minutos} min"
        return "-"


@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = (
        "partida",
        "numero",
        "piedras_1",
        "piedras_2",
        "ganador_juego",
        "estado",
        "subido_por",
    )
    list_filter = ("estado", "partida__ronda")
