from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Juego, Pareja, Partida, Ronda
from .swiss import calcular_clasificacion, generar_emparejamientos, generar_eliminatorias


@staff_member_required(login_url="/organizacion/login/")
def dashboard(request):
    parejas = Pareja.objects.filter(activa=True).count()
    rondas = Ronda.objects.all()
    ronda_actual = rondas.filter(estado=Ronda.Estado.EN_CURSO).first()
    partidas_total = Partida.objects.count()
    partidas_finalizadas = Partida.objects.filter(estado=Partida.Estado.FINALIZADA).count()
    juegos_rechazados = Juego.objects.filter(estado=Juego.Estado.RECHAZADO).count()

    return render(request, "organizacion/dashboard.html", {
        "parejas_count": parejas,
        "rondas": rondas,
        "ronda_actual": ronda_actual,
        "partidas_total": partidas_total,
        "partidas_finalizadas": partidas_finalizadas,
        "juegos_rechazados": juegos_rechazados,
    })


@staff_member_required(login_url="/organizacion/login/")
def parejas_lista(request):
    parejas = Pareja.objects.all()
    return render(request, "organizacion/parejas.html", {"parejas": parejas})


@staff_member_required(login_url="/organizacion/login/")
def pareja_crear(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        jugador1 = request.POST.get("jugador1", "").strip()
        jugador2 = request.POST.get("jugador2", "").strip()
        if nombre and jugador1 and jugador2:
            Pareja.objects.create(nombre=nombre, jugador1=jugador1, jugador2=jugador2)
            return redirect("org_parejas")
    return render(request, "organizacion/pareja_form.html")


@staff_member_required(login_url="/organizacion/login/")
def pareja_editar(request, pk):
    pareja = get_object_or_404(Pareja, pk=pk)
    if request.method == "POST":
        pareja.nombre = request.POST.get("nombre", pareja.nombre).strip()
        pareja.jugador1 = request.POST.get("jugador1", pareja.jugador1).strip()
        pareja.jugador2 = request.POST.get("jugador2", pareja.jugador2).strip()
        pareja.activa = request.POST.get("activa") == "on"
        pareja.save()
        return redirect("org_parejas")
    return render(request, "organizacion/pareja_form.html", {"pareja": pareja})


@staff_member_required(login_url="/organizacion/login/")
def rondas_lista(request):
    rondas = Ronda.objects.prefetch_related("partidas").all()
    puede_generar = not Ronda.objects.filter(estado=Ronda.Estado.EN_CURSO).exists()
    clasificatorias_completadas = Ronda.objects.filter(
        fase=Ronda.Fase.CLASIFICATORIA, estado=Ronda.Estado.COMPLETADA,
    ).count()
    puede_generar_eliminatorias = (
        clasificatorias_completadas >= 5
        and not Ronda.objects.filter(fase=Ronda.Fase.OCTAVOS).exists()
    )
    return render(request, "organizacion/rondas.html", {
        "rondas": rondas,
        "puede_generar": puede_generar,
        "puede_generar_eliminatorias": puede_generar_eliminatorias,
    })


@staff_member_required(login_url="/organizacion/login/")
def generar_ronda(request):
    if request.method == "POST":
        if Ronda.objects.filter(estado=Ronda.Estado.EN_CURSO).exists():
            return redirect("org_rondas")
        ultima = Ronda.objects.filter(fase=Ronda.Fase.CLASIFICATORIA).order_by("-numero").first()
        numero = (ultima.numero + 1) if ultima else 1
        ronda = Ronda.objects.create(
            numero=numero,
            estado=Ronda.Estado.EN_CURSO,
            fecha_inicio=timezone.now(),
        )
        generar_emparejamientos(ronda)
    return redirect("org_rondas")


@staff_member_required(login_url="/organizacion/login/")
def completar_ronda(request, pk):
    if request.method == "POST":
        ronda = get_object_or_404(Ronda, pk=pk)
        ronda.estado = Ronda.Estado.COMPLETADA
        ronda.save()
    return redirect("org_rondas")


@staff_member_required(login_url="/organizacion/login/")
def generar_octavos(request):
    if request.method == "POST":
        generar_eliminatorias()
    return redirect("org_rondas")


@staff_member_required(login_url="/organizacion/login/")
def ronda_detalle_org(request, pk):
    ronda = get_object_or_404(Ronda, pk=pk)
    partidas = ronda.partidas.select_related(
        "pareja_1", "pareja_2", "ganador", "inicio_solicitado_por"
    ).prefetch_related("juegos")
    return render(request, "organizacion/ronda_detalle.html", {
        "ronda": ronda,
        "partidas": partidas,
    })


@staff_member_required(login_url="/organizacion/login/")
def metricas(request):
    # Partidas sospechosamente rapidas
    partidas_rapidas = []
    for p in Partida.objects.filter(estado=Partida.Estado.FINALIZADA, fecha_inicio__isnull=False, fecha_fin__isnull=False):
        duracion = (p.fecha_fin - p.fecha_inicio).total_seconds() / 60
        if duracion < 10:
            partidas_rapidas.append({"partida": p, "duracion_min": round(duracion, 1)})

    # Juegos con piedras 40-0 (posible partida pactada)
    juegos_sospechosos = Juego.objects.filter(
        estado=Juego.Estado.CONFIRMADO,
    ).filter(
        Q(piedras_1=40, piedras_2=0) | Q(piedras_1=0, piedras_2=40)
    ).select_related("partida__pareja_1", "partida__pareja_2")

    # Juegos rechazados
    juegos_rechazados = Juego.objects.filter(
        estado=Juego.Estado.RECHAZADO,
    ).select_related("partida__pareja_1", "partida__pareja_2", "subido_por")

    return render(request, "organizacion/metricas.html", {
        "partidas_rapidas": partidas_rapidas,
        "juegos_sospechosos": juegos_sospechosos,
        "juegos_rechazados": juegos_rechazados,
    })
