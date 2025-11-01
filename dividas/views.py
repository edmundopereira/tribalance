# C:\projetos\tribalance_config\dividas\views.py

# --- Correção do Matplotlib (DEVE SER O PRIMEIRO) ---
import matplotlib
matplotlib.use('Agg')

# --- Bloco Único de Importações ---
import io
import base64
from datetime import date
from collections import defaultdict
from decimal import Decimal 
import math 

# Imports do Django
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

# Imports de Bibliotecas Externas
import pandas as pd
from unidecode import unidecode

# Imports Locais (do seu app)
from .models import Divida, Parcela
from .forms import DividaForm
from .services import gerar_parcelas
from .importer import importar_dividas_de_excel


# --- Funções Auxiliares (Mantidas Intactas) ---

def calcular_mes_referencia(data_vencimento):
    """
    Calcula o mês de referência (mês anterior ao vencimento).
    """
    venc = data_vencimento
    mes_venc = venc.month
    ano_venc = venc.year

    if mes_venc == 1:
        # Vencimento em Janeiro -> Mês de referência é Dezembro do ano anterior
        mes_ref = 12
        ano_ref = ano_venc - 1
    else:
        # Demais meses -> Mês de referência é o mês anterior do mesmo ano
        mes_ref = mes_venc - 1
        ano_ref = ano_venc
        
    return ano_ref, mes_ref

# --- View do Gráfico (PARA CHART.JS) ---

def saldo_parcelas_chart(request):
    """
    Calcula o saldo mensal do "Total Valor das Parcelas" e prepara os dados para o Chart.js.
    """
    # 1. Coleta de dados
    dividas = Divida.objects.all().prefetch_related('parcelas')
    
    # 2. Cálculo do Saldo Mensal (usando Decimal para precisão)
    saldo_mensal = defaultdict(Decimal) 

    for divida in dividas:
        valor_parcela = divida.valor_parcela 
        parcelas_ordenadas = divida.parcelas.all().order_by('vencimento') 
        
        if not parcelas_ordenadas:
            continue

        primeira_parcela = parcelas_ordenadas.first()
        ultima_parcela = parcelas_ordenadas.last()

        # O mês de referência é o mês anterior ao vencimento.
        # Para a primeira parcela, o mês de referência é o mês anterior ao seu vencimento.
        # Para a última parcela, o mês de referência é o mês anterior ao seu vencimento.
        ano_ref_ini, mes_ref_ini = calcular_mes_referencia(primeira_parcela.vencimento)
        ano_ref_fim, mes_ref_fim = calcular_mes_referencia(ultima_parcela.vencimento)

        current_year = ano_ref_ini
        current_month = mes_ref_ini
        
        while True:
            key = f"{current_year}-{current_month:02d}"
            saldo_mensal[key] += valor_parcela
            
            if current_year == ano_ref_fim and current_month == mes_ref_fim:
                break
            
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
                
            # Limite de segurança para evitar loops infinitos em caso de dados inconsistentes
            if current_year > ano_ref_fim + 50:
                break


    # 3. Preparação dos dados para o Chart.js
    if not saldo_mensal:
        return render(request, 'dividas/saldo_chart.html', {'chart_data_available': False})

    # Converter para DataFrame para ordenação e formatação fácil
    df = pd.DataFrame(saldo_mensal.items(), columns=['Mes_Referencia_Key', 'Saldo_Parcelas'])
    df['Mes_Referencia_Key'] = pd.to_datetime(df['Mes_Referencia_Key'], format='%Y-%m')
    df = df.sort_values('Mes_Referencia_Key').reset_index(drop=True)
    
    # Formato de rótulo: Jan/2025
    df['Mes_Nome'] = df['Mes_Referencia_Key'].dt.strftime('%b/%Y').str.replace(r'(\w+)/', lambda x: x.group(1).capitalize() + '/', regex=True)
    
    # Extrair listas finais
    chart_labels = df['Mes_Nome'].tolist()
    
    # CORREÇÃO: Converte diretamente de Decimal para float. O .tolist() do pandas já deve fazer isso,
    # mas garantimos que a lista final é de floats, não strings, para evitar problemas no JS.
    chart_data_values = [float(s) for s in df['Saldo_Parcelas'].tolist()]


    # 4. Renderizar o template com os dados Chart.js
    context = {
        'chart_data_available': True,
        'chart_labels': chart_labels,
        'chart_data_values': chart_data_values
    }
    
    return render(request, 'dividas/saldo_chart.html', context)

# --- Outras Views (Mantenha o restante do arquivo views.py como estava) ---

def divida_list(request):
# ... (conteúdo da divida_list) ...
    dividas = Divida.objects.all().order_by('-data_compra')

    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    mes_param = request.GET.get('mes', '').strip() 
    ano_param = request.GET.get('ano', '').strip() 
    tipo_param = request.GET.get('tipo', '').strip()
    status_param = request.GET.get('status', '').strip()
    descricao_param = request.GET.get('descricao', '').strip()
    forma_param = request.GET.get('forma', '').strip()
    valor_parcela_param = request.GET.get('valor_parcela', '').strip()

    
    if valor_parcela_param:
        try:
            valor_num = Decimal(valor_parcela_param.replace('.', '').replace(',', '.'))
            dividas = dividas.filter(valor_parcela__gte=valor_num)
        except (ValueError, TypeError):
            pass
            
    filtered_list = []
    
    for d in list(dividas):

        # Filtros de texto: Descrição (contém)
        if descricao_param:
            if unidecode(d.descricao).lower().find(unidecode(descricao_param).lower()) == -1:
                continue

        # Filtro por tipo de despesa
        if tipo_param:
            if not d.tipo_despesa or unidecode(d.tipo_despesa).lower() != unidecode(tipo_param).lower():
                continue

        # Filtro por forma de pagamento
        if forma_param:
            if unidecode(d.forma_pagamento).lower().find(unidecode(forma_param).lower()) == -1:
                continue

        # Calcula dinamicamente o mês e o ano de referência
        primeira_parcela = d.parcelas.order_by('numero').first()
        data_ref = primeira_parcela.vencimento if primeira_parcela and primeira_parcela.vencimento else d.data_compra
        
        ano_venc, mes_ref = calcular_mes_referencia(data_ref)
        mes_nome = meses_pt.get(mes_ref, '')

        d.mes_nome = mes_nome
        d.ano_venc = ano_venc

        # Filtro de mês
        if mes_param:
            if unidecode(mes_nome).lower() != unidecode(mes_param).lower():
                continue

        # Filtro de ano
        if ano_param:
            try:
                ano_int = int(ano_param)
                if ano_venc != ano_int:
                    continue
            except ValueError:
                pass

        # Filtro de status
        if status_param:
            current_status = d.status
            if unidecode(status_param).lower() != unidecode(current_status).lower():
                continue

        filtered_list.append(d)

    # Calcula totais das dívidas em aberto (ciclo atual)
    all_dividas = Divida.objects.all()
    
    open_total_valor = Decimal('0.0')
    open_total_parcela = Decimal('0.0')
    
    for d in all_dividas:
        is_open = d.is_open if hasattr(d, 'is_open') else d.parcelas.filter(quitada=False).exists()
        if is_open:
            open_total_valor += d.valor_total
            open_total_parcela += d.valor_parcela

    # Calcula totais das dívidas filtradas
    filtered_total_valor = sum(d.valor_total for d in filtered_list)
    filtered_total_parcela = sum(d.valor_parcela for d in filtered_list)

    # Paginação
    paginator = Paginator(filtered_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Lista de anos e tipos de despesa disponíveis
    anos_set = set()
    for p in all_dividas:
        primeira = p.parcelas.order_by('numero').first()
        ref_date = primeira.vencimento if primeira and primeira.vencimento else p.data_compra
        
        ano_ref, _ = calcular_mes_referencia(ref_date)
        anos_set.add(ano_ref)
        
    anos_disponiveis = sorted(anos_set)
    tipos_disponiveis = sorted({d.tipo_despesa for d in all_dividas if d.tipo_despesa})

    # Prepara a query string
    params = request.GET.copy()
    if 'page' in params:
        params.pop('page')
    querystring = params.urlencode()

    return render(request, 'dividas/divida_list.html', {
        'dividas': page_obj,
        'total_valor': open_total_valor,
        'total_parcela': open_total_parcela,
        'filtered_total_valor': filtered_total_valor,
        'filtered_total_parcela': filtered_total_parcela,
        'anos_disponiveis': anos_disponiveis,
        'tipos_disponiveis': tipos_disponiveis,
        'selected_mes': mes_param,
        'selected_ano': ano_param,
        'selected_tipo': tipo_param,
        'selected_status': status_param,
        'selected_descricao': descricao_param,
        'selected_forma': forma_param,
        'selected_valor_parcela': valor_parcela_param,
        'querystring': querystring,
    })


def divida_create(request):
    """Cria uma nova dívida e gera suas parcelas automaticamente."""
    if request.method == 'POST':
        form = DividaForm(request.POST)
        if form.is_valid():
            divida = form.save()
            gerar_parcelas(divida)
            
            primeira_parcela = divida.parcelas.order_by('numero').first()
            if primeira_parcela and primeira_parcela.vencimento:
                venc = primeira_parcela.vencimento
                meses_pt = {
                    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
                    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
                }
                
                ano_ref, mes_ref = calcular_mes_referencia(venc)
                
                divida.mes = meses_pt.get(mes_ref, '')
                divida.ano = ano_ref
                divida.save(update_fields=['mes', 'ano'])
                
            return redirect('dividas:divida_list')
    else:
        form = DividaForm()
    return render(request, 'dividas/divida_form.html', {'form': form})


def divida_detalhe(request, pk):
    """Exibe os detalhes de uma dívida, listando todas as suas parcelas."""
    divida = get_object_or_404(Divida, pk=pk)
    parcelas = divida.parcelas.all().order_by('numero')
    return render(request, 'dividas/divida_detalhe.html', {'divida': divida, 'parcelas': parcelas})


def importar_excel_view(request):
    """
    Permite o upload de um arquivo Excel para importar dívidas em massa.
    """
    if request.method == "POST":
        arquivo = request.FILES.get('arquivo')
        if not arquivo:
            messages.error(request, "Selecione um arquivo Excel para importar.")
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                for chunk in arquivo.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            dividas = importar_dividas_de_excel(tmp_path)
            messages.success(request, f"{len(dividas)} dívidas importadas com sucesso!")
            return redirect('dividas:divida_list')
    return render(request, 'dividas/importar_excel.html')
