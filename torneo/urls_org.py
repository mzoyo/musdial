from django.contrib.auth import views as auth_views
from django.urls import path

from . import views_org

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="organizacion/login.html"), name="org_login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/organizacion/login/"), name="org_logout"),
    path("", views_org.dashboard, name="org_dashboard"),
    path("parejas/", views_org.parejas_lista, name="org_parejas"),
    path("parejas/nueva/", views_org.pareja_crear, name="org_pareja_crear"),
    path("parejas/<int:pk>/editar/", views_org.pareja_editar, name="org_pareja_editar"),
    path("grupos/", views_org.grupos_lista, name="org_grupos"),
    path("grupos/iniciar/", views_org.iniciar_torneo, name="org_iniciar_torneo"),
    path("grupos/<int:pk>/", views_org.grupo_detalle_org, name="org_grupo_detalle"),
    path("jornadas/<int:pk>/completar/", views_org.completar_jornada, name="org_completar_jornada"),
    path("grupos/octavos/", views_org.generar_octavos, name="org_generar_octavos"),
    path("metricas/", views_org.metricas, name="org_metricas"),
    path("partidas-libres/", views_org.partidas_libres, name="org_partidas_libres"),
    path("partidas-libres/<int:pk>/borrar/", views_org.borrar_libre, name="org_borrar_libre"),
    path("partidas-libres/borrar-todas/", views_org.borrar_todas_libres, name="org_borrar_libres"),
]
