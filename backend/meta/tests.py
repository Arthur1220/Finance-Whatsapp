import json
from django.urls import reverse
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

# Importe os modelos que precisamos verificar
from users.models import User
from .models import Message

class MetaWebhookTests(APITestCase):
    """
    Suite de testes para o Webhook da Meta.
    """

    def setUp(self):
        """
        Configure os dados iniciais para os testes.
        """
        self.webhook_url = reverse('meta-webhook')
        # Este é o token secreto que você definiu no seu arquivo .env
        self.verify_token = settings.META_VERIFY_TOKEN

    def test_webhook_verification_success(self):
        """
        Garante que o webhook pode ser verificado pela Meta com sucesso.
        """
        params = {
            'hub.mode': 'subscribe',
            'hub.challenge': '123456789',
            'hub.verify_token': self.verify_token
        }
        response = self.client.get(self.webhook_url, params)
        
        # Esperamos uma resposta 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # O corpo da resposta deve ser o valor 'hub.challenge'
        self.assertEqual(response.content.decode(), '123456789')

    def test_webhook_verification_failure(self):
        """
        Garante que o webhook rejeita a verificação com um token incorreto.
        """
        params = {
            'hub.mode': 'subscribe',
            'hub.challenge': '123456789',
            'hub.verify_token': 'WRONG_TOKEN'
        }
        response = self.client.get(self.webhook_url, params)
        
        # Esperamos uma resposta 403 Proibido
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receive_text_message(self):
        """
        Testa o processamento de uma mensagem de texto recebida válida da Meta.
        Isso deve criar um novo Usuário e uma nova Mensagem.
        """
        # Uma carga útil realista simulando o que a Meta envia
        meta_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "5511999998888",
                                        "id": "wamid.HBjNSk_-FwAEl8-U8-A",
                                        "timestamp": "1664303417",
                                        "text": {"body": "Hello from test!"},
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        
        # Verifique as contagens antes da requisição
        initial_user_count = User.objects.count()
        initial_message_count = Message.objects.count()

        # Faça a requisição POST para o nosso webhook
        response = self.client.post(self.webhook_url, data=meta_payload, format='json')

        # Devemos sempre receber um 200 OK para confirmar o recebimento
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verifique se um novo Usuário e uma nova Mensagem foram criados
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        self.assertEqual(Message.objects.count(), initial_message_count + 1)

        # Verifique os detalhes dos objetos criados
        created_user = User.objects.get(phone_number="5511999998888")
        self.assertEqual(created_user.username, "5511999998888")
        self.assertEqual(created_user.country_code, "BR") # From phonenumbers library

        created_message = Message.objects.first()
        self.assertEqual(created_message.sender, created_user)
        self.assertEqual(created_message.body, "Hello from test!")
        self.assertEqual(created_message.whatsapp_message_id, "wamid.HBjNSk_-FwAEl8-U8-A")