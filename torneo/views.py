from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .grupos import actualizar_estados, clasificacion_grupo, obtener_clasificados, obtener_mejor_cuarto
from .models import Grupo, Juego, Pareja, Partida, Ronda
from . import whatsapp


def crear_partida_libre(request):
    if request.method == "POST":
        nombre_1 = request.POST.get("nombre_1", "").strip()
        nombre_2 = request.POST.get("nombre_2", "").strip()
        piedras = int(request.POST.get("piedras", 40))
        juegos = int(request.POST.get("juegos", 4))

        if not nombre_1 or not nombre_2:
            return render(request, "torneo/partida_libre.html", {
                "error": "Debes poner nombre a las dos parejas.",
            })

        p1 = Pareja.objects.create(nombre=nombre_1, jugador1=nombre_1, jugador2="")
        p2 = Pareja.objects.create(nombre=nombre_2, jugador1=nombre_2, jugador2="")

        partida = Partida.objects.create(
            pareja_1=p1,
            pareja_2=p2,
            es_amistoso=True,
            piedras_objetivo=piedras,
            juegos_para_ganar=juegos,
        )

        return render(request, "torneo/partida_libre_creada.html", {
            "partida": partida,
            "pareja_1": p1,
            "pareja_2": p2,
        })

    return render(request, "torneo/partida_libre.html")


def inicio(request):
    actualizar_estados()
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
    actualizar_estados()
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
    actualizar_estados()
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
    """Devuelve la partida activa (en curso o esperando confirmacion de inicio)."""
    _select = ("pareja_1", "pareja_2", "ronda", "inicio_solicitado_por")
    # Partida amistosa activa
    amistosa = Partida.objects.filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja),
        es_amistoso=True,
    ).exclude(
        estado=Partida.Estado.FINALIZADA,
    ).select_related(*_select).first()
    if amistosa:
        return amistosa
    # Partida de torneo en curso
    en_curso = Partida.objects.filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja),
        es_amistoso=False,
        estado=Partida.Estado.EN_CURSO,
    ).select_related(*_select).first()
    if en_curso:
        return en_curso
    # Partida con inicio solicitado (esperando confirmacion del rival)
    con_inicio = Partida.objects.filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja),
        es_amistoso=False,
        estado=Partida.Estado.PENDIENTE,
        inicio_solicitado_por__isnull=False,
    ).select_related(*_select).first()
    if con_inicio:
        return con_inicio
    return None


def _get_partidas_disponibles(pareja):
    """Partidas pendientes de jornadas activas (se pueden empezar)."""
    return Partida.objects.filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja),
        es_amistoso=False,
        estado=Partida.Estado.PENDIENTE,
        inicio_solicitado_por__isnull=True,
        ronda__estado=Ronda.Estado.EN_CURSO,
    ).select_related("pareja_1", "pareja_2", "ronda").order_by("ronda__numero")


def _get_partidas_futuras(pareja):
    """Partidas de jornadas que aun no han empezado."""
    return Partida.objects.filter(
        Q(pareja_1=pareja) | Q(pareja_2=pareja),
        es_amistoso=False,
        estado=Partida.Estado.PENDIENTE,
        ronda__estado=Ronda.Estado.PENDIENTE,
    ).select_related("pareja_1", "pareja_2", "ronda").order_by("ronda__numero")


def panel_pareja(request, token):
    actualizar_estados()
    pareja = get_object_or_404(Pareja, token=token)
    partida_actual = _get_partida_actual(pareja)
    partidas_disponibles = _get_partidas_disponibles(pareja)
    partidas_futuras = _get_partidas_futuras(pareja)

    # Juegos confirmados de la partida actual
    juegos_partida = []
    esperando_confirmacion = False
    if partida_actual and partida_actual.estado in (Partida.Estado.EN_CURSO, Partida.Estado.FINALIZADA):
        juegos_partida = partida_actual.juegos.filter(
            estado=Juego.Estado.CONFIRMADO
        ).select_related("ganador_juego")
        esperando_confirmacion = partida_actual.juegos.filter(
            estado=Juego.Estado.PENDIENTE_CONFIRMACION,
            subido_por=pareja,
        ).exists()

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

    hay_actividad = pendientes.exists() or (
        partida_actual and partida_actual.estado in [
            Partida.Estado.PENDIENTE, Partida.Estado.EN_CURSO
        ]
    )

    ctx = {
        "pareja": pareja,
        "partida_actual": partida_actual,
        "partidas_disponibles": partidas_disponibles,
        "partidas_futuras": partidas_futuras,
        "juegos_partida": juegos_partida,
        "pendientes": pendientes,
        "esperando_confirmacion": esperando_confirmacion,
        "historial": historial,
    }
    ctx.update(_contexto_partida(pareja, partida_actual))
    return render(request, "torneo/panel_pareja.html", ctx)


def _contexto_partida(pareja, partida):
    """Calcula variables de perspectiva: tu resultado siempre a la izquierda."""
    if not partida:
        return {}
    es_p1 = partida.pareja_1 == pareja
    return {
        "mi_pareja": partida.pareja_1 if es_p1 else partida.pareja_2,
        "rival": partida.pareja_2 if es_p1 else partida.pareja_1,
        "mis_juegos": partida.juegos_pareja_1() if es_p1 else partida.juegos_pareja_2(),
        "sus_juegos": partida.juegos_pareja_2() if es_p1 else partida.juegos_pareja_1(),
        "es_p1": es_p1,
    }


def panel_pareja_parcial(request, token):
    """Devuelve solo la seccion activa del panel (para polling)."""
    pareja = get_object_or_404(Pareja, token=token)
    actualizar_estados()
    partida_actual = _get_partida_actual(pareja)
    partidas_disponibles = _get_partidas_disponibles(pareja)
    partidas_futuras = _get_partidas_futuras(pareja)

    juegos_partida = []
    esperando_confirmacion = False
    if partida_actual and partida_actual.estado in (Partida.Estado.EN_CURSO, Partida.Estado.FINALIZADA):
        juegos_partida = partida_actual.juegos.filter(
            estado=Juego.Estado.CONFIRMADO
        ).select_related("ganador_juego")
        esperando_confirmacion = partida_actual.juegos.filter(
            estado=Juego.Estado.PENDIENTE_CONFIRMACION,
            subido_por=pareja,
        ).exists()

    pendientes = Juego.objects.filter(
        estado=Juego.Estado.PENDIENTE_CONFIRMACION,
    ).exclude(
        subido_por=pareja,
    ).filter(
        Q(partida__pareja_1=pareja) | Q(partida__pareja_2=pareja)
    ).select_related("partida__pareja_1", "partida__pareja_2")

    ctx = {
        "pareja": pareja,
        "partida_actual": partida_actual,
        "partidas_disponibles": partidas_disponibles,
        "partidas_futuras": partidas_futuras,
        "juegos_partida": juegos_partida,
        "pendientes": pendientes,
        "esperando_confirmacion": esperando_confirmacion,
    }
    ctx.update(_contexto_partida(pareja, partida_actual))
    return render(request, "torneo/panel_pareja_parcial.html", ctx)


def solicitar_inicio(request, token, partida_id=None):
    pareja = get_object_or_404(Pareja, token=token)

    if partida_id:
        partida = get_object_or_404(
            Partida,
            pk=partida_id,
        )
        if partida.pareja_1 != pareja and partida.pareja_2 != pareja:
            raise Http404
    else:
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
            if not partida.es_amistoso:
                whatsapp.notificar_inicio_partida(partida)

    return redirect("panel_pareja", token=token)


def cancelar_inicio(request, token, partida_id):
    pareja = get_object_or_404(Pareja, token=token)
    partida = get_object_or_404(Partida, pk=partida_id)

    if partida.pareja_1 != pareja and partida.pareja_2 != pareja:
        raise Http404

    if request.method == "POST" and partida.estado == Partida.Estado.PENDIENTE and partida.inicio_solicitado_por == pareja:
        partida.inicio_solicitado_por = None
        partida.save()

    return redirect("panel_pareja", token=token)


def subir_juego(request, token):
    pareja = get_object_or_404(Pareja, token=token)
    partida = _get_partida_actual(pareja)

    if not partida or partida.estado != Partida.Estado.EN_CURSO:
        return redirect("panel_pareja", token=token)

    if request.method == "POST":
        # Proteccion: no crear juego si ya hay uno pendiente de confirmar
        hay_pendiente = partida.juegos.filter(
            estado=Juego.Estado.PENDIENTE_CONFIRMACION
        ).exists()
        if hay_pendiente:
            return redirect("panel_pareja", token=token)

        ganador_num = request.POST.get("ganador", "")
        objetivo = partida.piedras_objetivo

        try:
            piedras_perdedor = int(request.POST.get("piedras_perdedor", -1))
        except (ValueError, TypeError):
            piedras_perdedor = -1

        if ganador_num not in ("1", "2"):
            return redirect("panel_pareja", token=token)

        if piedras_perdedor < 0 or piedras_perdedor >= objetivo:
            return redirect("panel_pareja", token=token)

        if ganador_num == "1":
            ganador = partida.pareja_1
            piedras_1 = objetivo
            piedras_2 = piedras_perdedor
        else:
            ganador = partida.pareja_2
            piedras_1 = piedras_perdedor
            piedras_2 = objetivo

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
            if not juego.partida.es_amistoso:
                whatsapp.notificar_juego(juego)
            juego.partida.comprobar_ganador()
            if juego.partida.estado == Partida.Estado.FINALIZADA:
                juego.partida.fecha_fin = timezone.now()
                juego.partida.save()
                if not juego.partida.es_amistoso:
                    whatsapp.notificar_fin_partida(juego.partida)
        elif accion == "rechazar":
            juego.estado = Juego.Estado.RECHAZADO
            juego.save()

        return redirect("panel_pareja", token=token)

    return render(request, "torneo/confirmar_juego.html", {
        "pareja": pareja, "juego": juego,
    })
