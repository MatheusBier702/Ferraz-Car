from functools import wraps
from django.contrib.auth.decorators import login_required
import json
import re
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .models import Cliente, Veiculo, OrdemServico, ItemServico

@login_required
@ensure_csrf_cookie
def dashboard(request):
    return render(request, 'oficina/dashboard.html')

def serialize(order):
    return {'pk': order.pk, 'id': str(order), 'clientId': order.cliente_id, 'vehicleId': order.veiculo_id,
        'owner': order.nome_cliente, 'phone': order.telefone_cliente, 'brand': order.marca,
        'model': order.modelo, 'vehicle': f'{order.marca} {order.modelo}', 'plate': order.placa,
        'year': order.ano, 'description': order.descricao, 'status': order.situacao,
        'date': timezone.localtime(order.criado_em).strftime('%d/%m/%Y'),
        'items': [{'description': i.descricao, 'cents': i.valor_centavos} for i in order.itens.all()]}

def text(data, key, maximum, required=True):
    value = data.get(key, '')
    if not isinstance(value, str): raise ValueError(f'Campo inválido: {key}.')
    value = value.strip()
    if (required and not value) or len(value) > maximum: raise ValueError(f'Confira o campo {key}.')
    return value

def payload(request):
    try: data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError): raise ValueError('Dados inválidos.')
    if not isinstance(data, dict): raise ValueError('Dados inválidos.')
    return data

def api_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Sua sessão terminou. Entre novamente.', 'login_url': '/login/'}, status=401)
        return view(request, *args, **kwargs)
    return wrapped

@api_login_required
@require_http_methods(['GET', 'POST'])
def services(request):
    if request.method == 'GET':
        today = timezone.localdate()
        orders = OrdemServico.objects.select_related('cliente', 'veiculo').prefetch_related('itens')
        return JsonResponse({'records': [serialize(o) for o in orders], 'clients': [{'pk': c.pk, 'name': c.nome, 'phone': c.telefone} for c in Cliente.objects.order_by('nome', 'pk')], 'vehicles': [{'pk': v.pk, 'clientId': v.proprietario_id, 'owner': v.proprietario.nome, 'brand': v.marca, 'model': v.modelo, 'plate': v.placa, 'year': v.ano} for v in Veiculo.objects.select_related('proprietario').order_by('placa')], 'stats': {
            'active': orders.exclude(situacao='Concluído').count(),
            'pending': orders.filter(situacao='Aguardando aprovação').count(),
            'completed': orders.filter(situacao='Concluído', criado_em__year=today.year, criado_em__month=today.month).count(),
            'vehicles': Veiculo.objects.count(), 'clients': Cliente.objects.count()}})
    try:
        data = payload(request)
        selected_client = None
        selected_vehicle = None
        if data.get('clientId') not in ('', None):
            if type(data['clientId']) is not int: raise ValueError('Cliente inválido.')
            selected_client = Cliente.objects.filter(pk=data['clientId']).first()
            if selected_client is None: raise ValueError('Cliente não encontrado.')
        if data.get('vehicleId') not in ('', None):
            if type(data['vehicleId']) is not int: raise ValueError('Veículo inválido.')
            selected_vehicle = Veiculo.objects.select_related('proprietario').filter(pk=data['vehicleId']).first()
            if selected_vehicle is None: raise ValueError('Veículo não encontrado.')
            if selected_client and selected_vehicle.proprietario_id != selected_client.pk:
                raise ValueError('O veículo não pertence ao cliente selecionado. Confira o cadastro.')
            selected_client = selected_vehicle.proprietario
            data = {**data, 'plate': selected_vehicle.placa, 'brand': selected_vehicle.marca,
                'model': selected_vehicle.modelo, 'year': selected_vehicle.ano}
        if selected_client:
            owner = selected_client.nome; phone = selected_client.telefone
        else:
            owner = text(data, 'owner', 100); phone = text(data, 'phone', 30, False)
        brand = text(data, 'brand', 100); model = text(data, 'model', 100)
        description = text(data, 'description', 1000)
        plate = re.sub(r'[\s-]', '', text(data, 'plate', 12)).upper()
        if not re.fullmatch(r'[A-Z]{3}(?:[0-9]{4}|[0-9][A-Z][0-9]{2})', plate):
            raise ValueError('Informe uma placa válida, como ABC1234 ou ABC1D23.')
        raw_year = data.get('year')
        if raw_year in ('', None): year = None
        else:
            if isinstance(raw_year, bool) or not re.fullmatch(r'[0-9]{4}', str(raw_year)): raise ValueError('Ano inválido.')
            year = int(raw_year)
            if not 1900 <= year <= 2100: raise ValueError('Ano inválido.')
        with transaction.atomic():
            vehicle = selected_vehicle or Veiculo.objects.select_related('proprietario').filter(placa=plate).first()
            if selected_client and vehicle and vehicle.proprietario_id != selected_client.pk:
                raise ValueError('Essa placa pertence a outro cliente. Atualize o proprietário em Veículos antes de criar o serviço.')
            if selected_client:
                client = selected_client
            elif vehicle and vehicle.proprietario.nome.casefold() == owner.casefold() and (not phone or vehicle.proprietario.telefone == phone):
                client = vehicle.proprietario
            else:
                # Não associa pessoas distintas apenas pelo nome quando não há telefone.
                client = Cliente.objects.filter(nome=owner, telefone=phone).first() if phone else None
                if client is None: client = Cliente.objects.create(nome=owner, telefone=phone)
            if vehicle is None: vehicle = Veiculo(placa=plate)
            vehicle.proprietario = client; vehicle.marca = brand; vehicle.modelo = model; vehicle.ano = year; vehicle.save()
            order = OrdemServico.objects.create(veiculo=vehicle, cliente=client, nome_cliente=owner,
                telefone_cliente=phone, marca=brand, modelo=model, placa=plate, ano=year, descricao=description)
            ItemServico.objects.create(ordem=order, descricao=description, valor_centavos=None)
        return JsonResponse({'record': serialize(order)}, status=201)
    except IntegrityError: return JsonResponse({'error': 'Essa placa já foi cadastrada. Reabra o formulário e selecione o veículo.'}, status=400)
    except ValueError as error: return JsonResponse({'error': str(error)}, status=400)

@api_login_required
@require_http_methods(['PATCH'])
def service_detail(request, pk):
    order = get_object_or_404(OrdemServico, pk=pk)
    try:
        data = payload(request)
        status = data.get('status')
        if status not in dict(OrdemServico.SITUACOES): raise ValueError('Situação inválida.')
        items = data.get('items')
        if not isinstance(items, list) or len(items) > 100: raise ValueError('Informe até 100 itens.')
        validated = []
        for item in items:
            if not isinstance(item, dict): raise ValueError('Item inválido.')
            description = text(item, 'description', 500)
            cents = item.get('cents')
            if cents is not None and (type(cents) is not int or not 0 <= cents <= 9999999900): raise ValueError('Valor inválido.')
            validated.append(ItemServico(ordem=order, descricao=description, valor_centavos=cents))
        if status == 'Concluído' and (not validated or any(i.valor_centavos is None for i in validated)):
            raise ValueError('Preencha os itens e valores antes de concluir.')
        with transaction.atomic():
            order.situacao = status; order.save(update_fields=['situacao'])
            order.itens.all().delete(); ItemServico.objects.bulk_create(validated)
        return JsonResponse({'record': serialize(order)})
    except ValueError as error: return JsonResponse({'error': str(error)}, status=400)

@api_login_required
@require_http_methods(['PATCH'])
def client_detail(request, pk):
    client = get_object_or_404(Cliente, pk=pk)
    try:
        data = payload(request)
        name = text(data, 'name', 100)
        phone = text(data, 'phone', 30, False)
        client.nome = name; client.telefone = phone
        client.save(update_fields=['nome', 'telefone'])
        return JsonResponse({'ok': True})
    except ValueError as error: return JsonResponse({'error': str(error)}, status=400)

@api_login_required
@require_http_methods(['PATCH'])
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Veiculo, pk=pk)
    try:
        data = payload(request)
        brand = text(data, 'brand', 100); model = text(data, 'model', 100)
        plate = re.sub(r'[\s-]', '', text(data, 'plate', 12)).upper()
        if not re.fullmatch(r'[A-Z]{3}(?:[0-9]{4}|[0-9][A-Z][0-9]{2})', plate): raise ValueError('Informe uma placa válida.')
        raw_year = data.get('year')
        year = None
        if raw_year not in ('', None):
            if isinstance(raw_year, bool) or not re.fullmatch(r'[0-9]{4}', str(raw_year)): raise ValueError('Ano inválido.')
            year = int(raw_year)
            if not 1900 <= year <= 2100: raise ValueError('Ano inválido.')
        client_id = data.get('clientId')
        if type(client_id) is not int: raise ValueError('Escolha um proprietário válido.')
        client = Cliente.objects.filter(pk=client_id).first()
        if client is None: raise ValueError('Proprietário não encontrado.')
        if Veiculo.objects.filter(placa=plate).exclude(pk=pk).exists(): raise ValueError('Essa placa já está cadastrada em outro veículo.')
        with transaction.atomic():
            vehicle.marca = brand; vehicle.modelo = model; vehicle.placa = plate; vehicle.ano = year; vehicle.proprietario = client
            vehicle.save()
        return JsonResponse({'ok': True})
    except IntegrityError: return JsonResponse({'error': 'Essa placa já está cadastrada em outro veículo.'}, status=400)
    except ValueError as error: return JsonResponse({'error': str(error)}, status=400)
