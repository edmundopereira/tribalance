from django import forms
from .models import Divida

class DividaForm(forms.ModelForm):
    class Meta:
        model = Divida
        fields = ['descricao', 'categoria', 'forma_pagamento', 'data_compra', 'valor_total', 'parcelas_totais', 'observacao']
