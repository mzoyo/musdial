import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from torneo.models import Juego, Pareja, Partida, Ronda
from torneo.swiss import generar_emparejamientos


NOMBRES_PAREJAS = [
    ("Los Ases", "Paco Garcia", "Luis Martinez"),
    ("Mus o Nada", "Ana Lopez", "Maria Ruiz"),
    ("Los Reyes", "Carlos Fernandez", "Pedro Diaz"),
    ("Las Sotas", "Carmen Gomez", "Rosa Jimenez"),
    ("Par de Ases", "Miguel Torres", "Juan Navarro"),
    ("Envido Total", "Elena Moreno", "Lucia Sanchez"),
    ("Los Caballos", "Andres Gil", "Javier Romero"),
    ("Ordago", "Marta Alvarez", "Sara Munoz"),
    ("Pares y Nones", "Fernando Ortega", "Pablo Castillo"),
    ("Treinta y Una", "Pilar Herrero", "Isabel Blanco"),
    ("La Grande", "Raul Santos", "Diego Ramos"),
    ("Los Bastos", "Laura Iglesias", "Teresa Vega"),
    ("Cuatro Reyes", "Alberto Fuentes", "Hugo Calvo"),
    ("Mus con Ganas", "Patricia Pena", "Silvia Cruz"),
    ("Los Copleros", "Rafael Prieto", "Manuel Cano"),
    ("Paso y Miro", "Eva Medina", "Clara Rubio"),
    ("Los Duros", "Daniel Mora", "Oscar Gallego"),
    ("Sin Envite", "Lucia Soto", "Irene Guerrero"),
    ("Los del Pueblo", "Victor Delgado", "Adrian Molina"),
    ("Farol Seguro", "Natalia Pascual", "Sandra Herrera"),
    ("Mus en Vena", "Roberto Leon", "Guillermo Vargas"),
    ("Las Espadas", "Angela Martin", "Paula Dominguez"),
    ("Piedra a Piedra", "Sergio Vazquez", "Ivan Mendez"),
    ("Los del Bar", "Cristina Reyes", "Beatriz Cortes"),
    ("Flor y Mus", "Marcos Aguilar", "Tomas Romero"),
    ("Los Favoritos", "Monica Suarez", "Alicia Herrero"),
]


class Command(BaseCommand):
    help = "Crea datos de demo para el torneo Musdial"

    def handle(self, *args, **options):
        if Pareja.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Ya existen datos. Ejecuta borrar_demo primero."
            ))
            return

        self.stdout.write("Creando 26 parejas...")
        parejas = []
        for nombre, j1, j2 in NOMBRES_PAREJAS:
            p = Pareja.objects.create(nombre=nombre, jugador1=j1, jugador2=j2)
            parejas.append(p)

        # Ronda 1: completada
        self.stdout.write("Generando Ronda 1 (completada)...")
        ronda1 = Ronda.objects.create(
            numero=1, estado=Ronda.Estado.COMPLETADA,
            fecha_inicio=timezone.now(),
        )
        partidas_r1 = generar_emparejamientos(ronda1)
        for partida in partidas_r1:
            self._simular_partida(partida, juegos_necesarios=4)

        # Ronda 2: en curso con partidas en distintos estados
        self.stdout.write("Generando Ronda 2 (en curso)...")
        ronda2 = Ronda.objects.create(
            numero=2, estado=Ronda.Estado.EN_CURSO,
            fecha_inicio=timezone.now(),
        )
        partidas_r2 = generar_emparejamientos(ronda2)

        for i, partida in enumerate(partidas_r2):
            if i < 5:
                # 5 partidas finalizadas
                self._simular_partida(partida, juegos_necesarios=4)
            elif i < 8:
                # 3 partidas en curso (con algunos juegos)
                partida.estado = Partida.Estado.EN_CURSO
                partida.inicio_solicitado_por = partida.pareja_1
                partida.fecha_inicio = timezone.now()
                partida.save()
                n_juegos = random.randint(1, 3)
                for j in range(1, n_juegos + 1):
                    self._crear_juego_confirmado(partida, j)
            elif i < 10:
                # 2 partidas esperando que el rival confirme inicio
                partida.inicio_solicitado_por = partida.pareja_1
                partida.save()
            # Las demas quedan pendientes

        self.stdout.write(self.style.SUCCESS("\nDemo creada correctamente!"))
        self.stdout.write(f"\nParejas creadas: {len(parejas)}")
        self.stdout.write(f"Ronda 1: completada ({len(partidas_r1)} partidas)")
        self.stdout.write(f"Ronda 2: en curso ({len(partidas_r2)} partidas)")

        self.stdout.write(self.style.SUCCESS("\nEnlaces de ejemplo para probar:"))
        # Mostrar parejas que estan en distintos estados en ronda 2
        for partida in partidas_r2[7:10]:
            self.stdout.write(f"\n  {partida.pareja_1} vs {partida.pareja_2}:")
            self.stdout.write(f"    /pareja/{partida.pareja_1.token}/")
            self.stdout.write(f"    /pareja/{partida.pareja_2.token}/")

    def _simular_partida(self, partida, juegos_necesarios):
        partida.estado = Partida.Estado.EN_CURSO
        partida.inicio_solicitado_por = partida.pareja_1
        partida.fecha_inicio = timezone.now()
        partida.save()

        j1_wins = 0
        j2_wins = 0
        numero = 0

        while j1_wins < juegos_necesarios and j2_wins < juegos_necesarios:
            numero += 1
            # Elegir ganador con algo de aleatoriedad
            if random.random() < 0.55:
                ganador = partida.pareja_1
                piedras_ganador = 40
                piedras_perdedor = random.choice([10, 15, 20, 25, 30, 35])
                j1_wins += 1
            else:
                ganador = partida.pareja_2
                piedras_ganador = 40
                piedras_perdedor = random.choice([10, 15, 20, 25, 30, 35])
                j2_wins += 1

            p1 = piedras_ganador if ganador == partida.pareja_1 else piedras_perdedor
            p2 = piedras_ganador if ganador == partida.pareja_2 else piedras_perdedor

            Juego.objects.create(
                partida=partida, numero=numero,
                piedras_1=p1, piedras_2=p2,
                ganador_juego=ganador,
                subido_por=partida.pareja_1,
                estado=Juego.Estado.CONFIRMADO,
                timestamp_confirmacion=timezone.now(),
            )

        partida.ganador = partida.pareja_1 if j1_wins >= juegos_necesarios else partida.pareja_2
        partida.estado = Partida.Estado.FINALIZADA
        partida.fecha_fin = timezone.now()
        partida.save()

    def _crear_juego_confirmado(self, partida, numero):
        ganador = random.choice([partida.pareja_1, partida.pareja_2])
        piedras_perdedor = random.choice([10, 15, 20, 25, 30, 35])
        p1 = 40 if ganador == partida.pareja_1 else piedras_perdedor
        p2 = 40 if ganador == partida.pareja_2 else piedras_perdedor

        Juego.objects.create(
            partida=partida, numero=numero,
            piedras_1=p1, piedras_2=p2,
            ganador_juego=ganador,
            subido_por=partida.pareja_1,
            estado=Juego.Estado.CONFIRMADO,
            timestamp_confirmacion=timezone.now(),
        )
