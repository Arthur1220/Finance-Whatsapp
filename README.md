# API Financeira com WhatsApp e IA Gemini

Este projeto é o backend para um sistema de gestão financeira que se integra com a API Oficial do WhatsApp Business (Meta) e utiliza a IA do Google (Gemini) para processar e responder a mensagens de forma inteligente e assíncrona.

## Visão Geral da Arquitetura

O sistema é construído sobre uma arquitetura de microsserviços desacoplada, orquestrada com Docker Compose. Ele foi projetado para ser escalável, resiliente e de fácil manutenção, separando claramente as responsabilidades de cada componente:

-   **App `core`**: Configurações centrais do Django e do Celery.
-   **App `users`**: Gerenciamento de usuários, autenticação via JWT e documentação da API.
-   **App `meta`**: Camada de comunicação com a API do WhatsApp. Responsável por receber webhooks e enviar mensagens.
-   **App `ai`**: O "cérebro" da aplicação. Responsável por carregar prompts, interagir com a API do Gemini e gerar respostas inteligentes.
-   **Celery & Redis**: Gerenciam a fila de tarefas assíncronas, garantindo que o processamento de webhooks seja instantâneo e robusto, sem risco de timeouts.

### Funcionalidades Implementadas

-   **Autenticação Segura via JWT** (`/api/login/`).
-   **Processamento Assíncrono de Webhooks** com Celery para alta performance.
-   **Integração com a IA Gemini** para geração de respostas contextuais.
-   **Histórico de Conversa** para alimentar a IA e manter o contexto.
-   **Criação Automática de Usuários** a partir de novas conversas no WhatsApp.
-   **Logs de Interação com a IA** para depuração e análise (`AILog`).
-   **Documentação Interativa da API** via Swagger UI (`/api/docs/`).
-   **Ambiente 100% Containerizado** com Docker e Docker Compose.
-   **Testes Automatizados** para garantir a estabilidade do código.

## Tech Stack

-   **Backend**: Python, Django, Django REST Framework
-   **Banco de Dados**: SQLite (desenvolvimento), preparado para PostgreSQL
-   **Fila de Tarefas**: Celery
-   **Message Broker**: Redis
-   **Servidor WSGI**: Gunicorn
-   **Inteligência Artificial**: Google Gemini API
-   **Containerização**: Docker, Docker Compose
-   **Túnel de Desenvolvimento**: Ngrok

---

## Pré-requisitos

-   Git
-   Python 3.11+ (`pip`, `venv`)
-   Docker e Docker Compose (para o método de container)
-   Ngrok (para conectar com a API da Meta em ambiente de desenvolvimento)

---

## Como Rodar o Projeto

Você pode rodar a aplicação de duas maneiras: com Docker (método recomendado para consistência) ou localmente em um ambiente virtual (ótimo para depuração mais direta).

### Método 1: Rodar com Docker (Recomendado)

1.  **Clone o Repositório:**
    ```bash
    git clone <url_do_seu_repositorio>
    cd Finance-Whatsapp
    ```

2.  **Configure as Variáveis de Ambiente:**
    Crie e preencha o arquivo `backend/.env` com todas as suas chaves de API (`SECRET_KEY`, credenciais da `META` e do `GEMINI`). Veja o arquivo `.env.example` como referência.

3.  **Construa e Inicie os Containers:**
    Na pasta raiz do projeto, execute:
    ```bash
    docker-compose up --build
    ```
    -   Este comando iniciará 3 serviços: `web` (Django), `worker` (Celery) e `redis`.
    -   Use `docker-compose up -d` para rodar em segundo plano.

4.  **Prepare o Banco de Dados (Primeira Vez):**
    Com os containers rodando, abra um **novo terminal** e execute:
    ```bash
    # Executar migrações
    docker-compose exec web python manage.py migrate
    # Criar um superusuário
    docker-compose exec web python manage.py createsuperuser
    ```

    Sua aplicação estará disponível em `http://localhost:8000`.

### Método 2: Rodar Localmente (Ambiente Virtual)

1.  **Clone o repositório e acesse a pasta do backend:**
    ```bash
    git clone <url_do_seu_repositorio>
    cd Finance-Whatsapp/backend
    ```

2.  **Crie e ative o ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate    # Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as Variáveis de Ambiente:**
    Crie e preencha o arquivo `.env` na pasta `backend/` com suas credenciais.

5.  **Inicie o Redis e o Celery:**
    Para a aplicação funcionar localmente, você precisa do Redis rodando. Se você tem Docker, a maneira mais fácil é iniciar apenas o Redis: `docker-compose up -d redis`. Depois, inicie o worker do Celery em um terminal separado:
    ```bash
    # No terminal 1 (com venv ativado)
    celery -A core worker -l info
    ```

6.  **Prepare o Banco de Dados e Inicie o Servidor:**
    Em outro terminal (com venv ativado), execute os comandos do Django:
    ```bash
    # No terminal 2
    python manage.py migrate
    python manage.py createsuperuser # Se for a primeira vez
    python manage.py runserver
    ```

    Sua aplicação estará disponível em `http://localhost:8000`.

---

## Conectando com o WhatsApp (Ngrok)

Para que a API da Meta (que vive na internet) possa enviar webhooks para a sua aplicação (que está rodando na sua máquina local), você precisa de um túnel. O `ngrok` cria esse túnel de forma segura.

### 1. Instalação e Configuração

Se você ainda não tem o `ngrok`, siga os passos de instalação para seu sistema (em WSL/Ubuntu, `sudo apt install ngrok`). Após instalar, conecte sua conta gratuita para obter sessões mais longas:
```bash
# Pegue seu token no dashboard do ngrok: [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken SEU_TOKEN_AQUI
```

*Você só precisa fazer isso uma vez.*

### 2\. Execução

1.  **Garanta que sua aplicação Django esteja rodando**, seja via Docker ou localmente. Ela estará escutando na porta `8000`.
2.  Em um **novo terminal**, inicie o `ngrok`:
    ```bash
    ngrok http 8000
    ```
3.  O `ngrok` exibirá uma URL pública na linha `Forwarding`. Exemplo: `https://abcd-1234.ngrok.io`.
4.  É esta URL `https://...` que você usará para configurar o webhook na plataforma da Meta, seguida do caminho do seu endpoint:
    `https://abcd-1234.ngrok.io/api/meta/webhook/`

-----

## Executando os Testes

Para garantir a integridade do código, rode a suíte de testes automatizados.

```bash
# Rodando com Docker
docker-compose exec web python manage.py test

# Rodando localmente (na pasta backend/, com venv ativado)
python manage.py test
```

## Principais Endpoints da API

  - `http://localhost:8000/admin/`: Painel de administração do Django.
  - `http://localhost:8000/api/docs/`: Documentação interativa da API (Swagger UI).
  - `http://localhost:8000/api/login/`: `POST` com `username` e `password` para obter tokens JWT.
  - `http://localhost:8000/api/users/`: Endpoint CRUD para gerenciamento de usuários.
  - `http://localhost:8000/api/meta/webhook/`: **(Apenas para a Meta)** Endpoint que recebe os webhooks do WhatsApp.
