import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from torneo.grupos import generar_todas_las_partidas
from torneo.models import Grupo, Juego, Pareja, Partida


GRUPOS = {
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
    help = "Crea datos de demo con las parejas reales del Musdial"

    def handle(self, *args, **options):
        if Pareja.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Ya existen datos. Ejecuta borrar_demo primero."
            ))
            return

        self.stdout.write("Creando grupos y parejas...")
        for letra, parejas_data in GRUPOS.items():
            grupo = Grupo.objects.create(nombre=letra)
            for nombre, j1, j2 in parejas_data:
                Pareja.objects.create(
                    nombre=nombre, jugador1=j1, jugador2=j2, grupo=grupo,
                )

        self.stdout.write("Generando partidas...")
        ronda, partidas = generar_todas_las_partidas()

        # Simular algunas partidas
        partidas_lista = list(partidas)
        random.shuffle(partidas_lista)

        for i, partida in enumerate(partidas_lista):
            if i < 15:
                self._simular_partida(partida)
            elif i < 20:
                partida.estado = Partida.Estado.EN_CURSO
                partida.inicio_solicitado_por = partida.pareja_1
                partida.fecha_inicio = timezone.now()
                partida.save()
                for j in range(1, random.randint(2, 4)):
                    self._crear_juego(partida, j)

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo creada: 5 grupos, 25 parejas, 50 partidas "
            f"(15 finalizadas, 5 en curso, 30 pendientes)"
        ))

        self.stdout.write("\nEnlaces de ejemplo:")
        for p in Pareja.objects.all()[:4]:
            self.stdout.write(f"  {p.nombre}: /pareja/{p.token}/")

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

            piedras_perdedor = random.choice([10, 15, 20, 25, 30, 35])
            Juego.objects.create(
                partida=partida, numero=numero,
                piedras_1=40 if ganador == partida.pareja_1 else piedras_perdedor,
                piedras_2=40 if ganador == partida.pareja_2 else piedras_perdedor,
                ganador_juego=ganador, subido_por=partida.pareja_1,
                estado=Juego.Estado.CONFIRMADO,
                timestamp_confirmacion=timezone.now(),
            )

        partida.ganador = partida.pareja_1 if j1_wins >= 4 else partida.pareja_2
        partida.estado = Partida.Estado.FINALIZADA
        partida.fecha_fin = timezone.now()
        partida.save()

    def _crear_juego(self, partida, numero):
        ganador = random.choice([partida.pareja_1, partida.pareja_2])
        piedras_perdedor = random.choice([10, 15, 20, 25, 30, 35])
        Juego.objects.create(
            partida=partida, numero=numero,
            piedras_1=40 if ganador == partida.pareja_1 else piedras_perdedor,
            piedras_2=40 if ganador == partida.pareja_2 else piedras_perdedor,
            ganador_juego=ganador, subido_por=partida.pareja_1,
            estado=Juego.Estado.CONFIRMADO,
            timestamp_confirmacion=timezone.now(),
        )
