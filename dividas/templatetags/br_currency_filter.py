"""
Template filter para formatar valores monetários em reais (R$) com
separador de milhares e vírgula como separador decimal.

Para usar este filtro, adicione a pasta `templatetags` dentro da sua
aplicação e mova este arquivo para lá. Em seguida, carregue o filtro
no template com `{% load br_currency_filter %}` e aplique
`{{ valor|br_currency }}` para formatar números.

Exemplo de uso no template:

```
{% load br_currency_filter %}
R$ {{ divida.valor_total|br_currency }}
```

Obs.: O formato brasileiro utiliza ponto como separador de milhar e
vírgula como separador decimal, por exemplo "1.234,56".
"""

from django import template

register = template.Library()

@register.filter(name='br_currency')
def br_currency(value):
    """Formata um número como moeda brasileira (R$) com duas casas decimais.

    Args:
        value (float or int or str): valor numérico a ser formatado.

    Returns:
        str: valor formatado como "R$ 1.234,56".
    """
    if value is None or value == '':
        return ''
    try:
        number = float(value)
    except (ValueError, TypeError):
        return value
    # Formata com duas casas decimais e separador de milhar
    formatted = '{:,.2f}'.format(number)
    # Substitui vírgulas e pontos para o formato brasileiro
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {formatted}'