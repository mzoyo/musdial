from django.core.management.base import BaseCommand

from torneo.models import Juego, Pareja, Partida, Ronda


class Command(BaseCommand):
    help = "Borra todos los datos del torneo (parejas, rondas, partidas, juegos)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--si",
            action="store_true",
            help="Confirmar el borrado sin preguntar",
        )

    def handle(self, *args, **options):
        if not options["si"]:
            self.stdout.write(self.style.WARNING(
                "Esto borrara TODOS los datos del torneo."
            ))
            respuesta = input("¿Estas seguro? (si/no): ")
            if respuesta.lower() != "si":
                self.stdout.write("Cancelado.")
                return

        juegos = Juego.objects.count()
        partidas = Partida.objects.count()
        rondas = Ronda.objects.count()
        parejas = Pareja.objects.count()

        Juego.objects.all().delete()
        Partida.objects.all().delete()
        Ronda.objects.all().delete()
        Pareja.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"Borrado: {juegos} juegos, {partidas} partidas, "
            f"{rondas} rondas, {parejas} parejas."
        ))
