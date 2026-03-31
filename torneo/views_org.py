from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .grupos import (
    clasificacion_grupo,
    generar_eliminatorias,
    generar_todas_las_partidas,
    obtener_clasificados,
    obtener_mejor_cuarto,
)
from .models import Grupo, Juego, Pareja, Partida, Ronda


@staff_member_required(login_url="/organizacion/login/")
def dashboard(request):
    grupos = Grupo.objects.prefetch_related("parejas").all()
    parejas_count = Pareja.objects.filter(activa=True).count()
    partidas_total = Partida.objects.filter(ronda__fase=Ronda.Fase.CLASIFICATORIA).count()
    partidas_finalizadas = Partida.objects.filter(
        ronda__fase=Ronda.Fase.CLASIFICATORIA, estado=Partida.Estado.FINALIZADA
    ).count()
    juegos_rechazados = Juego.objects.filter(estado=Juego.Estado.RECHAZADO).count()
    torneo_iniciado = partidas_total > 0

    return render(request, "organizacion/dashboard.html", {
        "grupos": grupos,
        "parejas_count": parejas_count,
        "partidas_total": partidas_total,
        "partidas_finalizadas": partidas_finalizadas,
        "juegos_rechazados": juegos_rechazados,
        "torneo_iniciado": torneo_iniciado,
    })


@staff_member_required(login_url="/organizacion/login/")
def parejas_lista(request):
    parejas = Pareja.objects.select_related("grupo").all()
    grupos = Grupo.objects.all()
    return render(request, "organizacion/parejas.html", {
        "parejas": parejas,
        "grupos": grupos,
    })


@staff_member_required(login_url="/organizacion/login/")
def pareja_crear(request):
    grupos = Grupo.objects.all()
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        jugador1 = request.POST.get("jugador1", "").strip()
        jugador2 = request.POST.get("jugador2", "").strip()
        grupo_id = request.POST.get("grupo")
        if nombre and jugador1 and jugador2:
            grupo = Grupo.objects.filter(pk=grupo_id).first() if grupo_id else None
            Pareja.objects.create(
                nombre=nombre, jugador1=jugador1, jugador2=jugador2, grupo=grupo
            )
            return redirect("org_parejas")
    return render(request, "organizacion/pareja_form.html", {"grupos": grupos})


@staff_member_required(login_url="/organizacion/login/")
def pareja_editar(request, pk):
    pareja = get_object_or_404(Pareja, pk=pk)
    grupos = Grupo.objects.all()
    if request.method == "POST":
        pareja.nombre = request.POST.get("nombre", pareja.nombre).strip()
        pareja.jugador1 = request.POST.get("jugador1", pareja.jugador1).strip()
        pareja.jugador2 = request.POST.get("jugador2", pareja.jugador2).strip()
        pareja.activa = request.POST.get("activa") == "on"
        grupo_id = request.POST.get("grupo")
        pareja.grupo = Grupo.objects.filter(pk=grupo_id).first() if grupo_id else None
        pareja.save()
        return redirect("org_parejas")
    return render(request, "organizacion/pareja_form.html", {
        "pareja": pareja,
        "grupos": grupos,
    })


@staff_member_required(login_url="/organizacion/login/")
def grupos_lista(request):
    grupos = Grupo.objects.prefetch_related("parejas").all()
    torneo_iniciado = Partida.objects.filter(ronda__fase=Ronda.Fase.CLASIFICATORIA).exists()
    puede_generar_eliminatorias = (
        torneo_iniciado
        and not Ronda.objects.filter(fase=Ronda.Fase.OCTAVOS).exists()
    )
    return render(request, "organizacion/grupos.html", {
        "grupos": grupos,
        "torneo_iniciado": torneo_iniciado,
        "puede_generar_eliminatorias": puede_generar_eliminatorias,
    })


@staff_member_required(login_url="/organizacion/login/")
def iniciar_torneo(request):
    if request.method == "POST":
        if not Partida.objects.filter(ronda__fase=Ronda.Fase.CLASIFICATORIA).exists():
            generar_todas_las_partidas()
    return redirect("org_grupos")


@staff_member_required(login_url="/organizacion/login/")
def grupo_detalle_org(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    tabla = clasificacion_grupo(grupo)
    partidas = Partida.objects.filter(
        grupo=grupo, ronda__fase=Ronda.Fase.CLASIFICATORIA
    ).select_related("pareja_1", "pareja_2", "ganador", "inicio_solicitado_por")
    return render(request, "organizacion/grupo_detalle.html", {
        "grupo": grupo,
        "tabla": tabla,
        "partidas": partidas,
    })


@staff_member_required(login_url="/organizacion/login/")
def generar_octavos(request):
    if request.method == "POST":
        generar_eliminatorias()
    return redirect("org_grupos")


@staff_member_required(login_url="/organizacion/login/")
def metricas(request):
    partidas_rapidas = []
    for p in Partida.objects.filter(
        estado=Partida.Estado.FINALIZADA,
        fecha_inicio__isnull=False,
        fecha_fin__isnull=False,
    ):
        duracion = (p.fecha_fin - p.fecha_inicio).total_seconds() / 60
        if duracion < 10:
            partidas_rapidas.append({"partida": p, "duracion_min": round(duracion, 1)})

    juegos_sospechosos = Juego.objects.filter(
        estado=Juego.Estado.CONFIRMADO,
    ).filter(
        Q(piedras_1=40, piedras_2=0) | Q(piedras_1=0, piedras_2=40)
    ).select_related("partida__pareja_1", "partida__pareja_2")

    juegos_rechazados = Juego.objects.filter(
        estado=Juego.Estado.RECHAZADO,
    ).select_related("partida__pareja_1", "partida__pareja_2", "subido_por")

    return render(request, "organizacion/metricas.html", {
        "partidas_rapidas": partidas_rapidas,
        "juegos_sospechosos": juegos_sospechosos,
        "juegos_rechazados": juegos_rechazados,
    })
