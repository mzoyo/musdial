import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

BOT_URL = "http://localhost:3001"


def _send(message):
    """Envia un mensaje al grupo de WhatsApp via el bot."""
    try:
        data = json.dumps({"message": message}).encode()
        req = urllib.request.Request(
            f"{BOT_URL}/send",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.warning(f"WhatsApp bot no disponible: {e}")


def notificar_inicio_partida(partida):
    """Notifica que una partida ha empezado."""
    msg = (
        f"*MUSDIAL* - Partida iniciada\n\n"
        f"*{partida.pareja_1}* vs *{partida.pareja_2}*\n"
    )
    if partida.grupo:
        msg += f"Grupo {partida.grupo.nombre}"
    if partida.ronda:
        msg += f" - {partida.ronda}"
    _send(msg)


def notificar_juego(juego):
    """Notifica el resultado de un juego confirmado."""
    partida = juego.partida
    msg = (
        f"*MUSDIAL* - Juego {juego.numero}\n\n"
        f"*{partida.pareja_1}* {juego.piedras_1} - {juego.piedras_2} *{partida.pareja_2}*\n"
        f"Marcador: *{partida.marcador()}*"
    )
    _send(msg)


def notificar_fin_partida(partida):
    """Notifica el resultado final de una partida."""
    from .grupos import clasificacion_grupo

    msg = (
        f"*MUSDIAL* - Partida finalizada\n\n"
        f"*{partida.pareja_1}* {partida.juegos_pareja_1()} - "
        f"{partida.juegos_pareja_2()} *{partida.pareja_2}*\n\n"
        f"Gana: *{partida.ganador}*\n"
    )

    if partida.grupo:
        msg += f"\n*Clasificacion Grupo {partida.grupo.nombre}:*\n"
        tabla = clasificacion_grupo(partida.grupo)
        for entry in tabla:
            pos = entry["posicion"]
            emoji = ["", "1.", "2.", "3.", "4.", "5."][pos]
            msg += f"{emoji} {entry['pareja'].nombre} - {entry['puntos']} pts ({entry['pg']}V-{entry['pp']}D)\n"

    _send(msg)
