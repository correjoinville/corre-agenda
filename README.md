# Corre Agenda

Calendário público de corridas de rua com painel administrativo. O projeto usa Flask, SQLite e HTML/CSS puro; não exige React, Node.js ou outro framework de front-end.

## Estrutura

```text
corre-agenda/
├── app.py                    # Aplicação, rotas, banco e regras
├── database.db              # Criado pelo comando de inicialização
├── requirements.txt         # Dependências para executar
├── requirements-dev.txt     # Dependências adicionais para testes
├── render.yaml              # Configuração para publicação no Render
├── .env.example             # Modelo das variáveis de ambiente
├── static/
│   ├── css/style.css         # Identidade visual e responsividade
│   └── js/app.js             # Confirmação antes de excluir
├── templates/
│   ├── base.html             # Cabeçalho e rodapé
│   ├── index.html            # Página pública
│   ├── login.html            # Login
│   ├── admin.html            # Lista administrativa
│   ├── event_form.html       # Cadastro e edição
│   └── _flashes.html         # Mensagens do sistema
└── tests/test_app.py         # Testes automatizados
```

## Executar no Windows

### 1. Instale o Python

Baixe o Python 3.11 ou mais recente em <https://www.python.org/downloads/>. Durante a instalação, marque **Add Python to PATH**.

### 2. Abra o terminal na pasta do projeto

No Explorador de Arquivos, abra a pasta, clique na barra de endereço, digite `powershell` e pressione Enter.

### 3. Crie e ative o ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação, execute uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4. Instale as dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure as variáveis

Gere uma chave secreta:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Na mesma janela do PowerShell, configure os valores. Troque os exemplos pela chave gerada e por uma senha forte:

```powershell
$env:SECRET_KEY="COLE-A-CHAVE-GERADA-AQUI"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="SUA-SENHA-FORTE-AQUI"
```

Essas variáveis valem para a janela atual. Para não digitá-las sempre, pesquise no Windows por **Editar as variáveis de ambiente da sua conta** e cadastre as três variáveis por lá.

### 6. Crie o banco de dados

```powershell
flask --app app init-db
```

Esse comando cria `database.db`, o usuário administrador e quatro eventos fictícios. Para começar sem exemplos, use `flask --app app init-db --sem-exemplos`.

### 7. Execute o servidor

Para desenvolvimento:

```powershell
flask --app app run --debug
```

Para uso normal na sua rede local:

```powershell
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

- Site público (Flask): <http://127.0.0.1:5000>
- Administração (Flask): <http://127.0.0.1:5000/admin>
- Com Waitress, troque a porta por `8000`.

## Testes

```powershell
pip install -r requirements-dev.txt
pytest -q
```

Os testes cobrem login/logout, proteção da administração, cadastro, edição, exclusão, agrupamento mensal, rascunhos, limite de 15 dias e validação de URLs.

## Onde modificar

- **Cores, espaçamento e aparência:** `static/css/style.css`, começando pelas variáveis em `:root`.
- **Página pública e cards:** `templates/index.html`.
- **Tabela administrativa:** `templates/admin.html`.
- **Campos de cadastro:** `templates/event_form.html` e a função `validate_event_form()` em `app.py`.
- **Regra dos 15 dias:** variável `cutoff`, dentro da rota `index()` em `app.py`.
- **Eventos demonstrativos:** lista `samples`, dentro de `init_database()` em `app.py`.
- **Banco e novas colunas:** constante `SCHEMA` em `app.py`. Em um banco já criado, faça uma migração antes de alterar a estrutura.

## Segurança e publicação

A senha é armazenada somente como hash. Os formulários possuem proteção CSRF, as rotas administrativas exigem sessão e URLs aceitam apenas HTTP/HTTPS. Nunca publique `SECRET_KEY` ou `ADMIN_PASSWORD` no código. Em produção, use HTTPS para que o cookie seguro possa ser ativado com `FLASK_ENV=production`.

## Publicar uma versão de teste no Render

1. Crie um repositório no GitHub e envie todos os arquivos do projeto descompactado.
2. Entre em <https://dashboard.render.com/> usando sua conta do GitHub.
3. Clique em **New +** e depois em **Blueprint**.
4. Escolha o repositório do projeto. O Render identificará o arquivo `render.yaml`.
5. Quando solicitado, informe uma senha forte em `ADMIN_PASSWORD`.
6. Confirme que o plano exibido é **Free — US$ 0/mês**. Não prossiga se aparecer cobrança.
7. Confirme a criação e aguarde o primeiro deploy.
8. Abra o endereço terminado em `.onrender.com`. A administração estará em `/admin`.

O plano gratuito é adequado somente para demonstração: seu SQLite fica no sistema de arquivos temporário e pode ser recriado depois de reinicializações ou novos deploys. Para uso real, anexe um disco persistente pago e configure `DATABASE_PATH=/var/data/database.db`, ou migre o banco para PostgreSQL.
