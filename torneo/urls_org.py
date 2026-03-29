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
    path("rondas/", views_org.rondas_lista, name="org_rondas"),
    path("rondas/generar/", views_org.generar_ronda, name="org_generar_ronda"),
    path("rondas/<int:pk>/completar/", views_org.completar_ronda, name="org_completar_ronda"),
    path("rondas/<int:pk>/", views_org.ronda_detalle_org, name="org_ronda_detalle"),
    path("rondas/octavos/", views_org.generar_octavos, name="org_generar_octavos"),
    path("metricas/", views_org.metricas, name="org_metricas"),
]
