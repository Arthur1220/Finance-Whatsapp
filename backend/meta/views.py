import json
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from datetime import datetime
import phonenumbers
from phonenumbers import geocoder

# Importe os modelos de ambos os apps
from .models import Message
from users.models import User

class MetaWebhookView(APIView):
    """
    View para receber e processar webhooks da API da Meta (WhatsApp).
    """
    # A Meta não envia um token CSRF, e a autenticação é feita pelo token de verificação.
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Lida com o desafio de verificação do webhook da Meta.
        """
        verify_token = settings.META_VERIFY_TOKEN
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')

        if mode == 'subscribe' and token == verify_token:
            print("WEBHOOK_VERIFIED")
            return HttpResponse(challenge, status=200)
        
        print("WEBHOOK_VERIFICATION_FAILED")
        return HttpResponse('Error, wrong validation token', status=403)

    def post(self, request):
        """
        Lida com as notificações de eventos (ex: mensagens recebidas).
        """
        data = request.data
        print("Received Webhook Payload:")
        print(json.dumps(data, indent=2))

        # Estrutura de verificação para garantir que seja uma notificação de mensagem do WhatsApp.
        if (
            'object' in data and data.get('object') == 'whatsapp_business_account' and
            'entry' in data and data.get('entry')
        ):
            for entry in data['entry']:
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages' and 'value' in change:
                        value = change['value']
                        # Process each received message.
                        # Processa cada mensagem recebida.
                        for message_data in value.get('messages', []):
                            if message_data.get('type') == 'text':
                                self.handle_text_message(message_data)
        
        return Response(status=status.HTTP_200_OK)

    def handle_text_message(self, message_data: dict):
        """
        Processa e salva uma mensagem de texto recebida.
        Ele encontra um usuário existente pelo número de telefone ou cria um novo.
        """
        sender_phone = message_data.get('from')
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp_str = message_data.get('timestamp')

        if not all([whatsapp_id, sender_phone, text_body, timestamp_str]):
            print("Incomplete message data received, skipping.")
            return

        # Obtenha ou crie o usuário associado ao número de telefone
        user, created = self.get_or_create_user_from_phone(sender_phone)
        if created:
            print(f"New user created for phone number {sender_phone} with country {user.country_code}")

        # Converte o carimbo de data/hora em um objeto datetime
        timestamp_dt = datetime.fromtimestamp(int(timestamp_str))

        try:
            # Cria a mensagem no banco de dados, ou a ignora se ela já existir
            Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user, # Link the message to the user object
                    'body': text_body,
                    'timestamp': timestamp_dt
                }
            )
            print(f"Message from {sender_phone} (User: {user.username}) saved to database.")
        except Exception as e:
            print(f"Error saving message to database: {e}")

    def get_or_create_user_from_phone(self, phone_number: str):
        """
        Encontra um usuário pelo número de telefone ou cria um novo se não for encontrado.
        Também analisa o número de telefone para extrair o código do país.
        """
        try:
            # Use a biblioteca phonenumbers para analisar e obter informações da região
            parsed_number = phonenumbers.parse(f"+{phone_number}", None)
            country_code = geocoder.region_code_for_number(parsed_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            country_code = None
        
        # Usamos 'defaults' para fornecer valores apenas se um novo usuário estiver sendo criado
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'username': phone_number, # Use phone number as a unique username
                'country_code': country_code
            }
        )

        if created:
            # Se um novo usuário foi criado, ele não tem uma senha utilizável.
            # Isso os impede de fazer login por meio da autenticação padrão do Django.
            user.set_unusable_password()
            user.save()

        return user, created