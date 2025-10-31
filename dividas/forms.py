from django import forms
from .models import Divida

class DividaForm(forms.ModelForm):
    class Meta:
        model = Divida
        fields = ['descricao', 'categoria', 'forma_pagamento', 'data_compra', 'valor_total', 'parcelas_totais', 'observacao']


class DividaFilterForm(forms.Form):
    # Campos de filtro que aparecem na tela
    mes = forms.CharField(required=False)
    ano = forms.CharField(required=False)
    tipo_despesa = forms.CharField(required=False)
    descricao = forms.CharField(required=False)
    forma_pagamento = forms.CharField(required=False)
    valor_parcela = forms.CharField(required=False)
    status = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adiciona choices dinâmicos para campos que precisam
        
        # Mês (Todos os meses existentes nas dívidas)
        meses_disponiveis = Divida.objects.exclude(mes__isnull=True).values_list('mes', flat=True).distinct().order_by('mes')
        mes_choices = [('', 'Todos')] + [(m, m) for m in meses_disponiveis]
        self.fields['mes'] = forms.ChoiceField(choices=mes_choices, required=False)

        # Ano (Todos os anos existentes nas dívidas)
        anos_disponiveis = Divida.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('ano')
        ano_choices = [('', 'Todos')] + [(str(a), str(a)) for a in anos_disponiveis]
        self.fields['ano'] = forms.ChoiceField(choices=ano_choices, required=False)

        # Tipo de Despesa
        tipos_disponiveis = Divida.objects.exclude(tipo_despesa__isnull=True).values_list('tipo_despesa', flat=True).distinct().order_by('tipo_despesa')
        tipo_choices = [('', 'Todos')] + [(t, t) for t in tipos_disponiveis]
        self.fields['tipo_despesa'] = forms.ChoiceField(choices=tipo_choices, required=False)

        # Forma de Pagamento
        forma_choices = [('', 'Todos')] + list(Divida.FORMAS_PAGAMENTO)
        self.fields['forma_pagamento'] = forms.ChoiceField(choices=forma_choices, required=False)

        # Status
        status_choices = [('', 'Todos'), ('Em aberto', 'Em aberto'), ('Quitada', 'Quitada')]
        self.fields['status'] = forms.ChoiceField(choices=status_choices, required=False)