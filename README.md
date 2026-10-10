# Ferraz Car

Painel de oficina feito com Django, HTML, CSS e JavaScript.

## Rodar no Windows

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abra http://127.0.0.1:8000/ no navegador.

## Estrutura

- `config/`: configurações e rotas do projeto.
- `oficina/`: aplicativo da oficina.
- `oficina/templates/oficina/dashboard.html`: página do painel.
- `oficina/static/oficina/style.css`: estilos com paleta dourada.
- `oficina/static/oficina/logo-ferraz-car.png`: logo fornecida.
- `oficina/static/oficina/app.js`: navegação, filtros e formulários da prévia.

## Estado atual

Interface responsiva com dados demonstrativos. Criar serviço adiciona um registro somente à memória do navegador; recarregar remove o registro. Clientes e veículos mostram exemplos. A impressão gera uma ordem demonstrativa, sem emissão fiscal. Ainda não há modelos de negócio, autenticação do painel ou persistência dos cadastros.

Próxima etapa: criar os modelos Cliente, Veículo, OrdemServico e ItemServico, conectar os formulários e proteger o painel com login.
