import random

from .models import Pareja, Partida, Ronda


def obtener_rivales_previos(pareja):
    """Devuelve el set de IDs de parejas contra las que ya ha jugado."""
    partidas = Partida.objects.filter(
        ronda__fase=Ronda.Fase.CLASIFICATORIA,
    ).exclude(
        estado=Partida.Estado.PENDIENTE,
    )
    rivales = set()
    for p in partidas.filter(pareja_1=pareja):
        rivales.add(p.pareja_2_id)
    for p in partidas.filter(pareja_2=pareja):
        rivales.add(p.pareja_1_id)
    return rivales


def generar_emparejamientos(ronda):
    """
    Genera los emparejamientos para una ronda del sistema suizo.

    Ronda 1: sorteo puro.
    Rondas siguientes: empareja por puntos similares evitando repeticiones.
    """
    parejas = list(Pareja.objects.filter(activa=True))

    if ronda.numero == 1:
        random.shuffle(parejas)
        return _crear_partidas(ronda, parejas)

    # Ordenar por puntos (desc), buchholz (desc) y aleatorio para desempatar
    parejas.sort(key=lambda p: (p.puntos(), p.buchholz(), random.random()), reverse=True)

    # Obtener rivales previos de cada pareja
    rivales_previos = {p.id: obtener_rivales_previos(p) for p in parejas}

    emparejados = set()
    emparejamientos = []

    for pareja in parejas:
        if pareja.id in emparejados:
            continue

        # Buscar el mejor rival disponible (puntuación más cercana, no jugado antes)
        mejor_rival = None
        for candidato in parejas:
            if candidato.id == pareja.id:
                continue
            if candidato.id in emparejados:
                continue
            if candidato.id in rivales_previos[pareja.id]:
                continue
            mejor_rival = candidato
            break

        if mejor_rival is None:
            # Si no hay rival sin repetición, permite repetición
            for candidato in parejas:
                if candidato.id != pareja.id and candidato.id not in emparejados:
                    mejor_rival = candidato
                    break

        if mejor_rival:
            emparejamientos.append((pareja, mejor_rival))
            emparejados.add(pareja.id)
            emparejados.add(mejor_rival.id)

    # Crear las partidas
    partidas = []
    for p1, p2 in emparejamientos:
        partida = Partida.objects.create(
            ronda=ronda,
            pareja_1=p1,
            pareja_2=p2,
        )
        partidas.append(partida)

    return partidas


def _crear_partidas(ronda, parejas):
    """Crea partidas a partir de una lista ordenada de parejas (de 2 en 2)."""
    partidas = []
    for i in range(0, len(parejas) - 1, 2):
        partida = Partida.objects.create(
            ronda=ronda,
            pareja_1=parejas[i],
            pareja_2=parejas[i + 1],
        )
        partidas.append(partida)
    return partidas


def calcular_clasificacion():
    """
    Devuelve la clasificación general ordenada por:
    1. Puntos (desc)
    2. Buchholz (desc)
    3. Diferencia de piedras (desc)
    4. Piedras a favor (desc)
    """
    parejas = list(Pareja.objects.filter(activa=True))
    clasificacion = []
    for pareja in parejas:
        clasificacion.append({
            "pareja": pareja,
            "puntos": pareja.puntos(),
            "buchholz": pareja.buchholz(),
            "dif_piedras": pareja.diferencia_piedras(),
            "piedras_favor": pareja.piedras_favor(),
            "victorias": pareja.victorias(),
        })

    clasificacion.sort(
        key=lambda x: (x["puntos"], x["buchholz"], x["dif_piedras"], x["piedras_favor"]),
        reverse=True,
    )

    for i, entry in enumerate(clasificacion, 1):
        entry["posicion"] = i

    return clasificacion


def generar_eliminatorias():
    """
    Genera los octavos de final a partir del top 16 de la clasificación.
    1o vs 16o, 2o vs 15o, etc.
    """
    clasificacion = calcular_clasificacion()[:16]

    ronda_octavos = Ronda.objects.create(
        numero=6,
        fase=Ronda.Fase.OCTAVOS,
    )

    partidas = []
    for i in range(8):
        p1 = clasificacion[i]["pareja"]
        p2 = clasificacion[15 - i]["pareja"]
        partida = Partida.objects.create(
            ronda=ronda_octavos,
            pareja_1=p1,
            pareja_2=p2,
        )
        partidas.append(partida)

    return ronda_octavos, partidas
