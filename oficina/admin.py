from django.contrib import admin
from .models import Cliente, Veiculo, OrdemServico, ItemServico
class ItemInline(admin.TabularInline):
    model = ItemServico
    extra = 0
@admin.register(OrdemServico)
class OrdemAdmin(admin.ModelAdmin):
    list_display = ['id', 'placa', 'nome_cliente', 'situacao', 'criado_em']
    search_fields = ['placa', 'nome_cliente']
    list_filter = ['situacao']
    inlines = [ItemInline]
admin.site.register(Cliente)
admin.site.register(Veiculo)
