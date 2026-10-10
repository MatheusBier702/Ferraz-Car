# Ferraz Car

Sistema de oficina com Django e SQLite.

## Rodar localmente

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abra http://127.0.0.1:8000/.

## Funcionalidades

Criar ordens cadastra cliente e veículo; a placa identifica o veículo. Nome e telefone são usados para localizar clientes existentes (nome sozinho não une clientes de carros diferentes). Cada ordem guarda os dados do atendimento, preservando histórico de antigos proprietários. Serviços e peças guardam valores em centavos. Ordens sem valores podem ser salvas em andamento; concluir e imprimir exige valores preenchidos. Cliente ou veículo abre seu histórico. Impressão em A4 com assinatura de cliente e oficina; não há emissão fiscal.

O banco está em `db.sqlite3`. Faça cópias desse arquivo com o servidor parado para backup. Os dados não ficam no navegador. Os exemplos visuais anteriores não foram inseridos no banco.

## Testar

```powershell
.\.venv\Scripts\python.exe manage.py test oficina
```

## Edição dos cadastros

Nas listas Clientes e Veículos, use Editar para atualizar os dados atuais. Veículos permitem alterar placa, marca, modelo, ano e proprietário. Placas duplicadas são rejeitadas. As ordens anteriores preservam os dados originais do atendimento; os cadastros atuais são mostrados separadamente do histórico.

## Próximas etapas

Rotina de backup e seleção de cadastros existentes ao criar atendimentos. O painel e a API exigem login; sair encerra a sessão por POST com proteção CSRF. A conta inicial Ferraz foi cadastrada no banco local. Antes de disponibilizar na internet, configurar a implantação de produção. SQLite também funciona em servidores com disco persistente; PostgreSQL é uma opção para crescimento.
