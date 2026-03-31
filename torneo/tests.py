from django.test import TestCase, Client
from django.utils import timezone

from .grupos import (
    clasificacion_grupo,
    generar_eliminatorias,
    generar_todas_las_partidas,
    obtener_mejor_cuarto,
)
from .models import Grupo, Juego, Pareja, Partida, Ronda


class ParejaModelTest(TestCase):
    def test_token_se_genera_automaticamente(self):
        g = Grupo.objects.create(nombre="A")
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B", grupo=g)
        self.assertTrue(len(p.token) > 0)

    def test_tokens_son_unicos(self):
        p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B")
        p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D")
        self.assertNotEqual(p1.token, p2.token)

    def test_puntos_sin_partidas(self):
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B")
        self.assertEqual(p.puntos_grupo(), 0)


class GrupoTest(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre="A")
        self.parejas = []
        for i in range(5):
            p = Pareja.objects.create(
                nombre=f"Pareja {i+1}", jugador1=f"J{i}a", jugador2=f"J{i}b",
                grupo=self.grupo,
            )
            self.parejas.append(p)

    def test_generar_todas_las_partidas(self):
        for letra in "BCDE":
            g = Grupo.objects.create(nombre=letra)
            for i in range(5):
                Pareja.objects.create(
                    nombre=f"{letra}{i}", jugador1=f"J{letra}{i}a",
                    jugador2=f"J{letra}{i}b", grupo=g,
                )
        rondas, partidas = generar_todas_las_partidas()
        self.assertEqual(len(partidas), 50)  # 10 x 5 grupos
        self.assertEqual(len(rondas), 5)  # 5 jornadas
        # 2 partidas por grupo por jornada = 10 por jornada
        for ronda in rondas:
            self.assertEqual(ronda.partidas.count(), 10)

    def test_clasificacion_grupo_sin_partidas(self):
        tabla = clasificacion_grupo(self.grupo)
        self.assertEqual(len(tabla), 5)
        for entry in tabla:
            self.assertEqual(entry["puntos"], 0)

    def test_clasificacion_con_resultados(self):
        ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        # Pareja 0 gana a Pareja 1
        partida = Partida.objects.create(
            ronda=ronda, grupo=self.grupo,
            pareja_1=self.parejas[0], pareja_2=self.parejas[1],
            estado=Partida.Estado.FINALIZADA, ganador=self.parejas[0],
        )
        tabla = clasificacion_grupo(self.grupo)
        # El ganador debe estar primero
        ganador = next(e for e in tabla if e["pareja"] == self.parejas[0])
        self.assertEqual(ganador["puntos"], 2)
        self.assertEqual(ganador["posicion"], 1)

    def test_enfrentamiento_directo(self):
        ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        Partida.objects.create(
            ronda=ronda, grupo=self.grupo,
            pareja_1=self.parejas[0], pareja_2=self.parejas[1],
            estado=Partida.Estado.FINALIZADA, ganador=self.parejas[1],
        )
        self.assertEqual(self.parejas[0].enfrentamiento_directo(self.parejas[1]), -1)
        self.assertEqual(self.parejas[1].enfrentamiento_directo(self.parejas[0]), 1)

    def test_diferencia_juegos(self):
        ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        partida = Partida.objects.create(
            ronda=ronda, grupo=self.grupo,
            pareja_1=self.parejas[0], pareja_2=self.parejas[1],
            estado=Partida.Estado.FINALIZADA, ganador=self.parejas[0],
        )
        # 4 juegos ganados por p0, 2 por p1
        for i in range(1, 5):
            Juego.objects.create(
                partida=partida, numero=i, piedras_1=40, piedras_2=20,
                ganador_juego=self.parejas[0], subido_por=self.parejas[0],
                estado=Juego.Estado.CONFIRMADO,
            )
        for i in range(5, 7):
            Juego.objects.create(
                partida=partida, numero=i, piedras_1=20, piedras_2=40,
                ganador_juego=self.parejas[1], subido_por=self.parejas[1],
                estado=Juego.Estado.CONFIRMADO,
            )
        self.assertEqual(self.parejas[0].juegos_ganados_grupo(), 4)
        self.assertEqual(self.parejas[0].juegos_perdidos_grupo(), 2)
        self.assertEqual(self.parejas[0].diferencia_juegos(), 2)


class MejorCuartoTest(TestCase):
    def test_mejor_cuarto(self):
        grupos = []
        for letra in "AB":
            g = Grupo.objects.create(nombre=letra)
            grupos.append(g)
            parejas = []
            for i in range(5):
                p = Pareja.objects.create(
                    nombre=f"{letra}{i}", jugador1=f"J{letra}{i}a",
                    jugador2=f"J{letra}{i}b", grupo=g,
                )
                parejas.append(p)

            ronda = Ronda.objects.get_or_create(numero=1, defaults={"estado": Ronda.Estado.EN_CURSO})[0]
            # Dar resultados para que haya posiciones claras
            for j, (p1, p2) in enumerate([(0, 1), (0, 2), (0, 3), (0, 4)]):
                Partida.objects.create(
                    ronda=ronda, grupo=g,
                    pareja_1=parejas[p1], pareja_2=parejas[p2],
                    estado=Partida.Estado.FINALIZADA, ganador=parejas[p1],
                )

        cuartos = obtener_mejor_cuarto()
        self.assertEqual(len(cuartos), 2)


class PartidaModelTest(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre="A")
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B", grupo=self.grupo)
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D", grupo=self.grupo)
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, grupo=self.grupo,
            pareja_1=self.p1, pareja_2=self.p2,
            estado=Partida.Estado.EN_CURSO, fecha_inicio=timezone.now(),
        )

    def test_marcador_inicial(self):
        self.assertEqual(self.partida.marcador(), "0 - 0")

    def test_juegos_necesarios_clasificatoria(self):
        self.assertEqual(self.ronda.juegos_necesarios, 4)

    def test_juegos_necesarios_eliminatoria(self):
        ronda_elim = Ronda.objects.create(numero=2, fase=Ronda.Fase.OCTAVOS)
        self.assertEqual(ronda_elim.juegos_necesarios, 6)

    def test_comprobar_ganador_con_4_juegos(self):
        for i in range(1, 5):
            Juego.objects.create(
                partida=self.partida, numero=i, piedras_1=40, piedras_2=20,
                ganador_juego=self.p1, subido_por=self.p1,
                estado=Juego.Estado.CONFIRMADO,
            )
        self.partida.comprobar_ganador()
        self.assertEqual(self.partida.ganador, self.p1)
        self.assertEqual(self.partida.estado, Partida.Estado.FINALIZADA)

    def test_no_ganador_con_3_juegos(self):
        for i in range(1, 4):
            Juego.objects.create(
                partida=self.partida, numero=i, piedras_1=40, piedras_2=20,
                ganador_juego=self.p1, subido_por=self.p1,
                estado=Juego.Estado.CONFIRMADO,
            )
        self.partida.comprobar_ganador()
        self.assertIsNone(self.partida.ganador)

    def test_juegos_pendientes_no_cuentan(self):
        Juego.objects.create(
            partida=self.partida, numero=1, piedras_1=40, piedras_2=20,
            ganador_juego=self.p1, subido_por=self.p1,
            estado=Juego.Estado.PENDIENTE_CONFIRMACION,
        )
        self.assertEqual(self.partida.juegos_pareja_1(), 0)


class InicioPartidaTest(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre="A")
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B", grupo=self.grupo)
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D", grupo=self.grupo)
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, grupo=self.grupo,
            pareja_1=self.p1, pareja_2=self.p2,
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
        self.assertEqual(self.partida.estado, Partida.Estado.PENDIENTE)


class SubirJuegoViewTest(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre="A")
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B", grupo=self.grupo)
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D", grupo=self.grupo)
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, grupo=self.grupo,
            pareja_1=self.p1, pareja_2=self.p2,
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
        self.assertEqual(juego.ganador_juego, self.p1)

    def test_rechaza_sin_40_piedras(self):
        resp = self.client.post(f"/pareja/{self.p1.token}/subir/", {
            "piedras_1": 35, "piedras_2": 25,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Juego.objects.count(), 0)

    def test_no_subir_si_partida_pendiente(self):
        self.partida.estado = Partida.Estado.PENDIENTE
        self.partida.save()
        resp = self.client.post(f"/pareja/{self.p1.token}/subir/", {
            "piedras_1": 40, "piedras_2": 25,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Juego.objects.count(), 0)


class ConfirmarJuegoViewTest(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre="A")
        self.p1 = Pareja.objects.create(nombre="P1", jugador1="A", jugador2="B", grupo=self.grupo)
        self.p2 = Pareja.objects.create(nombre="P2", jugador1="C", jugador2="D", grupo=self.grupo)
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.EN_CURSO)
        self.partida = Partida.objects.create(
            ronda=self.ronda, grupo=self.grupo,
            pareja_1=self.p1, pareja_2=self.p2,
            estado=Partida.Estado.EN_CURSO,
        )
        self.juego = Juego.objects.create(
            partida=self.partida, numero=1, piedras_1=40, piedras_2=25,
            ganador_juego=self.p1, subido_por=self.p1,
        )
        self.client = Client()

    def test_confirmar_juego(self):
        self.client.post(
            f"/pareja/{self.p2.token}/confirmar/{self.juego.pk}/",
            {"accion": "confirmar"},
        )
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.estado, Juego.Estado.CONFIRMADO)

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
        for i in range(2, 5):
            Juego.objects.create(
                partida=self.partida, numero=i, piedras_1=40, piedras_2=20,
                ganador_juego=self.p1, subido_por=self.p1,
                estado=Juego.Estado.CONFIRMADO,
            )
        self.client.post(
            f"/pareja/{self.p2.token}/confirmar/{self.juego.pk}/",
            {"accion": "confirmar"},
        )
        self.partida.refresh_from_db()
        self.assertEqual(self.partida.estado, Partida.Estado.FINALIZADA)
        self.assertEqual(self.partida.ganador, self.p1)


class EliminatoriasTest(TestCase):
    def setUp(self):
        """Crea 5 grupos con 5 parejas y resultados para generar clasificación."""
        self.ronda = Ronda.objects.create(numero=1, estado=Ronda.Estado.COMPLETADA)
        for letra in "ABCDE":
            g = Grupo.objects.create(nombre=letra)
            parejas = []
            for i in range(5):
                p = Pareja.objects.create(
                    nombre=f"{letra}{i}", jugador1=f"J{letra}{i}a",
                    jugador2=f"J{letra}{i}b", grupo=g,
                )
                parejas.append(p)
            # Crear resultados: p0 gana a todos, p1 gana a p2-p4, p2 gana a p3-p4, etc.
            for i in range(5):
                for j in range(i + 1, 5):
                    Partida.objects.create(
                        ronda=self.ronda, grupo=g,
                        pareja_1=parejas[i], pareja_2=parejas[j],
                        estado=Partida.Estado.FINALIZADA, ganador=parejas[i],
                    )

    def test_genera_8_octavos(self):
        ronda, partidas = generar_eliminatorias()
        self.assertIsNotNone(ronda)
        self.assertEqual(len(partidas), 8)
        self.assertEqual(ronda.fase, Ronda.Fase.OCTAVOS)

    def test_sin_cruces_mismo_grupo_en_octavos(self):
        _, partidas = generar_eliminatorias()
        for partida in partidas:
            self.assertNotEqual(
                partida.pareja_1.grupo_id,
                partida.pareja_2.grupo_id,
                f"Cruce del mismo grupo en octavos: {partida}",
            )

    def test_sin_cruces_mismo_grupo_en_cuartos(self):
        """Verifica que en cada cuarto de cuadro (2 octavos) no hay equipos del mismo grupo."""
        _, partidas = generar_eliminatorias()
        # Partidas se generan en pares: [0,1], [2,3], [4,5], [6,7] = 4 cuartos
        for i in range(0, 8, 2):
            grupos_en_cuarto = {
                partidas[i].pareja_1.grupo_id,
                partidas[i].pareja_2.grupo_id,
                partidas[i + 1].pareja_1.grupo_id,
                partidas[i + 1].pareja_2.grupo_id,
            }
            self.assertEqual(
                len(grupos_en_cuarto), 4,
                f"Cuarto {i // 2 + 1} tiene equipos del mismo grupo",
            )

    def test_16_parejas_distintas(self):
        _, partidas = generar_eliminatorias()
        parejas_ids = set()
        for p in partidas:
            parejas_ids.add(p.pareja_1_id)
            parejas_ids.add(p.pareja_2_id)
        self.assertEqual(len(parejas_ids), 16)


class VistasPublicasTest(TestCase):
    def test_inicio(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_clasificacion(self):
        resp = self.client.get("/clasificacion/")
        self.assertEqual(resp.status_code, 200)

    def test_grupo(self):
        g = Grupo.objects.create(nombre="A")
        resp = self.client.get(f"/grupo/{g.nombre}/")
        self.assertEqual(resp.status_code, 200)

    def test_panel_pareja(self):
        p = Pareja.objects.create(nombre="Test", jugador1="A", jugador2="B")
        resp = self.client.get(f"/pareja/{p.token}/")
        self.assertEqual(resp.status_code, 200)

    def test_panel_pareja_token_invalido(self):
        resp = self.client.get("/pareja/token-falso/")
        self.assertEqual(resp.status_code, 404)
