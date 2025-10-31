from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages

from .models import Divida, Parcela
from .forms import DividaForm
from .services import gerar_parcelas
from unidecode import unidecode

from .importer import importar_dividas_de_excel


def divida_list(request):
    """
    Exibe a listagem de dívidas parceladas com filtros semelhantes à tela de lançamentos.

    Esta view suporta filtros por mês, ano, tipo de despesa e status via drop-down, bem como
    filtros textuais por descrição, forma de pagamento e valor da parcela. O cálculo dos
    totais de dívidas em aberto e dos totais filtrados é feito no backend, permitindo
    atualização dinâmica no template.
    """
    # Ordena todas as dívidas pela data de compra (mais recentes primeiro)
    queryset = Divida.objects.all().order_by('-data_compra')

    # Captura os parâmetros de filtro da query string. Campos vazios significam "Todos".
    mes_param = request.GET.get('mes', '').strip()
    ano_param = request.GET.get('ano', '').strip()
    tipo_param = request.GET.get('tipo', '').strip()
    status_param = request.GET.get('status', '').strip()
    descricao_param = request.GET.get('descricao', '').strip()
    forma_param = request.GET.get('forma', '').strip()
    valor_parcela_param = request.GET.get('valor_parcela', '').strip()

    # Se o filtro de valor da parcela estiver presente e for numérico, aplica via ORM.
    if valor_parcela_param:
        try:
            valor_num = float(valor_parcela_param.replace('.', '').replace(',', '.'))
            # valor_parcela é uma propriedade calculada (Decimal); usamos filtros via anotação
            # ou filtramos posteriormente na lista. Aqui mantemos filtragem posterior.
        except ValueError:
            valor_num = None
    else:
        valor_num = None

    # Lista para armazenar resultados após aplicar filtros. Convertemos o queryset em lista
    # para permitir iteração e cálculo de mes/ano dinâmicos.
    filtered_list = []

    # Mapeamento de número do mês para o nome em português.
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    # Itéra sobre todas as dívidas do queryset (sem filtros de texto por enquanto)
    for d in queryset:
        # Calcula dinamicamente o mês e o ano de referência se não estiverem preenchidos
        if d.mes:
            mes_nome = d.mes
        else:
            primeira_parcela = d.parcelas.order_by('numero').first()
            data_ref = (primeira_parcela.vencimento if primeira_parcela and primeira_parcela.vencimento
                        else d.data_compra)
            mes_nome = meses_pt.get(data_ref.month, '')
        if d.ano:
            ano_venc = d.ano
        else:
            primeira_parcela = d.parcelas.order_by('numero').first()
            data_ref = (primeira_parcela.vencimento if primeira_parcela and primeira_parcela.vencimento
                        else d.data_compra)
            ano_venc = data_ref.year
        # Atribui estes atributos no objeto para uso no template
        d.mes_nome = mes_nome
        d.ano_venc = ano_venc

        # Aplica filtro de valor da parcela (>=) se definido
        if valor_num is not None and float(d.valor_parcela) < valor_num:
            continue

        # Filtros textuais: Descrição contém
        if descricao_param:
            if unidecode(d.descricao).lower().find(unidecode(descricao_param).lower()) == -1:
                continue
        # Filtro por forma de pagamento (substring)
        if forma_param:
            if unidecode(d.forma_pagamento).lower().find(unidecode(forma_param).lower()) == -1:
                continue
        # Filtro por tipo de despesa (igualdade exata após normalizar)
        if tipo_param:
            if not d.tipo_despesa or unidecode(d.tipo_despesa).lower() != unidecode(tipo_param).lower():
                continue
        # Filtro por status (Em aberto/Quitada)
        if status_param:
            current_status = d.status  # usa propriedade status do modelo
            if unidecode(status_param).lower() != unidecode(current_status).lower():
                continue
        # Filtro por mês (nome do mês em português)
        if mes_param:
            if unidecode(mes_param).lower() != unidecode(mes_nome).lower():
                continue
        # Filtro por ano
        if ano_param:
            try:
                ano_int = int(ano_param)
                if ano_venc != ano_int:
                    continue
            except ValueError:
                # Se ano_param não for numérico, ignora o filtro
                continue
        # Se passou em todos os filtros, adiciona à lista final
        filtered_list.append(d)

    # Calcula totais de dívidas em aberto (ciclo vigente) para todas as dívidas
    open_total_valor = 0.0
    open_total_parcela = 0.0
    for d in Divida.objects.all():
        if d.status == 'Em aberto':
            open_total_valor += float(d.valor_total)
            open_total_parcela += float(d.valor_parcela)

    # Calcula totais filtrados (independente de estar em aberto)
    filtered_total_valor = sum(float(d.valor_total) for d in filtered_list)
    filtered_total_parcela = sum(float(d.valor_parcela) for d in filtered_list)

    # Paginação: 25 itens por página
    paginator = Paginator(filtered_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Lista de anos disponíveis a partir das dívidas (dinâmica)
    anos_set = set()
    for d in Divida.objects.all():
        if d.ano:
            anos_set.add(d.ano)
        else:
            # calcula ano baseado na primeira parcela ou data_compra
            p = d.parcelas.order_by('numero').first()
            data_ref = (p.vencimento if p and p.vencimento else d.data_compra)
            anos_set.add(data_ref.year)
    anos_disponiveis = sorted(anos_set)

    # Lista de tipos de despesa disponíveis
    tipos_disponiveis = sorted({d.tipo_despesa for d in Divida.objects.all() if d.tipo_despesa})

    # Passa a querystring para links de paginação (sem o parâmetro de page)
    params = request.GET.copy()
    if 'page' in params:
        params.pop('page')
    querystring = params.urlencode()

    context = {
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
    }
    return render(request, 'dividas/divida_list.html', context)


def divida_create(request):
    """Cria uma nova dívida e gera suas parcelas automaticamente."""
    if request.method == 'POST':
        form = DividaForm(request.POST)
        if form.is_valid():
            divida = form.save()
            gerar_parcelas(divida)
            # Após gerar as parcelas, atribuir os campos de mês e ano com base na data de vencimento da primeira parcela
            primeira_parcela = divida.parcelas.order_by('numero').first()
            if primeira_parcela and primeira_parcela.vencimento:
                meses_pt = [
                    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
                ]
                month_idx = primeira_parcela.vencimento.month - 1
                if 0 <= month_idx < len(meses_pt):
                    divida.mes = meses_pt[month_idx]
                divida.ano = primeira_parcela.vencimento.year
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
    Permite o upload de um arquivo Excel para importar dívidas em massa. Ao importar,
    remove quaisquer dívidas existentes e cria novas de acordo com o conteúdo do arquivo.
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