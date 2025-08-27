import logging
import json
from datetime import datetime
from typing import Optional

import phonenumbers
from phonenumbers import geocoder
import requests
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from users.models import User
from .models import Message, Conversation
from ai.services import AIService

logger = logging.getLogger(__name__)


class WebhookService:
    CONVERSATION_TIMEOUT_HOURS = 1

    def process_payload(self, payload: dict):
        if not (payload.get('object') == 'whatsapp_business_account' and payload.get('entry')):
            return
        for entry in payload['entry']:
            for change in entry.get('changes', []):
                if change.get('field') == 'messages' and 'value' in change:
                    self._process_change_value(change['value'])

    def _process_change_value(self, value: dict):
        if 'messages' not in value:
            logger.info("WebhookService: Received a non-message event. Skipping.")
            return

        for message_data in value.get('messages', []):
            sender_wa_id = message_data.get('from')
            if not sender_wa_id:
                continue

            contact_info = value.get('contacts', [{}])[0]
            contact_name = contact_info.get('profile', {}).get('name')

            user, _ = self._find_or_create_user(sender_wa_id, contact_name)
            conversation = self._get_or_create_active_conversation(user)
            message_type = message_data.get('type')

            if message_type == 'text':
                self._handle_text_message(message_data, user, conversation)
            else:
                self._handle_unsupported_message(message_data, user, conversation, message_type)

    def _handle_text_message(self, message_data: dict, user: User, conversation: Conversation):
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp = datetime.fromtimestamp(int(message_data.get('timestamp')), tz=timezone.get_current_timezone())
        replied_to_wamid = message_data.get('context', {}).get('id')
        
        original_message = Message.objects.filter(whatsapp_message_id=replied_to_wamid).first() if replied_to_wamid else None

        try:
            incoming_message, created = Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user, 'conversation': conversation, 'body': text_body, 
                    'timestamp': timestamp, 'message_type': 'text', 
                    'direction': 'INBOUND', 'replied_to': original_message
                }
            )
            if created:
                logger.info(f"Inbound text message from user {user.id} saved to conversation {conversation.id}.")
            
            # Instancia o serviço da IA com o usuário E a conversa
            ai_service = AIService(user=user, conversation=conversation)
            # O método principal agora é get_ai_plan
            ai_plan = ai_service.get_ai_plan()
            
            response_text = ai_plan.get("response_text", "Desculpe, tive um problema para processar. Tente de novo?")
            
            # Envia a resposta de volta para o usuário
            MessageService().send_text_message(user, response_text, replied_to=incoming_message)
            
            action = ai_plan.get("conversation_action")
            if action == "END_CONVERSATION":
                conversation.status = 'CLOSED'
                conversation.end_time = timezone.now()
                conversation.save()
                logger.info(f"Conversation {conversation.id} closed by AI action.")

        except IntegrityError:
            logger.warning(f"Inbound message with WAMID {whatsapp_id} already exists. Skipping.")
        except Exception:
            logger.error(f"WebhookService: Unexpected error processing text message for user {user.id}.", exc_info=True)

    def _handle_unsupported_message(self, message_data: dict, user: User, conversation: Conversation, message_type: str):
        logger.info(f"Received an unsupported message of type '{message_type}' from user {user.id}.")
        response_text = "Desculpe, no momento nosso sistema só processa mensagens de texto."
        MessageService().send_text_message(user, response_text)

    def _get_or_create_active_conversation(self, user: User) -> Conversation:
        active_conversation = Conversation.objects.filter(user=user, status='ACTIVE').first()
        if active_conversation:
            last_message = active_conversation.messages.order_by('-timestamp').first()
            if last_message and (timezone.now() - last_message.timestamp > timezone.timedelta(hours=self.CONVERSATION_TIMEOUT_HOURS)):
                active_conversation.status = 'CLOSED'
                active_conversation.end_time = timezone.now()
                active_conversation.save()
                logger.info(f"Closed inactive conversation {active_conversation.id} for user {user.id}")
                active_conversation = None
        if not active_conversation:
            active_conversation = Conversation.objects.create(user=user)
            logger.info(f"Created new conversation {active_conversation.id} for user {user.id}")
        return active_conversation

    def _find_or_create_user(self, phone_number: str, full_name: Optional[str]) -> tuple[User, bool]:
        """
        Encontra um usuário pelo número de telefone ou cria um novo.
        """
        first_name = ""
        last_name = ""
        if full_name:
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            if len(name_parts) > 1:
                last_name = name_parts[1]
        
        defaults = {'username': phone_number}
        if first_name: # Only add names to defaults if they exist
            defaults['first_name'] = first_name
            defaults['last_name'] = last_name

        try:
            parsed_number = phonenumbers.parse(f"+{phone_number}", None)
            defaults['country_code'] = geocoder.region_code_for_number(parsed_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            logger.warning(f"Could not parse phone number: {phone_number}")

        user, created = User.objects.update_or_create(
            phone_number=phone_number,
            defaults=defaults
        )
        if created:
            user.set_unusable_password()
            user.save()
            logger.info(f"Created new user {user.id} for phone number {phone_number}.")
        
        return user, created

# --- Camada de Serviço para Envio de Mensagens ---

class MessageService:
    """
    Encapsula a lógica para interagir com a API da Meta para envio de mensagens.
    """
    API_VERSION = 'v20.0'
    BASE_URL = 'https://graph.facebook.com'

    def send_text_message(self, recipient: User, text: str, replied_to: Optional[Message] = None):
        """
        Envia uma mensagem de texto para um destinatário e a salva no banco de dados.
        """
        if not recipient.phone_number:
            logger.error(f"MessageService: Attempted to send message to user {recipient.id} without a phone number.")
            return

        phone_number_id = settings.META_PHONE_NUMBER_ID
        access_token = settings.META_ACCESS_TOKEN
        url = f"{self.BASE_URL}/{self.API_VERSION}/{phone_number_id}/messages"
        
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp", "to": recipient.phone_number,
            "type": "text", "text": {"body": text}
        }
        if replied_to:
            payload['context'] = {'message_id': replied_to.whatsapp_message_id}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
            response.raise_for_status()
            
            response_data = response.json()
            sent_message_id = response_data['messages'][0]['id']
            logger.info(f"Message sent to user {recipient.id} via Meta API. WAMID: {sent_message_id}")

            Message.objects.create(
                whatsapp_message_id=sent_message_id, sender=recipient,
                replied_to=replied_to, direction='OUTBOUND',
                body=text, message_type='text', timestamp=timezone.now()
            )
            logger.info(f"Outbound message for user {recipient.id} saved to database.")

        except requests.exceptions.RequestException:
            logger.error(f"MessageService: Failed to send message to user {recipient.id}.", exc_info=True)
        except (KeyError, IndexError):
            logger.error(f"MessageService: Invalid response from Meta API after sending message.", exc_info=True)