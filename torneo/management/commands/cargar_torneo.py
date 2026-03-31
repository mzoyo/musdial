from django.core.management.base import BaseCommand

from torneo.grupos import generar_todas_las_partidas
from torneo.models import Grupo, Pareja, Partida

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
    help = "Carga las 25 parejas reales, crea los 5 grupos y genera las 50 partidas del torneo"

    def handle(self, *args, **options):
        if Pareja.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Ya existen datos. Ejecuta borrar_demo --si primero si quieres resetear."
            ))
            return

        self.stdout.write("Creando grupos y parejas...")
        for letra, parejas_data in GRUPOS.items():
            grupo = Grupo.objects.create(nombre=letra)
            for nombre, j1, j2 in parejas_data:
                Pareja.objects.create(
                    nombre=nombre, jugador1=j1, jugador2=j2, grupo=grupo,
                )
            self.stdout.write(f"  Grupo {letra}: {len(parejas_data)} parejas")

        self.stdout.write("\nGenerando partidas (5 jornadas x 10 partidas)...")
        rondas, partidas = generar_todas_las_partidas()

        self.stdout.write(self.style.SUCCESS(
            f"\nTorneo cargado correctamente!"
            f"\n  {Grupo.objects.count()} grupos"
            f"\n  {Pareja.objects.count()} parejas"
            f"\n  {len(rondas)} jornadas"
            f"\n  {len(partidas)} partidas"
        ))

        self.stdout.write("\nJornadas:")
        for ronda in rondas:
            n = ronda.partidas.count()
            self.stdout.write(
                f"  {ronda}: {ronda.fecha_inicio.strftime('%d/%m')} - "
                f"{ronda.fecha_limite.strftime('%d/%m')} ({n} partidas)"
            )

        self.stdout.write(self.style.SUCCESS(
            "\nEnlaces de las parejas (para enviar por WhatsApp):"
        ))
        for grupo in Grupo.objects.all():
            self.stdout.write(f"\n  Grupo {grupo.nombre}:")
            for p in grupo.parejas.all():
                self.stdout.write(f"    {p.nombre}: /pareja/{p.token}/")
