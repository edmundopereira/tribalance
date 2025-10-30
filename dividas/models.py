from django.db import models
from django.utils import timezone

class Divida(models.Model):
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
    tipo_despesa = models.CharField(max_length=50, blank=True, null=True)  # campo novo
    observacao = models.TextField(blank=True, null=True)
    quitada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.descricao} - {self.valor_total}"

    @property
    def valor_parcela(self):
        return round(self.valor_total / self.parcelas_totais, 2)

    @property
    def parcelas_restantes(self):
        return self.parcelas.filter(paga=False).count()

class Parcela(models.Model):
    divida = models.ForeignKey(Divida, related_name='parcelas', on_delete=models.CASCADE)
    numero = models.PositiveIntegerField()
    vencimento = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    paga = models.BooleanField(default=False)
    data_pagamento = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.divida.descricao} - Parcela {self.numero}/{self.divida.parcelas_totais}"
