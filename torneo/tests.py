from django.test import TestCase, Client
from django.utils import timezone

from .models import Juego, Pareja, Partida, Ronda
from .swiss import calcular_clasificacion, generar_emparejamientos, generar_eliminatorias


class ParejaModelTest(TestCase):
    def test_token_se_genera_automaticamente(self):
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B")
        self.assertTrue(len(p.token) > 0)

    def test_tokens_son_unicos(self):
        p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B")
        p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D")
        self.assertNotEqual(p1.token, p2.token)

    def test_puntos_sin_partidas(self):
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B")
        self.assertEqual(p.puntos(), 0)

    def test_buchholz_sin_partidas(self):
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B")
        self.assertEqual(p.buchholz(), 0)


class PartidaModelTest(TestCase):
    def setUp(self):
        self.p1 = Pareja.objects.create(nombre="Pareja 1", jugador1="A", jugador2="B")
        self.p2 = Pareja.objects.create(nombre="Pareja 2", jugador1="C", jugador2="D")
        self.ronda = Ronda.objects.create(numero=1, fase=Ronda.Fase.CLASIFICATORIA, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, pareja_1=self.p1, pareja_2=self.p2,
            estado=Partida.Estado.EN_CURSO, fecha_inicio=timezone.now(),
        )

    def test_marcador_inicial(self):
        self.assertEqual(self.partida.marcador(), "0 - 0")

    def test_juegos_necesarios_clasificatoria(self):
        self.assertEqual(self.ronda.juegos_necesarios, 4)

    def test_juegos_necesarios_eliminatoria(self):
        ronda_elim = Ronda.objects.create(numero=6, fase=Ronda.Fase.OCTAVOS)
        self.assertEqual(ronda_elim.juegos_necesarios, 6)

    def test_comprobar_ganador_con_4_juegos(self):
        for i in range(1, 5):
            Juego.objects.create(
                partida=self.partida, numero=i,
                piedras_1=40, piedras_2=20,
                ganador_juego=self.p1, subido_por=self.p1,
                estado=Juego.Estado.CONFIRMADO,
            )
        self.partida.comprobar_ganador()
        self.assertEqual(self.partida.ganador, self.p1)
        self.assertEqual(self.partida.estado, Partida.Estado.FINALIZADA)

    def test_no_ganador_con_3_juegos(self):
        for i in range(1, 4):
            Juego.objects.create(
                partida=self.partida, numero=i,
                piedras_1=40, piedras_2=20,
                ganador_juego=self.p1, subido_por=self.p1,
                estado=Juego.Estado.CONFIRMADO,
            )
        self.partida.comprobar_ganador()
        self.assertIsNone(self.partida.ganador)

    def test_juegos_pendientes_no_cuentan(self):
        Juego.objects.create(
            partida=self.partida, numero=1,
            piedras_1=40, piedras_2=20,
            ganador_juego=self.p1, subido_por=self.p1,
            estado=Juego.Estado.PENDIENTE_CONFIRMACION,
        )
        self.assertEqual(self.partida.juegos_pareja_1(), 0)


class PiedrasTest(TestCase):
    def setUp(self):
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B")
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D")
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, pareja_1=self.p1, pareja_2=self.p2,
            estado=Partida.Estado.EN_CURSO,
        )

    def _crear_juego(self, piedras_1, piedras_2, numero=1):
        ganador = self.p1 if piedras_1 == 40 else self.p2
        Juego.objects.create(
            partida=self.partida, numero=numero,
            piedras_1=piedras_1, piedras_2=piedras_2,
            ganador_juego=ganador, subido_por=self.p1,
            estado=Juego.Estado.CONFIRMADO,
        )

    def test_diferencia_piedras(self):
        self.partida.estado = Partida.Estado.FINALIZADA
        self.partida.ganador = self.p1
        self.partida.save()
        self._crear_juego(40, 25, 1)
        self._crear_juego(40, 30, 2)
        # p1: 80 favor, 55 contra -> dif = 25
        self.assertEqual(self.p1.diferencia_piedras(), 25)
        self.assertEqual(self.p2.diferencia_piedras(), -25)

    def test_piedras_favor(self):
        self.partida.estado = Partida.Estado.FINALIZADA
        self.partida.ganador = self.p1
        self.partida.save()
        self._crear_juego(40, 25, 1)
        self.assertEqual(self.p1.piedras_favor(), 40)
        self.assertEqual(self.p2.piedras_favor(), 25)


class SwissTest(TestCase):
    def _crear_parejas(self, n):
        return [
            Pareja.objects.create(nombre=f"Pareja {i}", jugador1=f"J{i}a", jugador2=f"J{i}b")
            for i in range(1, n + 1)
        ]

    def test_emparejamiento_ronda_1(self):
        self._crear_parejas(26)
        ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        partidas = generar_emparejamientos(ronda)
        self.assertEqual(len(partidas), 13)

        # Verificar que todas las parejas juegan
        parejas_en_partida = set()
        for p in partidas:
            parejas_en_partida.add(p.pareja_1_id)
            parejas_en_partida.add(p.pareja_2_id)
        self.assertEqual(len(parejas_en_partida), 26)

    def test_no_repetir_rivales(self):
        parejas = self._crear_parejas(4)
        ronda1 = Ronda.objects.create(numero=1, estado=Ronda.Estado.COMPLETADA)
        # Ronda 1: p0 vs p1, p2 vs p3
        Partida.objects.create(
            ronda=ronda1, pareja_1=parejas[0], pareja_2=parejas[1],
            estado=Partida.Estado.FINALIZADA, ganador=parejas[0],
        )
        Partida.objects.create(
            ronda=ronda1, pareja_1=parejas[2], pareja_2=parejas[3],
            estado=Partida.Estado.FINALIZADA, ganador=parejas[2],
        )

        ronda2 = Ronda.objects.create(numero=2, estado=Ronda.Estado.EN_CURSO)
        partidas = generar_emparejamientos(ronda2)

        for p in partidas:
            # p0 no debe jugar contra p1, p2 no contra p3
            if p.pareja_1 == parejas[0]:
                self.assertNotEqual(p.pareja_2, parejas[1])
            if p.pareja_1 == parejas[2]:
                self.assertNotEqual(p.pareja_2, parejas[3])

    def test_clasificacion_ordenada(self):
        parejas = self._crear_parejas(4)
        ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.COMPLETADA)
        # p0 gana a p1, p2 gana a p3
        Partida.objects.create(
            ronda=ronda, pareja_1=parejas[0], pareja_2=parejas[1],
            estado=Partida.Estado.FINALIZADA, ganador=parejas[0],
        )
        Partida.objects.create(
            ronda=ronda, pareja_1=parejas[2], pareja_2=parejas[3],
            estado=Partida.Estado.FINALIZADA, ganador=parejas[2],
        )

        tabla = calcular_clasificacion()
        self.assertEqual(tabla[0]["puntos"], 2)
        self.assertEqual(tabla[1]["puntos"], 2)
        self.assertEqual(tabla[2]["puntos"], 0)
        self.assertEqual(tabla[3]["puntos"], 0)


class InicioPartidaTest(TestCase):
    def setUp(self):
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B")
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D")
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, pareja_1=self.p1, pareja_2=self.p2,
        )
        self.client = Client()

    def test_solicitar_inicio_primera_pareja(self):
        self.client.post(f"/pareja/{self.p1.token}/iniciar/")
        self.partida.refresh_from_db()
        self.assertEqual(self.partida.inicio_solicitado_por, self.p1)
        self.assertEqual(self.partida.estado, Partida.Estado.PENDIENTE)

    def test_confirmar_inicio_segunda_pareja(self):
        self.partida.inicio_solicitado_por = self.p1
        self.partida.save()
        self.client.post(f"/pareja/{self.p2.token}/iniciar/")
        self.partida.refresh_from_db()
        self.assertEqual(self.partida.estado, Partida.Estado.EN_CURSO)
        self.assertIsNotNone(self.partida.fecha_inicio)

    def test_no_empezar_dos_veces(self):
        self.client.post(f"/pareja/{self.p1.token}/iniciar/")
        self.client.post(f"/pareja/{self.p1.token}/iniciar/")
        self.partida.refresh_from_db()
        # La misma pareja no puede confirmar su propio inicio
        self.assertEqual(self.partida.estado, Partida.Estado.PENDIENTE)


class SubirJuegoViewTest(TestCase):
    def setUp(self):
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B")
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D")
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, pareja_1=self.p1, pareja_2=self.p2,
            estado=Partida.Estado.EN_CURSO, fecha_inicio=timezone.now(),
        )
        self.client = Client()

    def test_subir_juego_valido(self):
        resp = self.client.post(f"/pareja/{self.p1.token}/subir/", {
            "piedras_1": 40, "piedras_2": 25,
        })
        self.assertEqual(resp.status_code, 302)
        juego = Juego.objects.first()
        self.assertEqual(juego.piedras_1, 40)
        self.assertEqual(juego.piedras_2, 25)
        self.assertEqual(juego.ganador_juego, self.p1)
        self.assertEqual(juego.subido_por, self.p1)

    def test_rechaza_sin_40_piedras(self):
        resp = self.client.post(f"/pareja/{self.p1.token}/subir/", {
            "piedras_1": 35, "piedras_2": 25,
        })
        self.assertEqual(resp.status_code, 200)  # re-render con error
        self.assertEqual(Juego.objects.count(), 0)

    def test_rechaza_dos_40(self):
        resp = self.client.post(f"/pareja/{self.p1.token}/subir/", {
            "piedras_1": 40, "piedras_2": 40,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Juego.objects.count(), 0)

    def test_no_subir_si_partida_pendiente(self):
        self.partida.estado = Partida.Estado.PENDIENTE
        self.partida.save()
        resp = self.client.post(f"/pareja/{self.p1.token}/subir/", {
            "piedras_1": 40, "piedras_2": 25,
        })
        self.assertEqual(resp.status_code, 302)  # redirect sin crear
        self.assertEqual(Juego.objects.count(), 0)


class ConfirmarJuegoViewTest(TestCase):
    def setUp(self):
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B")
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D")
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, pareja_1=self.p1, pareja_2=self.p2,
            estado=Partida.Estado.EN_CURSO,
        )
        self.juego = Juego.objects.create(
            partida=self.partida, numero=1,
            piedras_1=40, piedras_2=25,
            ganador_juego=self.p1, subido_por=self.p1,
        )
        self.client = Client()

    def test_confirmar_juego(self):
        resp = self.client.post(
            f"/pareja/{self.p2.token}/confirmar/{self.juego.pk}/",
            {"accion": "confirmar"},
        )
        self.assertEqual(resp.status_code, 302)
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.estado, Juego.Estado.CONFIRMADO)
        self.assertIsNotNone(self.juego.timestamp_confirmacion)

    def test_rechazar_juego(self):
        self.client.post(
            f"/pareja/{self.p2.token}/confirmar/{self.juego.pk}/",
            {"accion": "rechazar"},
        )
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.estado, Juego.Estado.RECHAZADO)

    def test_no_confirmar_por_quien_subio(self):
        resp = self.client.post(
            f"/pareja/{self.p1.token}/confirmar/{self.juego.pk}/",
            {"accion": "confirmar"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_partida_se_cierra_al_llegar_a_4(self):
        # Crear 3 juegos confirmados previos
        for i in range(2, 5):
            Juego.objects.create(
                partida=self.partida, numero=i,
                piedras_1=40, piedras_2=20,
                ganador_juego=self.p1, subido_por=self.p1,
                estado=Juego.Estado.CONFIRMADO,
            )
        # Confirmar el juego 1 (ahora serian 4 para p1)
        self.client.post(
            f"/pareja/{self.p2.token}/confirmar/{self.juego.pk}/",
            {"accion": "confirmar"},
        )
        self.partida.refresh_from_db()
        self.assertEqual(self.partida.estado, Partida.Estado.FINALIZADA)
        self.assertEqual(self.partida.ganador, self.p1)


class VistasPublicasTest(TestCase):
    def test_inicio(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_clasificacion(self):
        resp = self.client.get("/clasificacion/")
        self.assertEqual(resp.status_code, 200)

    def test_ronda(self):
        ronda = Ronda.objects.create(numero=1)
        resp = self.client.get(f"/ronda/{ronda.numero}/")
        self.assertEqual(resp.status_code, 200)

    def test_panel_pareja(self):
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B")
        resp = self.client.get(f"/pareja/{p.token}/")
        self.assertEqual(resp.status_code, 200)

    def test_panel_pareja_token_invalido(self):
        resp = self.client.get("/pareja/token-falso/")
        self.assertEqual(resp.status_code, 404)
