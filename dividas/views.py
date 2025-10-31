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
    Lista e filtra dívidas parceladas.

    Os filtros para mês, ano, tipo de despesa e status são representados por dropdowns no template.
    Os demais campos (descrição, forma de pagamento, valor da parcela) são tratados como
    filtros textuais. Para garantir que os filtros de mês/ano funcionem corretamente mesmo
    quando os campos ``mes`` e ``ano`` do modelo não estiverem preenchidos, esta view calcula
    dinamicamente as propriedades ``mes_nome`` e ``ano_venc`` para cada dívida com base
    na data de vencimento da primeira parcela (ou na ``data_compra`` caso não haja parcelas).

    Após aplicar todos os filtros, calcula os totais das dívidas em aberto (ciclo vigente) e os
    totais para o conjunto filtrado. O resultado é paginado em blocos de 25 registros.
    """
    # Carrega todas as dívidas ordenadas pela data de compra (mais recente primeiro)
    dividas = Divida.objects.all().order_by('-data_compra')

    # Mapeia números para nomes de mês em português
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    # Recupera parâmetros de filtro da query string
    mes_param = request.GET.get('mes', '').strip() # O filtro é um select simples, retorna uma string
    ano_param = request.GET.get('ano', '').strip() # O filtro é um select simples, retorna uma string
    tipo_param = request.GET.get('tipo', '').strip()
    status_param = request.GET.get('status', '').strip()
    descricao_param = request.GET.get('descricao', '').strip()
    forma_param = request.GET.get('forma', '').strip()
    valor_parcela_param = request.GET.get('valor_parcela', '').strip()

    # Aplica filtros usando o ORM do Django (mais eficiente)
    # Todos os filtros de texto (descricao, tipo_despesa, forma_pagamento) serão
    # aplicados na iteração para garantir a busca case-insensitive e accent-insensitive.
    # Apenas o filtro de valor da parcela é mantido no ORM por ser numérico.
    
    if valor_parcela_param:
        try:
            # Filtra por valor_parcela maior ou igual
            valor_num = float(valor_parcela_param.replace('.', '').replace(',', '.'))
            dividas = dividas.filter(valor_parcela__gte=valor_num)
        except ValueError:
            pass
            
    # Filtros de Mês e Ano (requerem a lógica de data da primeira parcela)
    # Como a lógica de data é complexa (depende da primeira parcela), mantemos a iteração
    # apenas para os filtros de mês/ano e status, mas aplicamos os demais no ORM.
    
    filtered_list = []
    # Converte o QuerySet para lista e itera APENAS sobre os resultados já filtrados pelo ORM
    # Aplica filtros de texto (descricao, tipo, forma) com unaccent e lower,
    # pois o ORM não suporta __unaccent sem a extensão do banco de dados.
    for d in list(dividas):
        """
        Aplica filtros de texto e calcula dinamicamente o mês (anterior ao vencimento) e o ano de
        referência para cada dívida. Não utiliza os campos ``mes`` e ``ano`` armazenados na base,
        garantindo que o campo mês reflita sempre o mês anterior ao próximo vencimento da dívida.
        """

        # Filtros de texto: Descrição (contém)
        if descricao_param:
            if unidecode(d.descricao).lower().find(unidecode(descricao_param).lower()) == -1:
                continue

        # Filtro por tipo de despesa (igualdade exata após normalização)
        if tipo_param:
            if not d.tipo_despesa or unidecode(d.tipo_despesa).lower() != unidecode(tipo_param).lower():
                continue

        # Filtro por forma de pagamento (substring)
        if forma_param:
            if unidecode(d.forma_pagamento).lower().find(unidecode(forma_param).lower()) == -1:
                continue

        # Calcula dinamicamente o mês e o ano de referência SEMPRE com base na
        # data de vencimento da primeira parcela (ou data_compra). O mês é o mês
        # anterior ao vencimento. Se o vencimento for em janeiro, o mês é dezembro
        # e o ano é decrementado.
        primeira_parcela = d.parcelas.order_by('numero').first()
        data_ref = primeira_parcela.vencimento if primeira_parcela and primeira_parcela.vencimento else d.data_compra
        mes_venc = data_ref.month
        if mes_venc == 1:
            # vencimento em janeiro -> mês anterior é dezembro do ano anterior
            mes_idx_prev = 12 - 1  # índice 11 (Dezembro) na lista meses_pt
            ano_prev = data_ref.year - 1
        else:
            # demais meses -> subtrai 1 mês
            mes_idx_prev = mes_venc - 2
            ano_prev = data_ref.year
        mes_nome = meses_pt.get(mes_idx_prev + 1, '')
        ano_venc = ano_prev

        # Atribui atributos dinâmicos para uso no template
        d.mes_nome = mes_nome
        d.ano_venc = ano_venc

        # Filtro de mês (comparação acento-insensível)
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

        # Filtro de status (Em aberto ou Quitada)
        if status_param:
            current_status = d.status  # usa propriedade ``status`` do modelo
            if unidecode(status_param).lower() != unidecode(current_status).lower():
                continue

        # Se passou por todos os filtros, adiciona à lista
        filtered_list.append(d)

    # Calcula totais das dívidas em aberto (ciclo atual) em todo o conjunto de dívidas
    # Usamos o QuerySet original (dividas.all()) para calcular os totais em aberto
    all_dividas = Divida.objects.all()
    open_total_valor = 0
    open_total_parcela = 0
    for d in all_dividas:
        # Assumindo que 'is_open' é uma propriedade do modelo/manager
        is_open = d.is_open if hasattr(d, 'is_open') else d.parcelas.filter(quitada=False).exists()
        if is_open:
            open_total_valor += float(d.valor_total)
            open_total_parcela += float(d.valor_parcela)

    # Calcula totais das dívidas filtradas (independente de estar em aberto ou não)
    filtered_total_valor = sum(float(d.valor_total) for d in filtered_list)
    filtered_total_parcela = sum(float(d.valor_parcela) for d in filtered_list)

    # Paginação
    paginator = Paginator(filtered_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Lista de anos e tipos de despesa disponíveis para dropdowns (inclui todos do banco)
    # Calcula anos disponíveis com base no mês anterior ao vencimento da primeira parcela
    anos_set = set()
    for p in all_dividas:
        primeira = p.parcelas.order_by('numero').first()
        ref_date = primeira.vencimento if primeira and primeira.vencimento else p.data_compra
        # Se o vencimento é janeiro, o ano de referência é do ano anterior
        if ref_date.month == 1:
            anos_set.add(ref_date.year - 1)
        else:
            anos_set.add(ref_date.year)
    anos_disponiveis = sorted(anos_set)
    tipos_disponiveis = sorted({d.tipo_despesa for d in all_dividas if d.tipo_despesa})

    # Prepara a query string sem o parâmetro "page" para manter filtros na navegação
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
        # Passa valores selecionados para o template relembrar filtros
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
            # Após gerar as parcelas, atribui os campos de mês e ano com base na data de vencimento da primeira parcela.
            # O mês deve ser o mês anterior ao vencimento. Se o vencimento for janeiro, o mês passa a ser dezembro e o ano é decrementado.
            primeira_parcela = divida.parcelas.order_by('numero').first()
            if primeira_parcela and primeira_parcela.vencimento:
                venc = primeira_parcela.vencimento
                meses_pt = [
                    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
                ]
                mes_venc = venc.month
                if mes_venc == 1:
                    mes_anterior_idx = 12 - 1  # Dezembro
                    ano_anterior = venc.year - 1
                else:
                    mes_anterior_idx = mes_venc - 2
                    ano_anterior = venc.year
                if 0 <= mes_anterior_idx < len(meses_pt):
                    divida.mes = meses_pt[mes_anterior_idx]
                divida.ano = ano_anterior
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