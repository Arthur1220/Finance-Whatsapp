# Finance Whatsapp API

Este projeto é o backend de um sistema de gestão financeira que se integra com a API Oficial da Meta (WhatsApp Business) para automação de comunicação e processos.

## Visão Geral do Projeto

O objetivo principal é criar um serviço robusto que possa receber, processar, armazenar e responder a mensagens do WhatsApp. A aplicação identifica os usuários pelo número de telefone, cria um perfil básico para eles no sistema e armazena o histórico de mensagens, permitindo futuras interações e lógicas de negócio.

### Funcionalidades Principais

-   **Autenticação de Usuário via JWT:** Endpoints seguros para login e gerenciamento de tokens.
-   **Integração com Webhook da Meta:** Endpoint dedicado para receber e verificar notificações em tempo real do WhatsApp.
-   **Criação Automática de Usuários:** Usuários são criados automaticamente no sistema ao enviarem a primeira mensagem.
-   **Identificação de País:** O sistema identifica o país de origem do número de telefone.
-   **Armazenamento de Mensagens:** Histórico de conversas salvo e vinculado a cada usuário.
-   **Serviço para Envio de Mensagens:** Lógica centralizada para enviar mensagens via API da Meta.
-   **Documentação de API (Swagger/OpenAPI):** Documentação interativa e gerada automaticamente.
-   **Ambiente Dockerizado:** Configuração completa com Docker e Docker Compose para um ambiente de desenvolvimento consistente e portátil.
-   **Testes Automatizados:** Suíte de testes para garantir a qualidade e estabilidade do código.

## Tech Stack

-   **Backend:** Python, Django, Django REST Framework
-   **Banco de Dados:** SQLite (desenvolvimento), preparado para PostgreSQL
-   **Servidor WSGI:** Gunicorn
-   **Autenticação:** Simple JWT
-   **Análise de Telefones:** phonenumbers
-   **Containerização:** Docker, Docker Compose

---

## Pré-requisitos

Antes de começar, garanta que você tem as seguintes ferramentas instaladas:

-   Python 3.11+
-   `pip` e `venv`
-   Docker
-   Docker Compose
-   Git

---

## Como Rodar o Projeto

Existem duas maneiras de rodar a aplicação: localmente com um ambiente virtual ou com Docker.

### Método 1: Rodar Localmente (Ambiente Virtual)

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/Arthur1220/Finance-Whatsapp.git
    cd Finance-Whatsapp/backend
    ```

2.  **Crie e ative o ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No macOS/Linux
    # ou
    # venv\Scripts\activate    # No Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    Copie o arquivo de exemplo `.env.example` (se você criar um) ou crie um arquivo `.env` dentro da pasta `backend/` e preencha com suas credenciais:
    ```ini
    SECRET_KEY='sua-chave-secreta-do-django'
    DEBUG=True
    
    # --- Meta WhatsApp API ---
    META_VERIFY_TOKEN='SEU_TOKEN_DE_VERIFICACAO_SECRETO_CRIADO_POR_VOCE'
    META_ACCESS_TOKEN='COLE_O_TOKEN_DE_ACESSO_TEMPORARIO_DA_META_AQUI'
    META_PHONE_NUMBER_ID='COLE_O_ID_DO_NUMERO_DE_TELEFONE_DE_TESTE_AQUI'
    ```

5.  **Aplique as migrações do banco de dados:**
    ```bash
    python manage.py migrate
    ```

6.  **Crie um superusuário para acessar o Admin:**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Inicie o servidor de desenvolvimento:**
    ```bash
    python manage.py runserver
    ```

    A aplicação estará disponível em `http://127.0.0.1:8000`.

### Método 2: Rodar com Docker (Recomendado)

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/Arthur1220/Finance-Whatsapp.git
    cd Finance-Whatsapp
    ```

2.  **Configure as variáveis de ambiente:**
    Certifique-se de que o arquivo `backend/.env` existe e está preenchido como descrito no Método 1. O Docker Compose o utilizará automaticamente.

3.  **Construa e inicie os containers:**
    Este comando irá construir a imagem Docker (se ainda não existir) e iniciar o container da aplicação.
    ```bash
    docker-compose up --build
    ```
    Use `docker-compose up -d` para rodar em segundo plano (detached mode).

4.  **Crie um superusuário (se for a primeira vez):**
    Com os containers rodando, abra **outro terminal** e execute o comando `createsuperuser` dentro do container `web`:
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

    A aplicação estará disponível em `http://127.0.0.1:8000`.

---

## Executando os Testes

Para garantir que tudo está funcionando como esperado, rode a suíte de testes:

```bash
# Rodando localmente
python manage.py test

# Rodando com Docker
docker-compose exec web python manage.py test
```

## Principais Endpoints da API

  - `/api/docs/`: Documentação interativa da API (Swagger UI).
  - `/api/login/`: `POST` com `username` e `password` para obter tokens JWT.
  - `/api/users/`: Endpoint CRUD para gerenciamento de usuários.
  - `/api/users/me/`: `GET` para obter os dados do usuário autenticado.
  - `/api/meta/webhook/`: Endpoint para receber os webhooks da Meta (WhatsApp).
