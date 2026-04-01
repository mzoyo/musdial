import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from torneo.grupos import generar_todas_las_partidas
from torneo.models import Grupo, Juego, Pareja, Partida, Ronda

GRUPOS_DATA = {
    "A": [
        ("Bambel-Mora", "Bambel", "Mora"),
        ("Richi-Cuchu", "Richi", "Cuchu"),
        ("Nule-Benito", "Nule", "Benito"),
        ("Isma-Juanillo", "Isma", "Juanillo"),
        ("Los nenes", "Nene 1", "Nene 2"),
    ],
    "B": [
        ("Felipe-Eusebio", "Felipe", "Eusebio"),
        ("Sece-Guti", "Sece", "Guti"),
        ("Joselu-Seto", "Joselu", "Seto"),
        ("Isay-Trigo", "Isay", "Trigo"),
        ("Parra-Laura", "Parra", "Laura"),
    ],
    "C": [
        ("Chimba-Mora", "Chimba", "Mora"),
        ("Calorro-Higinio", "Calorro", "Higinio"),
        ("Domingo-J.Miguel", "Domingo", "J.Miguel"),
        ("Pichon-J.Carlos", "Pichon", "J.Carlos"),
        ("Sonia-Kayo", "Sonia", "Kayo"),
    ],
    "D": [
        ("Saul-Diego", "Saul", "Diego"),
        ("Carlos-Use", "Carlos", "Use"),
        ("Luis-Angel", "Luis", "Angel"),
        ("Ruben-Coco", "Ruben", "Coco"),
        ("Felix-Peris", "Felix", "Peris"),
    ],
    "E": [
        ("Fano-Prilly", "Fano", "Prilly"),
        ("Vindel-Pastor", "Vindel", "Pastor"),
        ("Canamon-Canamin", "Canamon", "Canamin"),
        ("Jaro-Tonin", "Jaro", "Tonin"),
        ("Isra-Enrique", "Isra", "Enrique"),
    ],
}


class Command(BaseCommand):
    help = "Crea demo con jornadas en distintos estados para probar la vista"

    def handle(self, *args, **options):
        # Limpiar todo
        Juego.objects.all().delete()
        Partida.objects.all().delete()
        Ronda.objects.all().delete()
        Pareja.objects.all().delete()
        Grupo.objects.all().delete()

        # Crear grupos y parejas
        for letra, parejas_data in GRUPOS_DATA.items():
            grupo = Grupo.objects.create(nombre=letra)
            for nombre, j1, j2 in parejas_data:
                Pareja.objects.create(nombre=nombre, jugador1=j1, jugador2=j2, grupo=grupo)

        # Generar todas las partidas
        rondas, partidas = generar_todas_las_partidas()

        # Jornada 1 y 2: COMPLETADAS (todas las partidas finalizadas)
        for ronda in rondas[:2]:
            ronda.estado = Ronda.Estado.COMPLETADA
            ronda.save()
            for partida in ronda.partidas.all():
                self._simular_partida(partida)

        # Jornada 3: EN_CURSO (algunas jugadas, algunas pendientes)
        ronda3 = rondas[2]
        ronda3.estado = Ronda.Estado.EN_CURSO
        ronda3.save()
        partidas_j3 = list(ronda3.partidas.all())
        # 7 jugadas, 3 pendientes
        for partida in partidas_j3[:7]:
            self._simular_partida(partida)

        # Jornadas 4 y 5: PENDIENTES (futuras)
        for ronda in rondas[3:]:
            ronda.estado = Ronda.Estado.PENDIENTE
            ronda.save()

        self.stdout.write(self.style.SUCCESS(
            "\nDemo creada:"
            "\n  Jornada 1: COMPLETADA (10 partidas jugadas)"
            "\n  Jornada 2: COMPLETADA (10 partidas jugadas)"
            "\n  Jornada 3: EN CURSO (7 jugadas, 3 pendientes)"
            "\n  Jornada 4: PENDIENTE (futura)"
            "\n  Jornada 5: PENDIENTE (futura)"
        ))

        # Mostrar enlace de una pareja que tenga partidas en distintos estados
        pareja = partidas_j3[8].pareja_1  # Una con partida pendiente en J3
        self.stdout.write(f"\nPrueba con: /pareja/{pareja.token}/ ({pareja.nombre})")
        pareja2 = partidas_j3[0].ganador  # Una que ya jugó J3
        self.stdout.write(f"O con: /pareja/{pareja2.token}/ ({pareja2.nombre})")

    def _simular_partida(self, partida):
        partida.estado = Partida.Estado.EN_CURSO
        partida.inicio_solicitado_por = partida.pareja_1
        partida.fecha_inicio = timezone.now()
        partida.save()

        j1_wins, j2_wins, numero = 0, 0, 0
        while j1_wins < 4 and j2_wins < 4:
            numero += 1
            if random.random() < 0.55:
                ganador = partida.pareja_1
                j1_wins += 1
            else:
                ganador = partida.pareja_2
                j2_wins += 1
            piedras_p = random.choice([10, 15, 20, 25, 30, 35])
            Juego.objects.create(
                partida=partida, numero=numero,
                piedras_1=40 if ganador == partida.pareja_1 else piedras_p,
                piedras_2=40 if ganador == partida.pareja_2 else piedras_p,
                ganador_juego=ganador, subido_por=partida.pareja_1,
                estado=Juego.Estado.CONFIRMADO,
                timestamp_confirmacion=timezone.now(),
            )

        partida.ganador = partida.pareja_1 if j1_wins >= 4 else partida.pareja_2
        partida.estado = Partida.Estado.FINALIZADA
        partida.fecha_fin = timezone.now()
        partida.save()
