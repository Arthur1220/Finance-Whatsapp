# API Financeira com WhatsApp e IA Gemini

Este projeto é o backend de um sistema de gestão financeira pessoal que permite aos usuários registrarem suas rendas e despesas através de mensagens simples no WhatsApp. A aplicação utiliza a IA do Google (Gemini) para interpretar a linguagem natural do usuário e se integra com a API Oficial do WhatsApp Business para uma comunicação fluida e assíncrona.

## Visão Geral da Arquitetura

O sistema é construído sobre uma arquitetura de serviços desacoplada, orquestrada com Docker Compose. Ele foi projetado para ser escalável, resiliente e de fácil manutenção, separando claramente as responsabilidades de cada componente:

-   **App `core`**: Configurações centrais do Django e do Celery.
-   **App `users`**: Gerenciamento de usuários e autenticação via JWT.
-   **App `meta`**: Camada de comunicação com a API do WhatsApp. Responsável por receber webhooks e orquestrar as respostas.
-   **App `expenses`**: Gerenciamento de despesas, incluindo modelos, serviços e lógica de categorização.
-   **App `incomes`**: Gerenciamento de entradas de dinheiro (rendas).
-   **App `ai`**: O "cérebro" da aplicação. Responsável por carregar prompts e usar a API do Gemini para interpretar as mensagens dos usuários.
-   **Celery & Redis**: Gerenciam a fila de tarefas assíncronas, garantindo que o processamento dos webhooks seja instantâneo e robusto.

### Funcionalidades Implementadas

-   **Registro de Rendas e Despesas via WhatsApp** usando linguagem natural.
-   **IA para Interpretação de Intenção:** O Gemini classifica se o usuário quer registrar uma despesa, uma renda, pedir ajuda, etc.
-   **Onboarding Automático:** Mensagens de boas-vindas personalizadas para novos usuários.
-   **Resumo Financeiro Mensal:** Comando para receber um balanço de entradas, saídas e gastos por categoria.
-   **Gerenciamento de Despesas:** Comandos para editar, deletar e recategorizar a última despesa registrada.
-   **Gerenciamento de Categorias:** Comandos para criar e deletar categorias de despesa personalizadas.
-   **Processamento Assíncrono de Webhooks** com Celery para alta performance.
-   **Documentação Interativa da API** via Swagger UI (`/api/docs/`).
-   **Ambiente 100% Containerizado** com Docker e Docker Compose.

## Tech Stack

-   **Backend**: Python, Django, Django REST Framework
-   **Banco de Dados**: SQLite (desenvolvimento), preparado para PostgreSQL
-   **Fila de Tarefas**: Celery
-   **Message Broker**: Redis
-   **Inteligência Artificial**: Google Gemini API
-   **Containerização**: Docker, Docker Compose
-   **Túnel de Desenvolvimento**: Ngrok

---

## Como Rodar o Projeto

O método recomendado para rodar este projeto é com Docker, pois ele gerencia todos os serviços (`web`, `worker`, `redis`) automaticamente.

### Pré-requisitos

-   Git
-   Docker
-   Docker Compose
-   Ngrok

### 1. Clonar o Repositório
```bash
git clone <url_do_seu_repositorio>
cd Finance-Whatsapp
```

### 2\. Configurar as Variáveis de Ambiente

Crie o arquivo `backend/.env` (você pode copiar de `backend/.env.example`, se houver) e preencha **todas** as variáveis com suas chaves de API:

```ini
# Chave secreta do Django
SECRET_KEY='sua-chave-secreta-do-django'
DEBUG=True

# Credenciais da API da Meta (WhatsApp)
META_VERIFY_TOKEN='CRIE_UM_TOKEN_SECRETO_PARA_O_WEBHOOK'
META_ACCESS_TOKEN='COLE_SEU_TOKEN_DE_ACESSO_PERMANENTE_DA_META_AQUI'
META_PHONE_NUMBER_ID='COLE_O_ID_DO_SEU_NUMERO_DE_TELEFONE_DO_WHATSAPP_AQUI'

# Credencial da API do Google Gemini
GEMINI_API_KEY='COLE_SUA_CHAVE_DE_API_DO_GEMINI_AQUI'
```

### 3\. Construir e Iniciar os Containers

Na pasta raiz do projeto, execute o seguinte comando:

```bash
docker-compose up --build -d
```

  - Para rodar em segundo plano (detached mode), use `docker-compose up --build -d`.

### 4\. Preparar o Banco de Dados (Primeira Vez)

Com os containers rodando, abra um **novo terminal** e execute os seguintes comandos:

```bash
# Executar as migrações para criar as tabelas
docker-compose exec web python manage.py migrate

# Criar um superusuário para acessar o Admin (`/admin/`)
docker-compose exec web python manage.py createsuperuser
```

Sua aplicação estará disponível em `http://localhost:8000`.

-----

## Reinicialização Fácil do Sistema (Reset Completo)

Se, durante o desenvolvimento, você precisar limpar completamente o banco de dados para testar o fluxo de "novo usuário" ou aplicar novas mudanças nos modelos, siga este procedimento.

**Atenção:** Isso apagará todos os dados locais.

Execute os comandos a partir da **pasta raiz** do projeto (`Finance-Whatsapp/`).

```bash
# 1. Pare e remova todos os containers
docker-compose down

# 2. Apague o banco de dados e as migrações antigas
rm -f backend/db.sqlite3
rm -rf backend/*/migrations/

# 3. Crie os novos arquivos de migração (localmente)
cd backend
python manage.py makemigrations users meta ai expenses incomes summaries payments
cd ..

# 4. Inicie os containers em segundo plano (o '-d' libera o terminal)
docker-compose up --build -d

# 5. Aplique as novas migrações dentro do container
docker-compose exec web python manage.py migrate

# 6. Crie um novo superusuário
docker-compose exec web python manage.py createsuperuser
```

Após estes passos, seu sistema estará rodando com uma base de dados 100% limpa e com a estrutura mais recente.

-----

## Conectando com o WhatsApp (Ngrok)

Para que a API da Meta possa enviar webhooks para sua aplicação local, você precisa usar o `ngrok`.

1.  **Instale e Configure o Ngrok:** Siga as instruções no site oficial. Lembre-se de adicionar seu authtoken (conta gratuita) para sessões mais longas:

    ```bash
    ngrok config add-authtoken SEU_TOKEN_AQUI
    ```

2.  **Execute:** Com sua aplicação rodando, abra um novo terminal e inicie o túnel:

    ```bash
    ngrok http 8000
    ```

3.  **Use a URL:** Copie a URL `https://...` fornecida pelo `ngrok` e use-a na configuração do seu webhook na plataforma da Meta, adicionando o caminho do seu endpoint no final:
    `https://SUA-URL-DO-NGROK.ngrok-free.app/api/meta/webhook/`

**Importante:** A cada reinício do `ngrok`, você precisa atualizar esta URL no painel da Meta.

-----

## Executando os Testes

Para garantir a integridade do código, rode a suíte de testes automatizados:

```bash
docker-compose exec web python manage.py test
```

## Principais Endpoints da API

  - `http://localhost:8000/admin/`: Painel de administração do Django.
  - `http://localhost:8000/api/docs/`: Documentação interativa da API (Swagger UI).
  - `http://localhost:8000/api/login/`: `POST` para obter tokens JWT (para futuras APIs).
  - `http://localhost:8000/api/meta/webhook/`: **(Apenas para a Meta)** Endpoint que recebe os webhooks do WhatsApp.
