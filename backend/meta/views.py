import logging
from django.http import HttpResponse, HttpRequest
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .tasks import process_webhook_payload

# Inicializa o logger para este módulo.
logger = logging.getLogger(__name__)

class MetaWebhookView(APIView):
    """
    Endpoint para receber e processar os webhooks da API da Meta (WhatsApp).

    Esta view é a porta de entrada para toda a comunicação iniciada pelo WhatsApp.
    Ela é projetada para ser extremamente rápida e resiliente, delegando todo o processamento pesado para uma fila de tarefas assíncronas (Celery).
    """
    # A autenticação é feita pela verificação do 'verify_token' no método GET, e pela assinatura digital da Meta nas requisições POST (verificação implícita).
    # Portanto, não precisamos de autenticação de sessão ou JWT aqui.
    permission_classes = [permissions.AllowAny]

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Valida a assinatura do webhook (challenge).

        Este método é chamado pela Meta apenas uma vez, durante a configuração do webhook no painel de desenvolvedores, para confirmar que a URL fornecida é válida e pertence ao desenvolvedor.
        """
        verify_token = settings.META_VERIFY_TOKEN
        
        # A Meta envia estes três parâmetros na URL.
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')

        # Valida se o 'mode' é 'subscribe' e se o 'token' bate com o nosso.
        if mode == 'subscribe' and token == verify_token:
            logger.info("Webhook verification successful!")
            return HttpResponse(challenge, status=200)
        
        logger.warning(f"Webhook verification failed. Token received: '{token}'")
        return HttpResponse('Error, wrong validation token', status=403)

    def post(self, request: HttpRequest) -> Response:
        """
        Recebe as notificações de eventos (ex: novas mensagens) e as enfileira para processamento.

        Este método recebe o payload JSON da Meta, envia para a tarefa assíncrona do Celery (`process_webhook_payload`) e responde imediatamente com 200 OK.
        Isso garante que a Meta não receba um timeout, mesmo que o processamento da mensagem seja demorado.
        """
        payload = request.data
        
        try:
            # A função .delay() enfileira a tarefa. O payload é serializado
            # e enviado para o Redis, de onde um worker do Celery o pegará.
            task = process_webhook_payload.delay(payload)
            logger.info(f"Webhook payload received and tasked to Celery worker with ID: {task.id}")
            
            return Response(status=status.HTTP_200_OK)
        
        except Exception as e:
            # Captura uma falha crítica (ex: Redis fora do ar) ao tentar enfileirar a tarefa.
            logger.critical(
                "Failed to queue webhook payload to Celery worker.", 
                exc_info=True
            )
            # Retorna um erro 500 para sinalizar que algo grave aconteceu.
            return Response(
                {"error": "Internal server error processing webhook."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )