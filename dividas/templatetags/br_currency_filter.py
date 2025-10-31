from django import template
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def br_currency(value):
    """
    Formata um valor numérico (float, Decimal ou int) para o formato de moeda brasileira (R$ X.XXX,XX).
    """
    if value is None or value == '':
        return 'R$ 0,00'
    
    # Tenta definir o locale para português do Brasil
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        # Tenta uma alternativa para sistemas Windows
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except locale.Error:
            # Fallback manual se o locale não puder ser definido
            if isinstance(value, str):
                try:
                    value = Decimal(value)
                except:
                    return 'R$ 0,00'
            
            if not isinstance(value, (Decimal, float, int)):
                return 'R$ 0,00'

            # Formatação manual
            s = f"{value:,.2f}".replace('.', 'TEMP').replace(',', '.').replace('TEMP', ',')
            return f"R$ {s}"

    # Se o locale foi definido, usa formatação nativa
    if isinstance(value, str):
        try:
            value = Decimal(value)
        except:
            return 'R$ 0,00'
            
    return locale.currency(value, grouping=True, symbol=True)
