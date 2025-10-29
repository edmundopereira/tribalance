from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('importacao/', views.importacao, name='importacao'),
    path('lancamentos/', views.lista_lancamentos, name='lista_lancamentos'),
    path('planejamento/', views.planejamento, name='planejamento'),
    path('projecao/', views.projecao, name='projecao'),
    path('relatorio/', views.relatorio, name='relatorio'),
    
    # Rotas de Ação (exemplo: para AJAX)
    # path('atualizar_meta/', views.atualizar_meta, name='atualizar_meta'), # Removida para corrigir o AttributeError
]
