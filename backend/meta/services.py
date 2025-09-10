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


logger = logging.getLogger(__name__)

# ==============================================================================
# SERVIÇO DE PROCESSAMENTO DE WEBHOOKS
# ==============================================================================
class WebhookService:
    """
    Orquestra o processamento de um payload de webhook vindo da Meta.
    """

    def process_payload(self, payload: dict):
        """
        Ponto de entrada principal. Valida e delega o payload para processamento.
        """
        if not (payload.get('object') == 'whatsapp_business_account' and payload.get('entry')):
            return
        for entry in payload['entry']:
            for change in entry.get('changes', []):
                if change.get('field') == 'messages' and 'value' in change:
                    self._process_message_value(change['value'])

    def _process_message_value(self, value: dict):
        """
        Processa o objeto 'value', que contém a mensagem do usuário.
        """
        if 'messages' not in value:
            logger.info("WebhookService: Received a non-message event. Skipping.")
            return

        message_data = value.get('messages', [{}])[0]
        sender_wa_id = message_data.get('from')
        if not sender_wa_id:
            return

        contact_info = value.get('contacts', [{}])[0]
        contact_name = contact_info.get('profile', {}).get('name')
        
        user, is_new_user = self._find_or_create_user(sender_wa_id, contact_name)
        
        # Salvamos a mensagem de entrada para ter o registro.
        self._save_inbound_message(message_data, user)
        
        # Envia a resposta apropriada.
        self._send_appropriate_reply(user, is_new_user)

    def _save_inbound_message(self, message_data: dict, user: User) -> Optional[Message]:
        """
        Salva a mensagem de entrada (`INBOUND`) no banco de dados.
        Retorna o objeto da mensagem salva.
        """
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp = datetime.fromtimestamp(int(message_data.get('timestamp')), tz=timezone.get_current_timezone())
        
        try:
            message, created = Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user, 
                    'body': text_body, 
                    'timestamp': timestamp, 
                    'direction': 'INBOUND'
                }
            )
            if created:
                logger.info(f"Inbound message from user {user.id} saved (WAMID: {whatsapp_id}).")
            return message
        except IntegrityError:
            logger.warning(f"Inbound message with WAMID {whatsapp_id} already exists. Skipping.")
            return None
        except Exception:
            logger.error(f"Error saving inbound message for user {user.id}.", exc_info=True)
            return None

    def _send_appropriate_reply(self, user: User, is_new_user: bool):
        """
        Decide qual mensagem de resposta enviar com base no status do usuário (novo ou existente).
        """
        if is_new_user:
            # Fluxo para um NOVO usuário.
            response_text = (
                f"Olá, {user.first_name}! 👋 Bem-vindo(a) ao Finance-Whatsapp!\n\n"
                "Este é o seu novo canal para registrar suas despesas de forma rápida e fácil. "
                "Para começar, basta enviar uma mensagem no formato:\n\n"
                "*VALOR DESCRIÇÃO*\n\nExemplo: *15,50 almoço no restaurante*"
            )
        else:
            # Fluxo para um usuário EXISTENTE.
            response_text = (
                f"Olá, {user.first_name}! Recebemos sua mensagem e ela foi registrada. "
                "Responderemos assim que possível. Obrigado!"
            )
        
        MessageService().send_text_message(user.phone_number, response_text)

    def _find_or_create_user(self, phone_number: str, full_name: Optional[str]) -> tuple[User, bool]:
        """
        Encontra ou cria um usuário, retornando o objeto e um booleano 'created'.
        """
        # (Este método não muda, sua lógica está perfeita)
        first_name = ""
        last_name = ""
        if full_name:
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            if len(name_parts) > 1:
                last_name = name_parts[1]
        
        defaults = {'username': phone_number}
        if first_name:
            defaults['first_name'] = first_name
            defaults['last_name'] = last_name

        try:
            parsed_number = phonenumbers.parse(f"+{phone_number}", None)
            defaults['country_code'] = geocoder.region_code_for_number(parsed_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            logger.warning(f"Could not parse phone number: {phone_number}")

        user, created = User.objects.update_or_create(phone_number=phone_number, defaults=defaults)
        if created:
            user.set_unusable_password()
            user.save()
            logger.info(f"Created new user {user.id} for phone number {phone_number}.")
        
        return user, created

# ==============================================================================
# SERVIÇO DE ENVIO DE MENSAGENS
# ==============================================================================
class MessageService:
    """
    Encapsula a lógica para se comunicar com a API da Meta APENAS para ENVIO.
    Não salva mais as mensagens de saída.
    """
    API_VERSION = 'v20.0'
    BASE_URL = 'https://graph.facebook.com'

    def send_text_message(self, recipient_phone_number: str, text: str):
        """
        Envia uma mensagem de texto simples para um destinatário.
        """
        if not recipient_phone_number:
            logger.error("MessageService: Attempted to send message but recipient_phone_number is missing.")
            return

        phone_number_id = settings.META_PHONE_NUMBER_ID
        access_token = settings.META_ACCESS_TOKEN
        url = f"{self.BASE_URL}/{self.API_VERSION}/{phone_number_id}/messages"
        
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp", "to": recipient_phone_number,
            "type": "text", "text": {"body": text}
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
            response.raise_for_status()
            response_data = response.json()
            sent_message_id = response_data['messages'][0]['id']
            logger.info(f"Message sent successfully to {recipient_phone_number}! WAMID: {sent_message_id}")
            return response_data
        except requests.exceptions.RequestException:
            logger.error(f"MessageService: Failed to send message to {recipient_phone_number}.", exc_info=True)
            return None