from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .grupos import clasificacion_grupo, obtener_clasificados, obtener_mejor_cuarto
from .models import Grupo, Juego, Pareja, Partida, Ronda


def inicio(request):
    grupos = Grupo.objects.prefetch_related("parejas").all()
    jornadas = Ronda.objects.filter(fase=Ronda.Fase.CLASIFICATORIA)
    rondas_elim = Ronda.objects.exclude(fase=Ronda.Fase.CLASIFICATORIA)
    total = Partida.objects.filter(ronda__fase=Ronda.Fase.CLASIFICATORIA).count()
    finalizadas = Partida.objects.filter(
        ronda__fase=Ronda.Fase.CLASIFICATORIA, estado=Partida.Estado.FINALIZADA
    ).count()
    return render(request, "torneo/inicio.html", {
        "grupos": grupos,
        "jornadas": jornadas,
        "rondas_elim": rondas_elim,
        "partidas_total": total,
        "partidas_finalizadas": finalizadas,
    })


def grupo_detalle(request, nombre):
    grupo = get_object_or_404(Grupo, nombre=nombre.upper())
    tabla = clasificacion_grupo(grupo)
    jornadas_data = []
    for ronda in Ronda.objects.filter(fase=Ronda.Fase.CLASIFICATORIA):
        partidas = Partida.objects.filter(
            grupo=grupo, ronda=ronda
        ).select_related("pareja_1", "pareja_2", "ganador")
        jornadas_data.append({"ronda": ronda, "partidas": partidas})
    return render(request, "torneo/grupo.html", {
        "grupo": grupo,
        "tabla": tabla,
        "jornadas": jornadas_data,
    })


def clasificacion(request):
    grupos_data = []
    for grupo in Grupo.objects.all():
        grupos_data.append({
            "grupo": grupo,
            "tabla": clasificacion_grupo(grupo),
        })
    cuartos = obtener_mejor_cuarto()
    return render(request, "torneo/clasificacion.html", {
        "grupos_data": grupos_data,
        "cuartos": cuartos,
    })


def partida_detalle(request, pk):
    partida = get_object_or_404(
        Partida.objects.select_related("pareja_1", "pareja_2", "ganador", "ronda", "grupo"),
        pk=pk,
    )
    juegos = partida.juegos.filter(
        estado=Juego.Estado.CONFIRMADO
    ).select_related("ganador_juego")
    return render(request, "torneo/partida.html", {
        "partida": partida,
        "juegos": juegos,
    })


def ronda_detalle(request, numero):
    ronda = get_object_or_404(Ronda, numero=numero)
    partidas = ronda.partidas.select_related("pareja_1", "pareja_2", "ganador")
    return render(request, "torneo/ronda.html", {
        "ronda": ronda,
        "partidas": partidas,
    })


# --- Panel de pareja (token privado) ---


def _get_partida_actual(pareja):
    return Partida.objects.filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja)
    ).filter(
        estado__in=[Partida.Estado.PENDIENTE, Partida.Estado.EN_CURSO]
    ).select_related(
        "pareja_1", "pareja_2", "ronda", "inicio_solicitado_por"
    ).order_by("ronda__numero").first()


def panel_pareja(request, token):
    pareja = get_object_or_404(Pareja, token=token)
    partida_actual = _get_partida_actual(pareja)

    pendientes = Juego.objects.filter(
        estado=Juego.Estado.PENDIENTE_CONFIRMACION,
    ).exclude(
        subido_por=pareja,
    ).filter(
        Q(partida__pareja_1=pareja) | Q(partida__pareja_2=pareja)
    ).select_related("partida__pareja_1", "partida__pareja_2")

    # Partidas finalizadas de esta pareja
    historial = Partida.objects.filter(
        estado=Partida.Estado.FINALIZADA,
    ).filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja)
    ).select_related("pareja_1", "pareja_2", "ganador").order_by("-fecha_fin")[:10]

    return render(request, "torneo/panel_pareja.html", {
        "pareja": pareja,
        "partida_actual": partida_actual,
        "pendientes": pendientes,
        "historial": historial,
    })


def solicitar_inicio(request, token):
    pareja = get_object_or_404(Pareja, token=token)
    partida = _get_partida_actual(pareja)

    if not partida or partida.estado != Partida.Estado.PENDIENTE:
        return redirect("panel_pareja", token=token)

    if request.method == "POST":
        if partida.inicio_solicitado_por is None:
            partida.inicio_solicitado_por = pareja
            partida.save()
        elif partida.inicio_solicitado_por != pareja:
            partida.estado = Partida.Estado.EN_CURSO
            partida.fecha_inicio = timezone.now()
            partida.save()

    return redirect("panel_pareja", token=token)


def subir_juego(request, token):
    pareja = get_object_or_404(Pareja, token=token)
    partida = _get_partida_actual(pareja)

    if not partida or partida.estado != Partida.Estado.EN_CURSO:
        return redirect("panel_pareja", token=token)

    if request.method == "POST":
        try:
            piedras_1 = int(request.POST.get("piedras_1", 0))
            piedras_2 = int(request.POST.get("piedras_2", 0))
        except (ValueError, TypeError):
            piedras_1, piedras_2 = 0, 0

        if (piedras_1 == 40) == (piedras_2 == 40):
            error = (
                "Una de las dos parejas debe tener 40 piedras."
                if piedras_1 != 40
                else "Las dos parejas no pueden tener 40 piedras."
            )
            return render(request, "torneo/subir_juego.html", {
                "pareja": pareja, "partida": partida, "error": error,
            })

        if piedras_1 < 0 or piedras_2 < 0 or piedras_1 > 40 or piedras_2 > 40:
            return render(request, "torneo/subir_juego.html", {
                "pareja": pareja, "partida": partida,
                "error": "Las piedras deben estar entre 0 y 40.",
            })

        ganador = partida.pareja_1 if piedras_1 == 40 else partida.pareja_2
        ultimo = partida.juegos.order_by("-numero").first()
        numero = (ultimo.numero + 1) if ultimo else 1

        Juego.objects.create(
            partida=partida, numero=numero,
            piedras_1=piedras_1, piedras_2=piedras_2,
            ganador_juego=ganador, subido_por=pareja,
        )
        return redirect("panel_pareja", token=token)

    return render(request, "torneo/subir_juego.html", {
        "pareja": pareja, "partida": partida,
    })


def confirmar_juego(request, token, juego_id):
    pareja = get_object_or_404(Pareja, token=token)
    juego = get_object_or_404(Juego, pk=juego_id)

    if juego.rival_confirma != pareja:
        raise Http404

    if juego.estado != Juego.Estado.PENDIENTE_CONFIRMACION:
        return redirect("panel_pareja", token=token)

    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion == "confirmar":
            juego.estado = Juego.Estado.CONFIRMADO
            juego.timestamp_confirmacion = timezone.now()
            juego.save()
            juego.partida.comprobar_ganador()
            if juego.partida.estado == Partida.Estado.FINALIZADA:
                juego.partida.fecha_fin = timezone.now()
                juego.partida.save()
        elif accion == "rechazar":
            juego.estado = Juego.Estado.RECHAZADO
            juego.save()

        return redirect("panel_pareja", token=token)

    return render(request, "torneo/confirmar_juego.html", {
        "pareja": pareja, "juego": juego,
    })
