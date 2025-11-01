from django.urls import path
from . import views

app_name = 'dividas'

urlpatterns = [
    path('', views.divida_list, name='divida_list'),
    path('nova/', views.divida_create, name='divida_create'),
    path('<int:pk>/', views.divida_detalhe, name='divida_detalhe'),
    path('importar/', views.importar_excel_view, name='importar_excel'),
    path('saldo-mensal/', views.saldo_parcelas_chart, name='saldo_mensal_chart'),

]
