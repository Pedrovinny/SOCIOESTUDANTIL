from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("admin/",          admin.site.urls),
    # existentes
    path("",                views.home,             name="home"),
    path("importar/",       views.importar_csv,     name="importar_csv"),
    path("leitor/",         views.leitor,            name="leitor"),
    path("relatorio/",      views.relatorio,         name="relatorio"),
    # novos
    path("alunos/",                        views.listar_alunos_view, name="listar_alunos"),
    path("alunos/<int:aluno_id>/perfil/",  views.perfil,             name="perfil"),
    path("beneficios/",                    views.beneficios,          name="beneficios"),
    path("painel/",                        views.painel,              name="painel"),
    path("relatorio-pdf/",                 views.relatorio_pdf,       name="relatorio_pdf"),
]