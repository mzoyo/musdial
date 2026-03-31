from django.contrib import admin
from django.utils.html import format_html

from .models import Grupo, Juego, Pareja, Partida, Ronda


class JuegoInline(admin.TabularInline):
    model = Juego
    extra = 0
    readonly_fields = ("timestamp_subida", "timestamp_confirmacion")


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("__str__",)


@admin.register(Pareja)
class ParejaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "jugador1", "jugador2", "grupo", "activa", "enlace_pareja")
    list_filter = ("activa", "grupo")
    search_fields = ("nombre", "jugador1", "jugador2")
    readonly_fields = ("token", "fecha_registro")

    @admin.display(description="Enlace")
    def enlace_pareja(self, obj):
        return format_html(
            '<a href="/pareja/{}" target="_blank">/pareja/{}</a>',
            obj.token, obj.token,
        )


@admin.register(Ronda)
class RondaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "fase", "estado")
    list_filter = ("fase", "estado")


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "grupo", "marcador", "ganador", "estado")
    list_filter = ("estado", "grupo", "ronda")
    inlines = [JuegoInline]


@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ("partida", "numero", "piedras_1", "piedras_2", "ganador_juego", "estado", "subido_por")
    list_filter = ("estado",)
