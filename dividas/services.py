from datetime import date
from dateutil.relativedelta import relativedelta
from .models import Parcela

def gerar_parcelas(divida):
    data_venc = divida.data_compra
    valor = divida.valor_parcela

    for i in range(1, divida.parcelas_totais + 1):
        Parcela.objects.create(
            divida=divida,
            numero=i,
            vencimento=data_venc + relativedelta(months=i),
            valor=valor
        )
