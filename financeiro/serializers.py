from rest_framework import serializers
from .models import Lancamento, MetaFinanceira, MetaMensal, CategoriaPilar


class LancamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lancamento
        fields = [
            'id', 'data', 'mes', 'lancamento', 'categoria', 'tipo',
            'valor', 'fonte', 'conta_final', 'pilar_tribalance',
            'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']


class MetaFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaFinanceira
        fields = [
            'id', 'nome_meta', 'valor_alvo', 'prazo_anos',
            'valor_mensal', 'progresso', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']


class MetaMensalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaMensal
        fields = [
            'id', 'pilar', 'percentual_ideal', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']


class CategoriaPilarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaPilar
        fields = [
            'id', 'categoria', 'pilar', 'palavras_chave', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']

