import json
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from datetime import datetime
from django.utils import timezone
import phonenumbers
from phonenumbers import geocoder

# Import models from both apps
from .models import Message
from users.models import User

# Import the service function to send WhatsApp messages
from .services import send_whatsapp_message

class MetaWebhookView(APIView):
    """
    View para receber e processar webhooks da API da Meta (WhatsApp).
    """
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

        if (
            'object' in data and data.get('object') == 'whatsapp_business_account' and
            'entry' in data and data.get('entry')
        ):
            for entry in data['entry']:
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages' and 'value' in change:
                        value = change['value']
                        
                        # --- NOVA LÓGICA AQUI ---
                        # Extract contact info at a higher level
                        # Extraia as informações de contato em um nível superior
                        contact_profile = value.get('contacts', [{}])[0].get('profile', {})
                        contact_name = contact_profile.get('name', None)
                        # --- FIM DA NOVA LÓGICA ---
                        
                        for message_data in value.get('messages', []):
                            if message_data.get('type') == 'text':
                                # Pass the contact name to the handler function
                                # Passe o nome do contato para a função de tratamento
                                self.handle_text_message(message_data, contact_name)
        
        return Response(status=status.HTTP_200_OK)

    def handle_text_message(self, message_data: dict, contact_name: str = None):
        """
        Processa e salva uma mensagem de texto recebida.
        """
        sender_phone = message_data.get('from')
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp_str = message_data.get('timestamp')

        if not all([whatsapp_id, sender_phone, text_body, timestamp_str]):
            print("Incomplete message data received, skipping.")
            return

        # Pass the contact name when creating the user
        # Passe o nome do contato ao criar o usuário
        user, created = self.get_or_create_user_from_phone(sender_phone, contact_name)
        if created:
            print(f"New user '{user.first_name}' created for phone number {sender_phone}")

        timestamp_dt = datetime.fromtimestamp(int(timestamp_str), tz=timezone.get_current_timezone())

        try:
            Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user,
                    'body': text_body,
                    'timestamp': timestamp_dt
                }
            )
            print(f"Message from {sender_phone} (User: {user.username}) saved to database.")

            # Lógica de resposta
            texto_de_resposta = f"Olá, {user.first_name}! Recebemos sua mensagem: '{text_body}'."
            send_whatsapp_message(user, texto_de_resposta)

        except Exception as e:
            print(f"Error saving message to database or replying: {e}")

    def get_or_create_user_from_phone(self, phone_number: str, full_name: str = None):
        """
        Encontra um usuário pelo número de telefone ou cria um novo, incluindo nome e sobrenome.
        """
        first_name = None
        last_name = ""
        if full_name:
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            if len(name_parts) > 1:
                last_name = name_parts[1]

        try:
            parsed_number = phonenumbers.parse(f"+{phone_number}", None)
            country_code = geocoder.region_code_for_number(parsed_number)
        except phonenumbers.phonumberutil.NumberParseException:
            country_code = None
        
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'username': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'country_code': country_code
            }
        )

        # Logic to update the name if the user already exists and the name is available now
        # Lógica para atualizar o nome se o usuário já existir e o nome estiver disponível agora
        if not created and full_name and not user.first_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save()

        if created:
            user.set_unusable_password()
            user.save()

        return user, created