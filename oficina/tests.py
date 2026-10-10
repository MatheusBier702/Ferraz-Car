import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Cliente, Veiculo, OrdemServico, ItemServico

class ServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test-user', password='test-password-123')
        self.client.force_login(self.user)

    def new_client(self):
        client = Client()
        client.force_login(self.user)
        return client

    def create(self, **changes):
        data = dict(owner='Ana', phone='11999999999', brand='Honda', model='Fit', plate='ABC1D23', year='2004', description='Revisão')
        data.update(changes)
        return self.client.post('/api/services/', data=json.dumps(data), content_type='application/json')

    def test_persistence_and_reuse(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        record = response.json()['record']
        self.assertEqual(self.new_client().get('/api/services/').json()['records'][0]['pk'], record['pk'])
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(Veiculo.objects.count(), 1)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(OrdemServico.objects.count(), 2)

    def test_owner_change_keeps_history(self):
        self.create()
        self.create(owner='Carlos', phone='11888888888', brand='Honda', model='Fit novo')
        old = OrdemServico.objects.order_by('pk').first()
        self.assertEqual(old.nome_cliente, 'Ana')
        self.assertEqual(old.modelo, 'Fit')
        self.assertEqual(Veiculo.objects.get().proprietario.nome, 'Carlos')

    def test_save_items_and_completion(self):
        pk = self.create().json()['record']['pk']
        items = [dict(description='Scanner', cents=20000), dict(description='Peça', cents=8500), dict(description='Mão de obra', cents=30000)]
        response = self.client.patch(f'/api/services/{pk}/', data=json.dumps(dict(status='Concluído', items=items)), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sum(i['cents'] for i in self.new_client().get('/api/services/').json()['records'][0]['items']), 58500)
        self.assertEqual(self.client.get('/api/services/').json()['stats']['completed'], 1)

    def test_invalid_update_preserves_items(self):
        pk = self.create().json()['record']['pk']
        for cents in [-1, 0.5, True, 10000000000]:
            response = self.client.patch(f'/api/services/{pk}/', data=json.dumps(dict(status='Em andamento', items=[dict(description='Peça', cents=cents)])), content_type='application/json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(ItemServico.objects.get().descricao, 'Revisão')
        response = self.client.patch(f'/api/services/{pk}/', data=json.dumps(dict(status='Concluído', items=[dict(description='Peça', cents=None)])), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_validation_without_partial_registration(self):
        for data in [dict(plate='errada'), dict(year='2004.5'), dict(owner=''), dict(description='')]:
            self.assertEqual(self.create(**data).status_code, 400)
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertEqual(Veiculo.objects.count(), 0)

    def test_csrf_and_frontend_hooks(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.get('/')
        self.assertContains(response, 'id="save-service"')
        self.assertContains(response, 'id="print-order"')
        self.assertEqual(client.post('/api/services/', data='{}', content_type='application/json').status_code, 403)
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/api/services/', data='{}', content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 400)

class LoginTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test-user', password='test-password-123')

    def test_anonymous_cannot_access_panel_or_data(self):
        self.assertRedirects(self.client.get('/'), '/login/?next=/')
        self.assertEqual(self.client.get('/api/services/').status_code, 401)
        self.assertEqual(self.client.post('/api/services/', data='{}', content_type='application/json').status_code, 401)
        self.assertEqual(self.client.patch('/api/services/1/', data='{}', content_type='application/json').status_code, 401)

    def test_login_logout(self):
        response = self.client.post('/login/', {'username': 'test-user', 'password': 'wrong'})
        self.assertContains(response, 'Usuário ou senha incorretos')
        self.assertNotIn('_auth_user_id', self.client.session)
        response = self.client.post('/login/', {'username': 'test-user', 'password': 'test-password-123'})
        self.assertRedirects(response, '/')
        self.assertEqual(self.client.get('/api/services/').status_code, 200)
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.assertRedirects(self.client.post('/logout/'), '/login/')
        self.assertEqual(self.client.get('/api/services/').status_code, 401)

    def test_external_redirect_rejected(self):
        response = self.client.post('/login/', {'username': 'test-user', 'password': 'test-password-123', 'next': 'https://example.com/'})
        self.assertRedirects(response, '/')

    def test_csrf_protects_login_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/login/', {}).status_code, 403)
        client.get('/login/')
        token = client.cookies['csrftoken'].value
        self.assertRedirects(client.post('/login/', {'username': 'test-user', 'password': 'test-password-123'}, HTTP_X_CSRFTOKEN=token), '/')
        self.assertEqual(client.post('/logout/').status_code, 403)
        token = client.cookies['csrftoken'].value
        self.assertRedirects(client.post('/logout/', HTTP_X_CSRFTOKEN=token), '/login/')

class RegistryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='registry-user', password='test-password-123')
        self.client.force_login(self.user)
        self.owner = Cliente.objects.create(nome='Ana', telefone='111')
        self.other = Cliente.objects.create(nome='Carlos', telefone='222')
        self.vehicle = Veiculo.objects.create(proprietario=self.owner, placa='ABC1D23', marca='Honda', modelo='Fit', ano=2004)
        self.order = OrdemServico.objects.create(veiculo=self.vehicle, cliente=self.owner, nome_cliente='Ana', telefone_cliente='111', marca='Honda', modelo='Fit', placa='ABC1D23', ano=2004, descricao='Revisão')

    def patch(self, url, data):
        return self.client.patch(url, data=json.dumps(data), content_type='application/json')

    def test_edit_client_preserves_order(self):
        response = self.patch(f'/api/clients/{self.owner.pk}/', {'name': 'Ana Maria', 'phone': '333'})
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(self.owner.nome, 'Ana Maria')
        self.assertEqual(self.owner.telefone, '333')
        self.assertEqual(self.order.nome_cliente, 'Ana')
        self.assertEqual(self.order.telefone_cliente, '111')
        listing = self.client.get('/api/services/').json()
        self.assertEqual(next(c for c in listing['clients'] if c['pk'] == self.owner.pk)['name'], 'Ana Maria')
        self.assertEqual(listing['records'][0]['owner'], 'Ana')

    def test_edit_vehicle_and_owner_preserves_history(self):
        data = dict(plate='xyz-1234', brand='Fiat', model='Uno', year='2010', clientId=self.other.pk)
        self.assertEqual(self.patch(f'/api/vehicles/{self.vehicle.pk}/', data).status_code, 200)
        self.vehicle.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(self.vehicle.placa, 'XYZ1234')
        self.assertEqual(self.vehicle.modelo, 'Uno')
        self.assertEqual(self.vehicle.proprietario_id, self.other.pk)
        self.assertEqual(self.order.placa, 'ABC1D23')
        self.assertEqual(self.order.modelo, 'Fit')
        self.assertEqual(self.order.cliente_id, self.owner.pk)
        listing = self.client.get('/api/services/').json()
        self.assertEqual(listing['vehicles'][0]['owner'], 'Carlos')

    def test_invalid_edit_is_atomic(self):
        Veiculo.objects.create(proprietario=self.other, placa='XYZ1234', marca='Fiat', modelo='Uno')
        base = dict(plate='ABC1D23', brand='Honda', model='Fit', year=2004, clientId=self.owner.pk)
        for changes in [dict(plate='XYZ1234'), dict(plate='erro'), dict(year='2004.5'), dict(clientId=-1), dict(brand='')]:
            self.assertEqual(self.patch(f'/api/vehicles/{self.vehicle.pk}/', base | changes).status_code, 400)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.placa, 'ABC1D23')
        self.assertEqual(self.patch(f'/api/clients/{self.owner.pk}/', {'name': '', 'phone': 'new'}).status_code, 400)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.telefone, '111')

    def test_edits_require_login_and_csrf(self):
        client = Client()
        for url in [f'/api/clients/{self.owner.pk}/', f'/api/vehicles/{self.vehicle.pk}/']:
            self.assertEqual(client.patch(url, data='{}', content_type='application/json').status_code, 401)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.patch(f'/api/clients/{self.owner.pk}/', data='{}', content_type='application/json').status_code, 403)
        client.get('/')
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.patch(f'/api/clients/{self.owner.pk}/', data=json.dumps(dict(name='Ana Nova', phone='444')), content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(self.patch('/api/clients/999999/', dict(name='Pessoa', phone='')).status_code, 404)
