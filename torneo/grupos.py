from datetime import datetime

from django.utils.timezone import make_aware

from .models import Grupo, Pareja, Partida, Ronda

# Calendario oficial del torneo
JORNADAS = [
    {"numero": 1, "inicio": "2026-03-21", "fin": "2026-04-05"},
    {"numero": 2, "inicio": "2026-04-06", "fin": "2026-04-19"},
    {"numero": 3, "inicio": "2026-04-20", "fin": "2026-05-03"},
    {"numero": 4, "inicio": "2026-05-04", "fin": "2026-05-17"},
    {"numero": 5, "inicio": "2026-05-18", "fin": "2026-05-31"},
]

ELIMINATORIAS = [
    {"numero": 6, "fase": Ronda.Fase.OCTAVOS, "inicio": "2026-06-01", "fin": "2026-06-07"},
    {"numero": 7, "fase": Ronda.Fase.CUARTOS, "inicio": "2026-06-08", "fin": "2026-06-14"},
]

# Emparejamientos round-robin para 5 equipos (indices 0-4)
# Cada jornada: 2 partidas, 1 equipo descansa
ROUND_ROBIN_5 = [
    [(0, 1), (2, 3)],  # Jornada 1 - descansa 4
    [(0, 2), (1, 4)],  # Jornada 2 - descansa 3
    [(0, 3), (2, 4)],  # Jornada 3 - descansa 1
    [(0, 4), (1, 3)],  # Jornada 4 - descansa 2
    [(1, 2), (3, 4)],  # Jornada 5 - descansa 0
]


def _parse_date(date_str):
    return make_aware(datetime.strptime(date_str, "%Y-%m-%d"))


def generar_todas_las_partidas():
    """
    Genera 5 jornadas con 2 partidas por grupo por jornada.
    Total: 2 x 5 grupos x 5 jornadas = 50 partidas.
    """
    rondas = []
    todas_partidas = []

    for jornada_info in JORNADAS:
        ronda = Ronda.objects.create(
            numero=jornada_info["numero"],
            fase=Ronda.Fase.CLASIFICATORIA,
            estado=Ronda.Estado.EN_CURSO,
            fecha_inicio=_parse_date(jornada_info["inicio"]),
            fecha_limite=_parse_date(jornada_info["fin"]),
        )
        rondas.append(ronda)

        jornada_idx = jornada_info["numero"] - 1
        emparejamientos = ROUND_ROBIN_5[jornada_idx]

        for grupo in Grupo.objects.all():
            parejas = list(grupo.parejas.filter(activa=True).order_by("pk"))
            if len(parejas) < 5:
                continue
            for i, j in emparejamientos:
                partida = Partida.objects.create(
                    ronda=ronda,
                    grupo=grupo,
                    pareja_1=parejas[i],
                    pareja_2=parejas[j],
                )
                todas_partidas.append(partida)

    return rondas, todas_partidas


def clasificacion_grupo(grupo):
    """
    Devuelve la clasificación de un grupo ordenada por:
    1. Puntos (desc)
    2. Enfrentamiento directo
    3. Diferencia de juegos (desc)
    """
    parejas = list(grupo.parejas.filter(activa=True))
    tabla = []
    for pareja in parejas:
        tabla.append({
            "pareja": pareja,
            "puntos": pareja.puntos_grupo(),
            "pj": pareja.partidas_jugadas_grupo(),
            "pg": pareja.victorias_grupo(),
            "pp": pareja.partidas_jugadas_grupo() - pareja.victorias_grupo(),
            "jg": pareja.juegos_ganados_grupo(),
            "jp": pareja.juegos_perdidos_grupo(),
            "dif_juegos": pareja.diferencia_juegos(),
        })

    # Ordenar por puntos, luego diferencia de juegos
    tabla.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)

    # Resolver empates por enfrentamiento directo entre parejas empatadas a puntos
    i = 0
    while i < len(tabla):
        j = i
        while j < len(tabla) and tabla[j]["puntos"] == tabla[i]["puntos"]:
            j += 1
        if j - i == 2:
            p1 = tabla[i]["pareja"]
            p2 = tabla[i + 1]["pareja"]
            if p1.enfrentamiento_directo(p2) < 0:
                tabla[i], tabla[i + 1] = tabla[i + 1], tabla[i]
        i = j

    for pos, entry in enumerate(tabla, 1):
        entry["posicion"] = pos

    return tabla


def obtener_mejor_cuarto():
    """
    Devuelve el mejor 4o clasificado de entre todos los grupos.
    Criterio: puntos, luego diferencia de juegos.
    """
    cuartos = []
    for grupo in Grupo.objects.all():
        tabla = clasificacion_grupo(grupo)
        if len(tabla) >= 4:
            entry = tabla[3]
            entry["grupo"] = grupo
            cuartos.append(entry)

    cuartos.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)
    return cuartos


def obtener_clasificados():
    """
    Devuelve los 16 clasificados: top 3 de cada grupo + mejor 4o.
    """
    clasificados = []
    for grupo in Grupo.objects.all():
        tabla = clasificacion_grupo(grupo)
        for entry in tabla[:3]:
            entry["grupo"] = grupo
            entry["via"] = f"Top 3 Grupo {grupo.nombre}"
            clasificados.append(entry)

    cuartos = obtener_mejor_cuarto()
    if cuartos:
        mejor = cuartos[0]
        mejor["via"] = f"Mejor 4o (Grupo {mejor['grupo'].nombre})"
        clasificados.append(mejor)

    return clasificados


def generar_eliminatorias():
    """
    Genera los octavos de final.
    Seeding: 1os de grupo, luego 2os, luego 3os, luego mejor 4o.
    """
    primeros = []
    segundos = []
    terceros = []

    for grupo in Grupo.objects.all():
        tabla = clasificacion_grupo(grupo)
        if len(tabla) >= 3:
            primeros.append(tabla[0])
            segundos.append(tabla[1])
            terceros.append(tabla[2])

    cuartos = obtener_mejor_cuarto()
    mejor_cuarto = cuartos[0] if cuartos else None

    primeros.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)
    segundos.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)
    terceros.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)

    seeded = (
        [e["pareja"] for e in primeros]
        + [e["pareja"] for e in segundos]
        + [e["pareja"] for e in terceros]
    )
    if mejor_cuarto:
        seeded.append(mejor_cuarto["pareja"])

    if len(seeded) < 16:
        return None, []

    octavos_info = ELIMINATORIAS[0]
    ronda_octavos = Ronda.objects.create(
        numero=octavos_info["numero"],
        fase=octavos_info["fase"],
        estado=Ronda.Estado.EN_CURSO,
        fecha_inicio=_parse_date(octavos_info["inicio"]),
        fecha_limite=_parse_date(octavos_info["fin"]),
    )

    partidas = []
    for i in range(8):
        partida = Partida.objects.create(
            ronda=ronda_octavos,
            pareja_1=seeded[i],
            pareja_2=seeded[15 - i],
        )
        partidas.append(partida)

    return ronda_octavos, partidas
