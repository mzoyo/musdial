import secrets

from django.core.validators import MaxValueValidator
from django.db import models


def generar_token():
    return secrets.token_urlsafe(8)


class Pareja(models.Model):
    nombre = models.CharField(max_length=100)
    jugador1 = models.CharField("Jugador 1", max_length=100)
    jugador2 = models.CharField("Jugador 2", max_length=100)
    token = models.CharField(
        max_length=20, unique=True, default=generar_token, editable=False
    )
    activa = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "parejas"

    def __str__(self):
        return self.nombre

    def victorias(self):
        return self.partidas_ganadas.count()

    def puntos(self):
        return self.victorias() * 2

    def diferencia_piedras(self):
        total_favor = 0
        total_contra = 0
        for juego in Juego.objects.filter(
            partida__estado=Partida.Estado.FINALIZADA,
            estado=Juego.Estado.CONFIRMADO,
        ).filter(
            models.Q(partida__pareja_1=self) | models.Q(partida__pareja_2=self)
        ):
            if juego.partida.pareja_1 == self:
                total_favor += juego.piedras_1
                total_contra += juego.piedras_2
            else:
                total_favor += juego.piedras_2
                total_contra += juego.piedras_1
        return total_favor - total_contra

    def piedras_favor(self):
        total = 0
        for juego in Juego.objects.filter(
            partida__estado=Partida.Estado.FINALIZADA,
            estado=Juego.Estado.CONFIRMADO,
        ).filter(
            models.Q(partida__pareja_1=self) | models.Q(partida__pareja_2=self)
        ):
            if juego.partida.pareja_1 == self:
                total += juego.piedras_1
            else:
                total += juego.piedras_2
        return total

    def buchholz(self):
        rivales = set()
        partidas = Partida.objects.filter(
            estado=Partida.Estado.FINALIZADA
        ).filter(
            models.Q(pareja_1=self) | models.Q(pareja_2=self)
        )
        for partida in partidas:
            rival = partida.pareja_2 if partida.pareja_1 == self else partida.pareja_1
            rivales.add(rival)
        return sum(r.puntos() for r in rivales)


class Ronda(models.Model):
    class Fase(models.TextChoices):
        CLASIFICATORIA = "clasificatoria", "Clasificatoria"
        OCTAVOS = "octavos", "Octavos de final"
        CUARTOS = "cuartos", "Cuartos de final"
        SEMIFINAL = "semifinal", "Semifinal"
        TERCER_PUESTO = "tercer_puesto", "Tercer puesto"
        FINAL = "final", "Final"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_CURSO = "en_curso", "En curso"
        COMPLETADA = "completada", "Completada"

    numero = models.PositiveIntegerField()
    fase = models.CharField(max_length=20, choices=Fase.choices, default=Fase.CLASIFICATORIA)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_limite = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"Ronda {self.numero} ({self.get_fase_display()})"

    @property
    def juegos_necesarios(self):
        if self.fase == self.Fase.CLASIFICATORIA:
            return 4
        return 6


class Partida(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"

    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, related_name="partidas")
    pareja_1 = models.ForeignKey(
        Pareja, on_delete=models.CASCADE, related_name="partidas_como_1"
    )
    pareja_2 = models.ForeignKey(
        Pareja, on_delete=models.CASCADE, related_name="partidas_como_2"
    )
    ganador = models.ForeignKey(
        Pareja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partidas_ganadas",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    inicio_solicitado_por = models.ForeignKey(
        Pareja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    fecha_inicio = models.DateTimeField(blank=True, null=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "partidas"

    def __str__(self):
        return f"{self.pareja_1} vs {self.pareja_2} (Ronda {self.ronda.numero})"

    def juegos_pareja_1(self):
        return self.juegos.filter(
            ganador_juego=self.pareja_1, estado=Juego.Estado.CONFIRMADO
        ).count()

    def juegos_pareja_2(self):
        return self.juegos.filter(
            ganador_juego=self.pareja_2, estado=Juego.Estado.CONFIRMADO
        ).count()

    def marcador(self):
        return f"{self.juegos_pareja_1()} - {self.juegos_pareja_2()}"

    def comprobar_ganador(self):
        necesarios = self.ronda.juegos_necesarios
        j1 = self.juegos_pareja_1()
        j2 = self.juegos_pareja_2()
        if j1 >= necesarios:
            self.ganador = self.pareja_1
            self.estado = self.Estado.FINALIZADA
            self.save()
        elif j2 >= necesarios:
            self.ganador = self.pareja_2
            self.estado = self.Estado.FINALIZADA
            self.save()


class Juego(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_CONFIRMACION = "pendiente", "Pendiente de confirmación"
        CONFIRMADO = "confirmado", "Confirmado"
        RECHAZADO = "rechazado", "Rechazado"

    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name="juegos")
    numero = models.PositiveIntegerField()
    piedras_1 = models.PositiveIntegerField(
        "Piedras pareja 1",
        validators=[MaxValueValidator(40)],
    )
    piedras_2 = models.PositiveIntegerField(
        "Piedras pareja 2",
        validators=[MaxValueValidator(40)],
    )
    ganador_juego = models.ForeignKey(
        Pareja, on_delete=models.CASCADE, related_name="juegos_ganados",
    )
    subido_por = models.ForeignKey(
        Pareja,
        on_delete=models.CASCADE,
        related_name="juegos_subidos",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE_CONFIRMACION,
    )
    timestamp_subida = models.DateTimeField(auto_now_add=True)
    timestamp_confirmacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["numero"]
        unique_together = ["partida", "numero"]

    def __str__(self):
        return (
            f"Juego {self.numero}: {self.partida.pareja_1} {self.piedras_1} - "
            f"{self.piedras_2} {self.partida.pareja_2}"
        )

    @property
    def rival_confirma(self):
        if self.subido_por == self.partida.pareja_1:
            return self.partida.pareja_2
        return self.partida.pareja_1
