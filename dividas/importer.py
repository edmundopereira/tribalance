import re
import pandas as pd
import unicodedata
from datetime import datetime
from .models import Divida, Parcela
from .services import gerar_parcelas


def normalizar_texto(txt):
    """Remove acentos, deixa minúsculo e elimina espaços extras"""
    if not isinstance(txt, str):
        txt = str(txt)
    txt = txt.strip().lower()
    txt = unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').decode('utf-8')
    return txt


def parse_valor(valor_cell):
    """
    Converte o conteúdo da coluna de valor para um float.

    Se o valor vier como string, remove símbolos de moeda, espaços e separadores de milhar,
    substituindo vírgulas por pontos. Se vier como número, aplica float diretamente.
    """
    if isinstance(valor_cell, str):
        s = valor_cell.replace('R$', '').replace('R$ ', '').strip()
        # remove separador de milhar (.) e troca vírgula por ponto
        s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return 0.0
    else:
        try:
            return float(valor_cell)
        except Exception:
            return 0.0


def importar_dividas_de_excel(caminho_arquivo):
    """
    Importa dívidas parceladas a partir de um arquivo Excel.

    - Remove quaisquer dívidas existentes antes de importar as novas.
    - Detecta automaticamente o número total de parcelas e quantas já foram pagas a partir de campos
      como "Parcela 6/7" ou "12x".
    - Converte valores com formatação monetária brasileira para floats.
    - Cria as parcelas e marca as já pagas para que o campo "restantes" reflita corretamente
      a diferença entre o total e as pagas.
    """
    # 1. Limpar dados anteriores
    Parcela.objects.all().delete()
    Divida.objects.all().delete()

    # 2. Ler o Excel e normalizar colunas
    df = pd.read_excel(caminho_arquivo)
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace("ç", "c")
        .str.replace("ã", "a")
        .str.replace("á", "a")
    )

    dividas_criadas = []

    for _, row in df.iterrows():
        descricao = str(row.get("lancamento", "")).strip()
        # Lê o valor informado na planilha; trata como valor de cada parcela
        valor_cell = row.get("valor", 0)
        valor_unitario = parse_valor(valor_cell)
        # Armazena o tipo de despesa exatamente como aparece na planilha (após remover espaços extras)
        tipo_despesa_raw = str(row.get("tipo_despesa", "")).strip()
        forma = normalizar_texto(row.get("forma_pagamento", ""))
        parcelas_txt = normalizar_texto(row.get("parcelas", ""))
        data = pd.to_datetime(row.get("data", datetime.today()), errors="coerce").date()

        # Ignorar linhas sem descrição ou com valor da parcela igual a zero
        if not descricao or valor_unitario == 0:
            continue

        # Detectar total de parcelas e parcelas já pagas
        # Detectar total de parcelas e, quando aplicável, quantas já foram pagas.
        total_parcelas = 1
        parcelas_pagas = None
        match_total = re.search(r'(\d+)[/xX](\d+)', parcelas_txt)  # ex: "Parcela 6/7"
        match_unico = re.search(r'(\d+)\s*[xX]', parcelas_txt)     # ex: "12x"
        if match_total:
            # "6/7" significa que 6 parcelas já se passaram, 7 no total
            parcelas_pagas = int(match_total.group(1))
            total_parcelas = int(match_total.group(2))
        elif match_unico:
            # "12x" significa 12 parcelas no total, nenhuma explicitamente paga
            total_parcelas = int(match_unico.group(1))
            parcelas_pagas = 0
        elif "avista" in parcelas_txt or "a vista" in parcelas_txt or "à vista" in parcelas_txt:
            # compra à vista: uma parcela única e já quitada
            total_parcelas = 1
            parcelas_pagas = 1
        elif not parcelas_txt:
            # campo vazio: considerar como uma única parcela já paga
            total_parcelas = 1
            parcelas_pagas = 1

        # Determinar se é dívida parcelada (cartão ou crédito)
        condicao_cartao = any(palavra in forma for palavra in ["cartao", "credito"])
        if not condicao_cartao:
            continue

        # Calcula o valor total como valor da parcela * número de parcelas
        valor_total = valor_unitario * total_parcelas

        # Criar a dívida
        divida = Divida.objects.create(
            descricao=descricao or "Lançamento sem descrição",
            categoria="compra",
            forma_pagamento="credito",
            data_compra=data,
            valor_total=valor_total,
            parcelas_totais=total_parcelas,
            tipo_despesa=tipo_despesa_raw,
            observacao=f"{row.get('forma_pagamento', '')} / {row.get('parcelas', '')}",
            quitada=False,
        )
        # Gerar todas as parcelas
        gerar_parcelas(divida)
        # Se houver parcelas já pagas, marcar as correspondentes como quitadas
        if parcelas_pagas is not None and parcelas_pagas > 0:
            for parcela in divida.parcelas.order_by('numero')[:parcelas_pagas]:
                parcela.paga = True
                # Define a data de pagamento como a data de vencimento da parcela ou data atual
                parcela.data_pagamento = parcela.vencimento
                parcela.save()
            # Se todas as parcelas estiverem pagas, marcar a dívida como quitada
            if parcelas_pagas >= total_parcelas:
                divida.quitada = True
                divida.save(update_fields=["quitada"])

        dividas_criadas.append(divida)

    return dividas_criadas