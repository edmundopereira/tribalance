from django.shortcuts import render, redirect, get_object_or_404
from .models import Divida, Parcela
from .forms import DividaForm
from .services import gerar_parcelas

def divida_list(request):
    dividas = Divida.objects.all().order_by('-data_compra')
    return render(request, 'dividas/divida_list.html', {'dividas': dividas})

def divida_create(request):
    if request.method == 'POST':
        form = DividaForm(request.POST)
        if form.is_valid():
            divida = form.save()
            gerar_parcelas(divida)
            return redirect('dividas:divida_list')
    else:
        form = DividaForm()
    return render(request, 'dividas/divida_form.html', {'form': form})

def divida_detalhe(request, pk):
    divida = get_object_or_404(Divida, pk=pk)
    parcelas = divida.parcelas.all().order_by('numero')
    return render(request, 'dividas/divida_detalhe.html', {'divida': divida, 'parcelas': parcelas})

from django.shortcuts import render, redirect
from django.contrib import messages
from .importer import importar_dividas_de_excel

def importar_excel_view(request):
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

