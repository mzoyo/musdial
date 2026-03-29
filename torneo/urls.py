from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("clasificacion/", views.clasificacion, name="clasificacion"),
    path("ronda/<int:numero>/", views.ronda_detalle, name="ronda_detalle"),
    path("partida/<int:pk>/", views.partida_detalle, name="partida_detalle"),
    # Panel privado de pareja
    path("pareja/<str:token>/", views.panel_pareja, name="panel_pareja"),
    path("pareja/<str:token>/iniciar/", views.solicitar_inicio, name="solicitar_inicio"),
    path("pareja/<str:token>/subir/", views.subir_juego, name="subir_juego"),
    path(
        "pareja/<str:token>/confirmar/<int:juego_id>/",
        views.confirmar_juego,
        name="confirmar_juego",
    ),
]
