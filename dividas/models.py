from django.db import models
from django.utils import timezone


class Divida(models.Model):
    """
    Modelo que representa uma dívida parcelada. Inclui lógica para determinar se a dívida
    está no ciclo de cobrança atual (fatura em aberto) e retorna seu status de acordo
    com a data de compra e a regra de pagamento até o dia 15 de cada mês.
    """

    CATEGORIAS = [
        ('cartao', 'Cartão de Crédito'),
        ('emprestimo', 'Empréstimo'),
        ('compra', 'Compra Parcelada'),
        ('outro', 'Outros'),
    ]

    FORMAS_PAGAMENTO = [
        ('credito', 'Cartão de Crédito'),
        ('debito', 'Débito em Conta'),
        ('boleto', 'Boleto'),
        ('pix', 'Pix'),
        ('outro', 'Outro'),
    ]

    descricao = models.CharField(max_length=150)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='compra')
    forma_pagamento = models.CharField(max_length=20, choices=FORMAS_PAGAMENTO, default='credito')
    data_compra = models.DateField(default=timezone.now)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    parcelas_totais = models.PositiveIntegerField(default=1)
    tipo_despesa = models.CharField(max_length=50, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    quitada = models.BooleanField(default=False)

    # Novos campos para armazenar mês e ano de referência (ex.: vencimento da primeira parcela)
    # O campo "mes" deve conter o nome do mês em português (Janeiro, Fevereiro, etc.).
    # O campo "ano" deve conter o valor numérico do ano.
    mes = models.CharField(max_length=20, blank=True, null=True)
    ano = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.descricao} - {self.valor_total}"

    @property
    def valor_parcela(self):
        """Retorna o valor de cada parcela (valor total dividido pelo número de parcelas)."""
        return round(self.valor_total / self.parcelas_totais, 2)

    @property
    def parcelas_restantes(self):
        """Conta quantas parcelas ainda não foram marcadas como pagas."""
        return self.parcelas.filter(paga=False).count()

    @property
    def is_open(self):
        """
        Determina se a dívida está no ciclo aberto de cobrança, seguindo a regra:
        - As faturas são pagas até o dia 15 de cada mês.
        - O ciclo de cobrança vai do dia 16 do mês anterior até o dia 15 do mês corrente.
        - Se hoje é dia >15, o ciclo passa a ser do dia 16 do mês corrente ao dia 15 do mês seguinte.
        Se a data de compra (data_compra) da dívida está dentro do ciclo aberto, retorna True.
        """
        from datetime import date
        today = timezone.localdate()
        if today.day > 15:
            # ciclo aberto é de 16 do mês atual até 15 do próximo mês
            cycle_start = date(today.year, today.month, 16)
            cycle_end_year = today.year + (today.month == 12)
            cycle_end_month = (today.month % 12) + 1
            cycle_end = date(cycle_end_year, cycle_end_month, 15)
        else:
            # ciclo aberto é de 16 do mês anterior até 15 do mês atual
            cycle_end = date(today.year, today.month, 15)
            cycle_start_month = today.month - 1 if today.month > 1 else 12
            cycle_start_year = today.year if today.month > 1 else today.year - 1
            cycle_start = date(cycle_start_year, cycle_start_month, 16)
        return cycle_start <= self.data_compra <= cycle_end

    @property
    def status(self):
        """Retorna 'Em aberto' ou 'Quitada' de acordo com o resultado de is_open()."""
        return 'Em aberto' if self.is_open else 'Quitada'


class Parcela(models.Model):
    """Representa uma parcela associada a uma Divida."""
    divida = models.ForeignKey(Divida, related_name='parcelas', on_delete=models.CASCADE)
    numero = models.PositiveIntegerField()
    vencimento = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    paga = models.BooleanField(default=False)
    data_pagamento = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.divida.descricao} - Parcela {self.numero}/{self.divida.parcelas_totais}"