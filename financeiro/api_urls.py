from django.urls import path
from . import api_views

app_name = 'api'

urlpatterns = [
    # API REST para Lançamentos
    path('lancamentos/', api_views.LancamentoListView.as_view(), name='lancamento-list'),
    path('lancamentos/<int:pk>/', api_views.LancamentoDetailView.as_view(), name='lancamento-detail'),
    
    # API REST para Metas
    path('metas/', api_views.MetaFinanceiraListView.as_view(), name='meta-list'),
    
    # API para dados do dashboard
    path('dashboard/kpis/', api_views.DashboardKPIsView.as_view(), name='dashboard-kpis'),
    path('dashboard/fluxo-caixa/', api_views.FluxoCaixaView.as_view(), name='fluxo-caixa'),
    path('dashboard/distribuicao-pilares/', api_views.DistribuicaoPilaresView.as_view(), name='distribuicao-pilares'),
]

