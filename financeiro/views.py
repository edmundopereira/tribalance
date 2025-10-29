from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
from decimal import Decimal
import json

from .models import Lancamento, MetaFinanceira, MetaMensal, CategoriaPilar, ImportacaoLog
from .utils import (
    processar_arquivo_importacao,
    calcular_kpis,
    classificar_lancamento,
    exportar_csv,
    exportar_excel
)


def dashboard(request):
    """
    View para o dashboard principal com KPIs e gráficos.
    """
    # Filtros
    periodo = request.GET.get('periodo', 'mes')  # mes, trimestre, ano
    conta = request.GET.get('conta', '')
    
    # Determinar data de início baseado no período
    hoje = timezone.now().date()
    if periodo == 'mes':
        data_inicio = hoje.replace(day=1)
    elif periodo == 'trimestre':
        trimestre = (hoje.month - 1) // 3
        data_inicio = hoje.replace(month=trimestre * 3 + 1, day=1)
    else:  # ano
        data_inicio = hoje.replace(month=1, day=1)
    
    # Query base
    lancamentos = Lancamento.objects.filter(data__gte=data_inicio)
    
    if conta:
        lancamentos = lancamentos.filter(fonte=conta)
    
    # Calcular KPIs
    kpis = calcular_kpis(lancamentos)
    
    # Dados para gráficos
    fluxo_caixa = calcular_fluxo_caixa(lancamentos)
    distribuicao_pilares = calcular_distribuicao_pilares(lancamentos)
    
    # Contas disponíveis
    contas = Lancamento.objects.values_list('fonte', flat=True).distinct()
    
    context = {
        'kpis': kpis,
        'fluxo_caixa_json': json.dumps(fluxo_caixa),
        'distribuicao_pilares_json': json.dumps(distribuicao_pilares),
        'periodo': periodo,
        'conta': conta,
        'contas': contas,
        'data_inicio': data_inicio,
        'data_fim': hoje,
    }
    
    return render(request, 'financeiro/dashboard.html', context)


def importacao(request):
    """
    View para upload de arquivo de importação.
    """
    if request.method == 'POST':
        arquivo = request.FILES.get('arquivo')
        
        if not arquivo:
            messages.error(request, 'Por favor, selecione um arquivo.')
            return redirect('financeiro:importacao')
        
        try:
            resultado = processar_arquivo_importacao(arquivo)
            
            # Registrar no log
            log = ImportacaoLog.objects.create(
                arquivo=arquivo,
                status=resultado['status'],
                total_registros=resultado['total'],
                registros_importados=resultado['importados'],
                registros_duplicados=resultado['duplicados'],
                registros_rejeitados=resultado['rejeitados'],
                mensagem=resultado['mensagem']
            )
            
            messages.success(
                request,
                f"Importação concluída! {resultado['importados']} registros importados, "
                f"{resultado['duplicados']} duplicados, {resultado['rejeitados']} rejeitados."
            )
            
            return redirect('financeiro:dashboard')
        
        except Exception as e:
            messages.error(request, f'Erro ao processar arquivo: {str(e)}')
            return redirect('financeiro:importacao')
    
    # GET - exibir formulário
    logs_recentes = ImportacaoLog.objects.all()[:5]
    
    context = {
        'logs_recentes': logs_recentes,
    }
    
    return render(request, 'financeiro/importacao.html', context)


def lista_lancamentos(request):
    """
    View para listar lançamentos em formato tabular com paginação e filtros.
    RF11 - Relatório Tabular de Lançamentos
    """
    # Inicializar queryset
    lancamentos = Lancamento.objects.all()
    
    # Aplicar filtros
    filtros_aplicados = {}
    
    # Filtro por data
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio:
        lancamentos = lancamentos.filter(data__gte=data_inicio)
        filtros_aplicados['data_inicio'] = data_inicio
    if data_fim:
        lancamentos = lancamentos.filter(data__lte=data_fim)
        filtros_aplicados['data_fim'] = data_fim
    
    # Filtro por mês
    mes = request.GET.get('mes')
    if mes:
        lancamentos = lancamentos.filter(mes=mes)
        filtros_aplicados['mes'] = mes
    
    # Filtro por tipo
    tipo = request.GET.get('tipo')
    if tipo:
        lancamentos = lancamentos.filter(tipo=tipo)
        filtros_aplicados['tipo'] = tipo
    
    # Filtro por categoria
    categoria = request.GET.get('categoria')
    if categoria:
        lancamentos = lancamentos.filter(categoria=categoria)
        filtros_aplicados['categoria'] = categoria
    
    # Filtro por pilar
    pilar = request.GET.get('pilar')
    if pilar:
        lancamentos = lancamentos.filter(pilar_tribalance=pilar)
        filtros_aplicados['pilar'] = pilar
    
    # Filtro por fonte
    fonte = request.GET.get('fonte')
    if fonte:
        lancamentos = lancamentos.filter(fonte=fonte)
        filtros_aplicados['fonte'] = fonte
    
    # Filtro por conta final
    conta_final = request.GET.get('conta_final')
    if conta_final:
        lancamentos = lancamentos.filter(conta_final=conta_final)
        filtros_aplicados['conta_final'] = conta_final
    
    # Filtro por descrição (busca)
    busca = request.GET.get('busca')
    if busca:
        lancamentos = lancamentos.filter(lancamento__icontains=busca)
        filtros_aplicados['busca'] = busca
    
    # Ordenação
    ordem = request.GET.get('ordem', '-data')
    lancamentos = lancamentos.order_by(ordem)
    
    # Calcular resumo dos resultados
    total_registros = lancamentos.count()
    soma_valores = lancamentos.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Paginação
    paginator = Paginator(lancamentos, 25)  # 25 registros por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    meses = Lancamento.MES_CHOICES
    tipos = Lancamento.TIPO_CHOICES
    pilares = Lancamento.PILAR_CHOICES
    categorias = Lancamento.objects.values_list('categoria', flat=True).distinct()
    fontes = Lancamento.objects.values_list('fonte', flat=True).distinct()
    contas_finais = Lancamento.objects.values_list('conta_final', flat=True).distinct()
    
    # Exportação
    if request.GET.get('export'):
        formato = request.GET.get('export')
        if formato == 'csv':
            return exportar_csv(lancamentos, 'lancamentos')
        elif formato == 'excel':
            return exportar_excel(lancamentos, 'lancamentos')
    
    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'total_registros': total_registros,
        'soma_valores': soma_valores,
        'filtros_aplicados': filtros_aplicados,
        'meses': meses,
        'tipos': tipos,
        'pilares': pilares,
        'categorias': categorias,
        'fontes': fontes,
        'contas_finais': contas_finais,
        'ordem': ordem,
    }
    
    return render(request, 'financeiro/lista_lancamentos.html', context)


def planejamento(request):
    """
    View para planejamento orçamentário.
    RF03 - Planejamento Orçamentário
    """
    # Obter ou criar metas mensais padrão
    metas_padrao = {
        'NECESSIDADE': 55,
        'CONFORTO & EXPERIÊNCIA': 30,
        'CRESCIMENTO & LIBERDADE': 15,
    }
    
    metas = {}
    for pilar, percentual in metas_padrao.items():
        meta, created = MetaMensal.objects.get_or_create(
            pilar=pilar,
            defaults={'percentual_ideal': percentual}
        )
        metas[pilar] = meta
    
    # Calcular dados do mês atual
    hoje = timezone.now().date()
    data_inicio = hoje.replace(day=1)
    lancamentos_mes = Lancamento.objects.filter(data__gte=data_inicio)
    
    # Calcular totais por pilar
    distribuicao = {}
    receita_total = Decimal('0.00')
    
    # Mapeamento para chaves simples no template (CORREÇÃO SYNTAX ERROR)
    chave_map = {
        'NECESSIDADE': 'NECESSIDADE',
        'CONFORTO & EXPERIÊNCIA': 'CONFORTO_EXPERIENCIA',  
        'CRESCIMENTO & LIBERDADE': 'CRESCIMENTO_LIBERDADE',  
    }
    
    for pilar, chave_simples in chave_map.items():
        total = lancamentos_mes.filter(
            pilar_tribalance=pilar,
            tipo__in=['DESPESA', 'DÉBITO']
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        distribuicao[chave_simples] = {
            'total': abs(total),
            'meta': metas[pilar],
        }
    
    # Calcular receita total
    receita_total = lancamentos_mes.filter(
        tipo__in=['RECEITA', 'CRÉDITO']
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Calcular percentuais
    if receita_total > 0:
        for pilar_original, chave_simples in chave_map.items():
            distribuicao[chave_simples]['percentual'] = (
                (distribuicao[chave_simples]['total'] / receita_total) * 100
            )
            distribuicao[chave_simples]['status'] = calcular_status(
                distribuicao[chave_simples]['percentual'],
                distribuicao[chave_simples]['meta'].percentual_ideal
            )
    
    context = {
        'metas': metas,
        'distribuicao': distribuicao,
        'receita_total': receita_total,
    }
    
    return render(request, 'financeiro/planejamento.html', context)


def atualizar_meta(request):
    """
    View para atualizar metas mensais (AJAX).
    """
    if request.method == 'POST':
        pilar = request.POST.get('pilar')
        percentual = request.POST.get('percentual')
        
        try:
            meta = MetaMensal.objects.get(pilar=pilar)
            meta.percentual_ideal = Decimal(percentual)
            meta.save()
            
            return render(request, 'financeiro/partials/meta_atualizada.html', {
                'meta': meta,
                'sucesso': True
            })
        except Exception as e:
            return render(request, 'financeiro/partials/meta_atualizada.html', {
                'erro': str(e),
                'sucesso': False
            })


def projecao(request):
    """
    View para projeção financeira.
    RF04 - Projeção Financeira
    """
    horizonte = request.GET.get('horizonte', 'longo')  # curto, medio, longo
    aporte_mensal = Decimal(request.GET.get('aporte_mensal', '1000'))
    taxa_retorno = Decimal(request.POST.get('taxa_retorno', '0.00')) / 100
    taxa_mensal = Decimal(str((1 + float(taxa_retorno)) ** (1/12) - 1))

    
    # Determinar período
    if horizonte == 'curto':
        meses = 12
    elif horizonte == 'medio':
        meses = 60
    else:  # longo
        meses = 132  # 11 anos
    
    # Calcular patrimônio inicial
    saldo_inicial = Lancamento.objects.filter(
        pilar_tribalance='CRESCIMENTO & LIBERDADE'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Simular crescimento
    projecao_dados = []
    patrimonio = saldo_inicial
    taxa_retorno = Decimal(request.POST.get('taxa_retorno', '0.00')) / 100
    
    # Linha 340 Corrigida: Converte a base da potência para float
    taxa_mensal = (1 + float(taxa_retorno)) ** (1/12) - 1
    
    # Converte o resultado de volta para Decimal para o restante dos cálculos
    taxa_mensal = Decimal(str(taxa_mensal))


    
    for mes in range(meses + 1):
        projecao_dados.append({
            'mes': mes,
            'patrimonio': float(patrimonio),
        })
        patrimonio = patrimonio * (1 + taxa_mensal) + aporte_mensal
    
    context = {
        'horizonte': horizonte,
        'aporte_mensal': aporte_mensal,
        'taxa_retorno': taxa_retorno * 100,
        'projecao_json': json.dumps(projecao_dados),
        'patrimonio_final': float(patrimonio),
    }
    
    return render(request, 'financeiro/projecao.html', context)


def relatorio(request):
    """
    View para relatório e parecer financeiro.
    RF05 - Relatório e Parecer Financeiro
    """
    periodo = request.GET.get('periodo', 'mes')
    
    # Determinar período
    hoje = timezone.now().date()
    if periodo == 'mes':
        data_inicio = hoje.replace(day=1)
    elif periodo == 'trimestre':
        trimestre = (hoje.month - 1) // 3
        data_inicio = hoje.replace(month=trimestre * 3 + 1, day=1)
    else:  # ano
        data_inicio = hoje.replace(month=1, day=1)
    
    lancamentos = Lancamento.objects.filter(data__gte=data_inicio)
    
    # Calcular métricas
    kpis = calcular_kpis(lancamentos)
    
    # Análise por pilar
    analise_pilares = {}
    for pilar, _ in Lancamento.PILAR_CHOICES:
        total = lancamentos.filter(pilar_tribalance=pilar).aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        analise_pilares[pilar] = {
            'total': abs(total),
            'percentual': 0,
        }
    
    # Calcular percentuais
    total_geral = sum(p['total'] for p in analise_pilares.values())
    if total_geral > 0:
        for pilar in analise_pilares:
            analise_pilares[pilar]['percentual'] = (
                (analise_pilares[pilar]['total'] / total_geral) * 100
            )
    
    # Gerar parecer
    parecer = gerar_parecer(kpis, analise_pilares)
    
    context = {
        'periodo': periodo,
        'kpis': kpis,
        'analise_pilares': analise_pilares,
        'parecer': parecer,
        'data_inicio': data_inicio,
        'data_fim': hoje,
    }
    
    return render(request, 'financeiro/relatorio.html', context)


# Funções auxiliares

def calcular_fluxo_caixa(lancamentos):
    """
    Calcula fluxo de caixa diário para gráfico de linha.
    """
    dados_por_dia = {}
    
    for lancamento in lancamentos:
        data_str = lancamento.data.isoformat()
        if data_str not in dados_por_dia:
            dados_por_dia[data_str] = Decimal('0.00')
        
        if lancamento.is_receita():
            dados_por_dia[data_str] += lancamento.valor
        else:
            dados_por_dia[data_str] -= abs(lancamento.valor)
    
    # Ordenar por data
    dados_ordenados = sorted(dados_por_dia.items())
    
    return {
        'labels': [item[0] for item in dados_ordenados],
        'data': [float(item[1]) for item in dados_ordenados],
    }


def calcular_distribuicao_pilares(lancamentos):
    """
    Calcula distribuição de despesas por pilar para gráfico de pizza.
    """
    distribuicao = {}
    
    for pilar, label in Lancamento.PILAR_CHOICES:
        total = lancamentos.filter(
            pilar_tribalance=pilar,
            tipo__in=['DESPESA', 'DÉBITO']
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        distribuicao[label] = float(abs(total))
    
    return {
        'labels': list(distribuicao.keys()),
        'data': list(distribuicao.values()),
    }


def calcular_status(percentual_atual, percentual_ideal):
    """
    Calcula status da meta (Dentro, Acima, Abaixo).
    """
    margem = 5  # 5% de margem
    
    if abs(percentual_atual - percentual_ideal) <= margem:
        return 'Dentro'
    elif percentual_atual > percentual_ideal:
        return 'Acima'
    else:
        return 'Abaixo'


def gerar_parecer(kpis, analise_pilares):
    """
    Gera parecer financeiro baseado nos KPIs.
    """
    parecer = {
        'pontos_fortes': [],
        'pontos_atencao': [],
        'recomendacoes': [],
    }
    
    # Análise de pontos fortes
    if kpis['fbi'] > 1:
        parecer['pontos_fortes'].append('Equilíbrio financeiro positivo')
    
    if kpis['sbi'] > 0.5:
        parecer['pontos_fortes'].append('Reserva de segurança adequada')
    
    # Análise de pontos de atenção
    if analise_pilares['NECESSIDADE']['percentual'] > 60:
        parecer['pontos_atencao'].append('Despesas de necessidade acima do ideal')
    
    if analise_pilares['CRESCIMENTO & LIBERDADE']['percentual'] < 10:
        parecer['pontos_atencao'].append('Aportes para crescimento abaixo do ideal')
    
    # Recomendações
    if not parecer['pontos_fortes']:
        parecer['recomendacoes'].append('Revisar categorização de despesas')
    
    if parecer['pontos_atencao']:
        parecer['recomendacoes'].append('Considerar reduzir despesas em categorias não essenciais')
    
    parecer['recomendacoes'].append('Manter disciplina no aporte mensal para investimentos')
    
    return parecer
