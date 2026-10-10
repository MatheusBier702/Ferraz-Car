from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=30, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nome

class Veiculo(models.Model):
    proprietario = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='veiculos')
    placa = models.CharField(max_length=7, unique=True)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)
    def __str__(self): return f'{self.placa} - {self.marca} {self.modelo}'

class OrdemServico(models.Model):
    SITUACOES = [(s, s) for s in ['Em andamento', 'Aguardando aprovação', 'Concluído']]
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name='ordens')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ordens')
    nome_cliente = models.CharField(max_length=100)
    telefone_cliente = models.CharField(max_length=30, blank=True)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    placa = models.CharField(max_length=7)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)
    descricao = models.TextField(max_length=1000)
    situacao = models.CharField(max_length=30, choices=SITUACOES, default='Em andamento')
    criado_em = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-criado_em', '-pk']
    def __str__(self): return f'OS-{self.pk:04d}'

class ItemServico(models.Model):
    ordem = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='itens')
    descricao = models.CharField(max_length=500)
    valor_centavos = models.PositiveBigIntegerField(null=True, blank=True)
