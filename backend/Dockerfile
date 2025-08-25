# 1. Imagem Base: Começamos com uma imagem oficial e leve do Python.
FROM python:3.11-slim

# 2. Variáveis de Ambiente: Otimizações para rodar Python no Docker.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Diretório de Trabalho: Define o diretório padrão dentro do container.
WORKDIR /app

# 4. Instalar Dependências: Copia e instala as bibliotecas primeiro.
#    Isso aproveita o cache do Docker. Se o requirements.txt não mudar,
#    o Docker não reinstala tudo a cada build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar o Código: Copia todo o código do seu projeto para o container.
COPY . .

# 6. Expor a Porta: Informa ao Docker que a aplicação rodará na porta 8000.
EXPOSE 8000

# 7. Comando Padrão: O comando para iniciar a aplicação usando Gunicorn.
#    Em um ambiente de produção, este seria o comando usado.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]