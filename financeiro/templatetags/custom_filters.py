from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def br_format(value):
    """
    Formata um valor numérico do padrão americano (ponto decimal) para o
    padrão brasileiro (vírgula decimal) após o uso do floatformat.
    Ex: '123.45' -> '123,45'
    """
    if value is None:
        return '0,00'
    
    # O valor já deve ser uma string após o floatformat.
    # Apenas substitui o ponto pela vírgula.
    return value.replace('.', ',')

@register.filter
def br_decimal_format(value, arg=2):
    """
    Formata um valor Decimal ou float para o padrão brasileiro com
    separador de milhar e vírgula decimal, garantindo o número de casas decimais.
    """
    if value is None:
        return '0,00'

    try:
        # Garante que o valor é um float ou Decimal
        value = float(value)
    except:
        return '0,00'

    # Formata com o locale brasileiro (se configurado) ou usa o formato padrão
    # e depois aplica a lógica de substituição.
    # O locale.format_string é mais robusto, mas requer o locale configurado.
    # Como alternativa, vamos usar a formatação de string do Python e o filtro br_format.
    
    # 1. Formata para string com o número de casas decimais
    format_string = f"%.{arg}f"
    formatted_value = format_string % value
    
    # 2. Substitui o ponto decimal por vírgula
    return formatted_value.replace('.', ',')
