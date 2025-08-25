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
from .models import Message

# Inicializa o logger para este módulo.
logger = logging.getLogger(__name__)

# --- Camada de Serviço para o Webhook ---

class WebhookService:
    """
    Encapsula toda a lógica de negócio para processar webhooks do WhatsApp.
    """
    def process_payload(self, payload: dict):
        """
        Ponto de entrada principal que orquestra o processamento do payload.
        """
        logger.info("WebhookService: Starting payload processing.")
        
        if not (payload.get('object') == 'whatsapp_business_account' and payload.get('entry')):
            logger.warning("WebhookService: Payload is not a valid WhatsApp business account notification.")
            return

        for entry in payload['entry']:
            self._process_entry(entry)

    def _process_entry(self, entry: dict):
        """
        Processa uma única 'entry' do payload, que pode conter múltiplas 'changes'.
        """
        for change in entry.get('changes', []):
            if change.get('field') == 'messages' and 'value' in change:
                self._process_change_value(change['value'])

    def _process_change_value(self, value: dict):
        """
        Processa o objeto 'value' que contém informações de contatos e mensagens.
        """
        contact_info = value.get('contacts', [{}])[0]
        contact_name = contact_info.get('profile', {}).get('name')
        sender_wa_id = contact_info.get('wa_id')

        if not sender_wa_id:
            logger.warning("WebhookService: No sender WA ID found in contact info.")
            return

        for message_data in value.get('messages', []):
            message_type = message_data.get('type')
            
            if message_type == 'text':
                self._handle_text_message(message_data, contact_name, sender_wa_id)
            else:
                self._handle_unsupported_message(message_data, contact_name, message_type, sender_wa_id)

    def _handle_text_message(self, message_data: dict, contact_name: Optional[str], sender_wa_id: str):
        """
        Processa uma mensagem de texto recebida.
        """
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp_str = message_data.get('timestamp')
        replied_to_wamid = message_data.get('context', {}).get('id')

        if not all([whatsapp_id, text_body, timestamp_str]):
            logger.warning("WebhookService: Incomplete text message data received. Skipping.")
            return

        user, _ = self._find_or_create_user(sender_wa_id, contact_name)
        timestamp = datetime.fromtimestamp(int(timestamp_str), tz=timezone.get_current_timezone())

        original_message = None
        if replied_to_wamid:
            original_message = Message.objects.filter(whatsapp_message_id=replied_to_wamid).first()

        try:
            incoming_message, created = Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user, 'body': text_body, 'timestamp': timestamp,
                    'message_type': 'text', 'direction': 'INBOUND', 'replied_to': original_message
                }
            )
            if created:
                logger.info(f"Inbound text message from user {user.id} saved (WAMID: {whatsapp_id}).")
            
            # Aqui é onde a lógica da IA será chamada no futuro.
            # Por enquanto, enviamos uma resposta de confirmação.
            response_text = f"Olá, {user.first_name}! Sua mensagem foi recebida."
            MessageService().send_text_message(user, response_text, replied_to=incoming_message)

        except IntegrityError:
            logger.warning(f"Inbound message with WAMID {whatsapp_id} already exists. Skipping.")
        except Exception:
            logger.error(f"WebhookService: Unexpected error processing text message for user {user.id}.", exc_info=True)

    def _handle_unsupported_message(self, message_data: dict, contact_name: Optional[str], message_type: str, sender_wa_id: str):
        """
        Processa mensagens que não são de texto e envia uma resposta padrão.
        """
        user, _ = self._find_or_create_user(sender_wa_id, contact_name)
        logger.info(f"Received an unsupported message of type '{message_type}' from user {user.id}.")

        response_text = "Desculpe, no momento nosso sistema só processa mensagens de texto."
        MessageService().send_text_message(user, response_text)

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