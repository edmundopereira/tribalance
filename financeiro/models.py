from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Lancamento(models.Model):
    """
    Modelo para representar lançamentos financeiros (receitas e despesas).
    Segue a estrutura definida no documento de requisitos.
    """
    
    TIPO_CHOICES = [ # <-- REVERTIDO para o original
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
        ('CRÉDITO', 'Crédito'),
        ('DÉBITO', 'Débito'),
    ]

    PILAR_CHOICES = [
        ('NECESSIDADE', 'Necessidade'),
        ('CONFORTO & EXPERIÊNCIA', 'Conforto & Experiência'),
        ('CRESCIMENTO & LIBERDADE', 'Crescimento & Liberdade'),
    ]
    
    MES_CHOICES = [
        ('JANEIRO', 'Janeiro'),
        ('FEVEREIRO', 'Fevereiro'),
        ('MARÇO', 'Março'),
        ('ABRIL', 'Abril'),
        ('MAIO', 'Maio'),
        ('JUNHO', 'Junho'),
        ('JULHO', 'Julho'),
        ('AGOSTO', 'Agosto'),
        ('SETEMBRO', 'Setembro'),
        ('OUTUBRO', 'Outubro'),
        ('NOVEMBRO', 'Novembro'),
        ('DEZEMBRO', 'Dezembro'),
    ]

    id = models.AutoField(primary_key=True)
    data = models.DateField(help_text="Data do lançamento (YYYY-MM-DD)")
    mes = models.CharField(max_length=15, choices=MES_CHOICES, help_text="Mês de referência") # <-- GARANTA QUE ESTA LINHA ESTÁ CORRETA
    lancamento = models.CharField(max_length=255, help_text="Descrição da transação") # <-- GARANTA QUE ESTA LINHA ESTÁ CORRETA
    categoria = models.CharField(max_length=100, help_text="Categoria original")
    # TIPO AGORA DEVE USAR CHOICES (Linha 45)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, help_text="Tipo de transação")     
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Valor monetário (positivo ou negativo)"
    )
    fonte = models.CharField(max_length=100, help_text="Conta de origem (ex: Santander, Nubank)")
    conta_final = models.CharField(max_length=50, help_text="Conta de destino (ex: Carteira, Poupança)")
    pilar_tribalance = models.CharField(
        max_length=50,
        choices=PILAR_CHOICES,
        help_text="Pilar em que o lançamento se enquadra"
    )
    
    # Campos adicionais para rastreamento
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data', '-criado_em']
        indexes = [
            models.Index(fields=['data']),
            # models.Index(fields=['mes']), # <-- REMOVIDO PARA CORRIGIR O ERRO
            models.Index(fields=['tipo']),
            models.Index(fields=['pilar_tribalance']),
            models.Index(fields=['categoria']),
            models.Index(fields=['fonte']),
        ]

        verbose_name = "Lançamento"
        verbose_name_plural = "Lançamentos"
    
    def __str__(self):
        return f"{self.data} - {self.lancamento} ({self.tipo}): R$ {self.valor}"
    
    def is_receita(self):
        return self.tipo in ['RECEITA', 'CRÉDITO']
    
    def is_despesa(self):
        return self.tipo in ['DESPESA', 'DÉBITO']


class MetaFinanceira(models.Model):
    """
    Modelo para metas financeiras de longo prazo.
    """
    
    id = models.AutoField(primary_key=True)
    nome_meta = models.CharField(max_length=100, help_text="Nome da meta (aposentadoria, viagem...)")
    valor_alvo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Valor total desejado"
    )
    prazo_anos = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Prazo em anos para atingir a meta"
    )
    valor_mensal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Aporte mensal recomendado"
    )
    progresso = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentual atingido (0–100%)"
    )
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Meta Financeira"
        verbose_name_plural = "Metas Financeiras"
    
    def __str__(self):
        return f"{self.nome_meta} - R$ {self.valor_alvo} ({self.prazo_anos} anos)"


class MetaMensal(models.Model):
    """
    Modelo para metas mensais de orçamento por pilar.
    """
    
    PILAR_CHOICES = [
        ('NECESSIDADE', 'Necessidade'),
        ('CONFORTO & EXPERIÊNCIA', 'Conforto & Experiência'),
        ('CRESCIMENTO & LIBERDADE', 'Crescimento & Liberdade'),
    ]
    
    id = models.AutoField(primary_key=True)
    pilar = models.CharField(max_length=50, choices=PILAR_CHOICES, unique=True)
    percentual_ideal = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentual ideal da renda para este pilar"
    )
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Meta Mensal"
        verbose_name_plural = "Metas Mensais"
    
    def __str__(self):
        return f"{self.pilar} - {self.percentual_ideal}%"


class CategoriaPilar(models.Model):
    """
    Modelo para mapear categorias específicas a pilares do TriBalance.
    Permite classificação automática de transações.
    """
    
    PILAR_CHOICES = [
        ('NECESSIDADE', 'Necessidade'),
        ('CONFORTO & EXPERIÊNCIA', 'Conforto & Experiência'),
        ('CRESCIMENTO & LIBERDADE', 'Crescimento & Liberdade'),
    ]
    
    id = models.AutoField(primary_key=True)
    categoria = models.CharField(max_length=100, unique=True, help_text="Nome da categoria")
    pilar = models.CharField(max_length=50, choices=PILAR_CHOICES)
    palavras_chave = models.TextField(
        blank=True,
        help_text="Palavras-chave separadas por vírgula para identificação automática"
    )
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Categoria Pilar"
        verbose_name_plural = "Categorias Pilar"
    
    def __str__(self):
        return f"{self.categoria} → {self.pilar}"


class ImportacaoLog(models.Model):
    """
    Modelo para registrar histórico de importações de extratos.
    """
    
    STATUS_CHOICES = [
        ('SUCESSO', 'Sucesso'),
        ('ERRO', 'Erro'),
        ('PARCIAL', 'Parcial'),
    ]
    
    id = models.AutoField(primary_key=True)
    arquivo = models.FileField(upload_to='importacoes/')
    data_importacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    total_registros = models.IntegerField(default=0)
    registros_importados = models.IntegerField(default=0)
    registros_duplicados = models.IntegerField(default=0)
    registros_rejeitados = models.IntegerField(default=0)
    mensagem = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-data_importacao']
        verbose_name = "Log de Importação"
        verbose_name_plural = "Logs de Importação"
    
    def __str__(self):
        return f"Importação {self.data_importacao.strftime('%d/%m/%Y %H:%M')} - {self.status}"

