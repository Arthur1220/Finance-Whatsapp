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

from .models import Message
from users.models import User
from .services import send_whatsapp_message

class MetaWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
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
        data = request.data
        print("Received Webhook Payload:")
        print(json.dumps(data, indent=2))

        if (
            data.get('object') == 'whatsapp_business_account' and
            data.get('entry')
        ):
            for entry in data['entry']:
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages' and 'value' in change:
                        value = change['value']
                        contact_profile = value.get('contacts', [{}])[0].get('profile', {})
                        contact_name = contact_profile.get('name', None)
                        
                        for message_data in value.get('messages', []):
                            message_type = message_data.get('type')
                            
                            if message_type == 'text':
                                self.handle_text_message(message_data, contact_name)
                            else:
                                self.handle_unsupported_message(message_data, contact_name, message_type)
        
        return Response(status=status.HTTP_200_OK)

    def handle_text_message(self, message_data: dict, contact_name: str = None):
        sender_phone = message_data.get('from')
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp_str = message_data.get('timestamp')
        
        replied_to_wamid = message_data.get('context', {}).get('id')

        if not all([whatsapp_id, sender_phone, text_body, timestamp_str]):
            return

        user, created = self.get_or_create_user_from_phone(sender_phone, contact_name)
        timestamp_dt = datetime.fromtimestamp(int(timestamp_str), tz=timezone.get_current_timezone())

        original_message = None
        if replied_to_wamid:
            original_message = Message.objects.filter(whatsapp_message_id=replied_to_wamid).first()

        try:
            incoming_message, created = Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user,
                    'body': text_body,
                    'timestamp': timestamp_dt,
                    'message_type': 'text',
                    'direction': 'INBOUND',
                    'replied_to': original_message
                }
            )
            print(f"Inbound message from {user.username} saved.")
            if original_message:
                print(f"  -> It's a reply to message ID: {original_message.whatsapp_message_id}")

            texto_de_resposta = f"Olá, {user.first_name}! Recebemos e processamos a sua mensagem."
            send_whatsapp_message(user, texto_de_resposta, replied_to=incoming_message)

        except Exception as e:
            print(f"Error processing text message: {e}")

    def handle_unsupported_message(self, message_data: dict, contact_name: str, message_type: str):
        sender_phone = message_data.get('from')
        if not sender_phone:
            return

        user, _ = self.get_or_create_user_from_phone(sender_phone, contact_name)
        
        whatsapp_id = message_data.get('id')
        timestamp_str = message_data.get('timestamp')
        timestamp_dt = datetime.fromtimestamp(int(timestamp_str), tz=timezone.get_current_timezone())
        
        Message.objects.get_or_create(
            whatsapp_message_id=whatsapp_id,
            defaults={
                'sender': user,
                'timestamp': timestamp_dt,
                'message_type': message_type,
                'direction': 'INBOUND',
            }
        )
        print(f"Unsupported message of type '{message_type}' from {user.username} was recorded.")
        
        texto_de_resposta = "Desculpe, no momento só aceitamos mensagens de texto. Por favor, envie sua solicitação em formato de texto."
        send_whatsapp_message(user, texto_de_resposta)
        
    def get_or_create_user_from_phone(self, phone_number: str, full_name: str = None):
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
        except phonenumbers.phonenumberutil.NumberParseException:
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

        if not created and full_name and not user.first_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save()

        if created:
            user.set_unusable_password()
            user.save()

        return user, created