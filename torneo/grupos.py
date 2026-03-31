from itertools import combinations

from .models import Grupo, Pareja, Partida, Ronda


def generar_partidas_grupo(grupo, ronda):
    """
    Genera todas las partidas round-robin para un grupo en una ronda dada.
    5 parejas = 10 partidas por grupo.
    """
    parejas = list(grupo.parejas.filter(activa=True))
    partidas = []
    for p1, p2 in combinations(parejas, 2):
        partida = Partida.objects.create(
            ronda=ronda,
            grupo=grupo,
            pareja_1=p1,
            pareja_2=p2,
        )
        partidas.append(partida)
    return partidas


def generar_todas_las_partidas():
    """
    Genera una ronda clasificatoria con todas las partidas de todos los grupos.
    Total: 10 partidas x 5 grupos = 50 partidas.
    """
    ronda = Ronda.objects.create(
        numero=1,
        fase=Ronda.Fase.CLASIFICATORIA,
        estado=Ronda.Estado.EN_CURSO,
    )
    partidas = []
    for grupo in Grupo.objects.all():
        partidas.extend(generar_partidas_grupo(grupo, ronda))
    return ronda, partidas


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
            # Solo 2 empatadas: enfrentamiento directo
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

    # Ordenar dentro de cada bombo por puntos y dif juegos
    primeros.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)
    segundos.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)
    terceros.sort(key=lambda x: (x["puntos"], x["dif_juegos"]), reverse=True)

    # Seeding: 1-5 primeros, 6-10 segundos, 11-15 terceros, 16 mejor cuarto
    seeded = (
        [e["pareja"] for e in primeros]
        + [e["pareja"] for e in segundos]
        + [e["pareja"] for e in terceros]
    )
    if mejor_cuarto:
        seeded.append(mejor_cuarto["pareja"])

    if len(seeded) < 16:
        return None, []

    ronda_octavos = Ronda.objects.create(
        numero=2,
        fase=Ronda.Fase.OCTAVOS,
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
