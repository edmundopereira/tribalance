from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum
from decimal import Decimal
import json

from .models import Lancamento, MetaFinanceira
from .serializers import LancamentoSerializer, MetaFinanceiraSerializer
from .views import calcular_fluxo_caixa, calcular_distribuicao_pilares, calcular_kpis


class LancamentoListView(generics.ListCreateAPIView):
    """
    API para listar e criar lançamentos.
    RF08 - API REST
    """
    queryset = Lancamento.objects.all()
    serializer_class = LancamentoSerializer
    
    def get_queryset(self):
        queryset = Lancamento.objects.all()
        
        # Filtros
        periodo = self.request.query_params.get('periodo')
        tipo = self.request.query_params.get('tipo')
        pilar = self.request.query_params.get('pilar')
        categoria = self.request.query_params.get('categoria')
        conta = self.request.query_params.get('conta')
        
        if periodo:
            queryset = queryset.filter(mes=periodo)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if pilar:
            queryset = queryset.filter(pilar_tribalance=pilar)
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        if conta:
            queryset = queryset.filter(fonte=conta)
        
        return queryset


class LancamentoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API para recuperar, atualizar ou deletar um lançamento específico.
    """
    queryset = Lancamento.objects.all()
    serializer_class = LancamentoSerializer


class MetaFinanceiraListView(generics.ListCreateAPIView):
    """
    API para listar e criar metas financeiras.
    """
    queryset = MetaFinanceira.objects.all()
    serializer_class = MetaFinanceiraSerializer


class DashboardKPIsView(APIView):
    """
    API para obter KPIs do dashboard.
    RF02 - Dashboard Financeiro
    """
    def get(self, request):
        lancamentos = Lancamento.objects.all()
        kpis = calcular_kpis(lancamentos)
        
        return Response(kpis, status=status.HTTP_200_OK)


class FluxoCaixaView(APIView):
    """
    API para obter dados de fluxo de caixa.
    """
    def get(self, request):
        lancamentos = Lancamento.objects.all()
        fluxo_caixa = calcular_fluxo_caixa(lancamentos)
        
        return Response(fluxo_caixa, status=status.HTTP_200_OK)


class DistribuicaoPilaresView(APIView):
    """
    API para obter distribuição de despesas por pilar.
    """
    def get(self, request):
        lancamentos = Lancamento.objects.all()
        distribuicao = calcular_distribuicao_pilares(lancamentos)
        
        return Response(distribuicao, status=status.HTTP_200_OK)

