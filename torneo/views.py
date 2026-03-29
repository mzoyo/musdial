from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Juego, Pareja, Partida, Ronda
from .swiss import calcular_clasificacion


def inicio(request):
    rondas = Ronda.objects.all()
    ronda_actual = rondas.filter(estado=Ronda.Estado.EN_CURSO).first()
    return render(request, "torneo/inicio.html", {
        "rondas": rondas,
        "ronda_actual": ronda_actual,
    })


def clasificacion(request):
    tabla = calcular_clasificacion()
    return render(request, "torneo/clasificacion.html", {"tabla": tabla})


def ronda_detalle(request, numero):
    ronda = get_object_or_404(Ronda, numero=numero)
    partidas = ronda.partidas.select_related("pareja_1", "pareja_2", "ganador")
    return render(request, "torneo/ronda.html", {
        "ronda": ronda,
        "partidas": partidas,
    })


def partida_detalle(request, pk):
    partida = get_object_or_404(
        Partida.objects.select_related("pareja_1", "pareja_2", "ganador", "ronda"),
        pk=pk,
    )
    juegos = partida.juegos.filter(
        estado=Juego.Estado.CONFIRMADO
    ).select_related("ganador_juego")
    return render(request, "torneo/partida.html", {
        "partida": partida,
        "juegos": juegos,
    })


# --- Panel de pareja (token privado) ---


def _get_partida_actual(pareja):
    return Partida.objects.filter(
        ronda__estado=Ronda.Estado.EN_CURSO,
    ).filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja)
    ).select_related(
        "pareja_1", "pareja_2", "ronda", "inicio_solicitado_por"
    ).first()


def panel_pareja(request, token):
    pareja = get_object_or_404(Pareja, token=token)
    partida_actual = _get_partida_actual(pareja)

    # Juegos pendientes de confirmar por esta pareja
    pendientes = Juego.objects.filter(
        estado=Juego.Estado.PENDIENTE_CONFIRMACION,
    ).exclude(
        subido_por=pareja,
    ).filter(
        Q(partida__pareja_1=pareja) | Q(partida__pareja_2=pareja)
    ).select_related("partida__pareja_1", "partida__pareja_2")

    return render(request, "torneo/panel_pareja.html", {
        "pareja": pareja,
        "partida_actual": partida_actual,
        "pendientes": pendientes,
    })


def solicitar_inicio(request, token):
    pareja = get_object_or_404(Pareja, token=token)
    partida = _get_partida_actual(pareja)

    if not partida or partida.estado != Partida.Estado.PENDIENTE:
        return redirect("panel_pareja", token=token)

    if request.method == "POST":
        if partida.inicio_solicitado_por is None:
            # Primera pareja solicita inicio
            partida.inicio_solicitado_por = pareja
            partida.save()
        elif partida.inicio_solicitado_por != pareja:
            # La otra pareja confirma → partida en curso
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

        # Validar que exactamente una sea 40
        if (piedras_1 == 40) == (piedras_2 == 40):
            error = (
                "Una de las dos parejas debe tener 40 piedras."
                if piedras_1 != 40
                else "Las dos parejas no pueden tener 40 piedras."
            )
            return render(request, "torneo/subir_juego.html", {
                "pareja": pareja,
                "partida": partida,
                "error": error,
            })

        if piedras_1 < 0 or piedras_2 < 0 or piedras_1 > 40 or piedras_2 > 40:
            return render(request, "torneo/subir_juego.html", {
                "pareja": pareja,
                "partida": partida,
                "error": "Las piedras deben estar entre 0 y 40.",
            })

        ganador = partida.pareja_1 if piedras_1 == 40 else partida.pareja_2

        ultimo = partida.juegos.order_by("-numero").first()
        numero = (ultimo.numero + 1) if ultimo else 1

        Juego.objects.create(
            partida=partida,
            numero=numero,
            piedras_1=piedras_1,
            piedras_2=piedras_2,
            ganador_juego=ganador,
            subido_por=pareja,
        )

        return redirect("panel_pareja", token=token)

    return render(request, "torneo/subir_juego.html", {
        "pareja": pareja,
        "partida": partida,
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
        "pareja": pareja,
        "juego": juego,
    })
