import logging
import json
from datetime import datetime
from typing import Optional

import requests
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
import phonenumbers
from phonenumbers import geocoder

from users.models import User
from .models import Message
from ai.services import AIService

logger = logging.getLogger(__name__)

# ==============================================================================
# --- MENSAGENS PADRÃO ---
# ==============================================================================

STANDARD_REPLIES = {
    "pedir_ajuda": (
        "Com certeza! Eu sou o Fin, seu assistente para registro de despesas. Veja o que você pode fazer:\n\n"
        "1️⃣ *Registrar uma Despesa:*\nBasta me enviar uma mensagem no formato `VALOR DESCRIÇÃO`.\nExemplo: `25,50 almoço`\n\n"
        "2️⃣ *Ver Comandos:*\nEnvie `comandos` ou `ajuda` a qualquer momento.\n\n"
        "Posso te ajudar com mais alguma coisa? 😉"
    ),
    "pedir_comandos": (
        "Aqui estão os comandos que você pode usar:\n\n"
        "• `ajuda` ou `comandos`: Mostra esta mensagem de ajuda.\n"
        "• `categorias`: Explica como as categorias de despesas funcionam.\n"
        "• `saldo`: Consulta o saldo atual (em breve).\n"
        "• `extrato`: Mostra o extrato de despesas (em breve).\n"
        "• `resumo`: Fornece um resumo das despesas (em breve).\n\n"
        "Para registrar uma despesa, envie uma mensagem no formato: `VALOR DESCRIÇÃO` (ex: `15,90 padaria`)."
    ),
    "pedir_categorias": "No momento, as categorias são definidas automaticamente, como Alimentação, Transporte, Lazer, etc. Em breve você poderá gerenciá-las!",
    "pedir_saldo": "A funcionalidade de consulta de saldo ainda está em desenvolvimento. Logo teremos novidades! 🚀",
    "pedir_extrato": "A funcionalidade de extrato ainda está em desenvolvimento. Logo teremos novidades! 🚀",
    "pedir_resumo": "A funcionalidade de resumo ainda está em desenvolvimento. Logo teremos novidades! 🚀",
    "indefinido": "Desculpe, não entendi. Para registrar uma despesa, por favor, envie no formato: `VALOR DESCRIÇÃO` (ex: `15,90 padaria`). Se precisar de ajuda, é só mandar `ajuda`.",
    "saudacao_novo_usuario": (
        "Olá, {}! 👋 Bem-vindo(a) ao Finance-Whatsapp!\n\n"
        "Eu sou o Fin, e vou te ajudar a registrar suas despesas de forma rápida e fácil. Quer entender como funciono? Basta enviar uma mensagem como:\n\n"
        "*Me explique o que pode fazer com o Fin*"
    ),
    "saudacao": "Olá! Sou o Fin, seu assistente de despesas. Como posso te ajudar hoje? Para registrar um gasto, é só me enviar `VALOR DESCRIÇÃO`.",
    "agradecimento": "De nada! 😊 Se precisar de mais alguma coisa, é só chamar.",
    "despedida": "Até a próxima! 👋",
}

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

        incoming_message = self._save_inbound_message(message_data, user)
        if not incoming_message:
            return
        
        # Envia a resposta apropriada.
        self._send_appropriate_reply(user, is_new_user, incoming_message)

    def _save_inbound_message(self, message_data: dict, user: User) -> Optional[Message]:
        """
        Salva a mensagem de entrada (`INBOUND`) no banco de dados.
        Retorna o objeto da mensagem salva.
        """
        whatsapp_id = message_data.get('id')
        text_body = message_data.get('text', {}).get('body')
        timestamp = datetime.fromtimestamp(int(message_data.get('timestamp')), tz=timezone.get_current_timezone())
        
        replied_to_wamid = message_data.get('context', {}).get('id')
        original_message = None
        if replied_to_wamid:
            original_message = Message.objects.filter(whatsapp_message_id=replied_to_wamid).first()

        try:
            message, created = Message.objects.get_or_create(
                whatsapp_message_id=whatsapp_id,
                defaults={
                    'sender': user, 
                    'body': text_body, 
                    'timestamp': timestamp, 
                    'direction': 'INBOUND',
                    'replied_to': original_message
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

    def _send_appropriate_reply(self, user: User, is_new_user: bool, incoming_message: Message):
        """
        Decide qual mensagem de resposta enviar com base no status do usuário (novo ou existente).
        """
        if is_new_user:
            # Se o usuário é novo, envia a saudação e encerra o fluxo.
            response_text = STANDARD_REPLIES["saudacao_novo_usuario"].format(user.first_name)
            MessageService().send_text_message(user.phone_number, response_text)
            return

        # Para usuários existentes, o fluxo completo de análise acontece.
        self._handle_user_message(incoming_message, user)

    def _handle_user_message(self, incoming_message: Message, user: User):
        """
        Processa a mensagem do usuário existente, interpretando e respondendo.
        """
        text_body = incoming_message.body

        ai_service = AIService(user=user)
        ai_plan = ai_service.interpret_message(text_body)
        intent = ai_plan.get("intent")

        if intent == "registrar_despesa":
            # Lógica para salvar a despesa
            amount = ai_plan.get("amount")
            description = ai_plan.get("description")
            response_text = f"✅ (Simulação) Despesa de R${amount:.2f} em '{description}' seria registrada!"
        
        elif intent in STANDARD_REPLIES:
            # Se a intenção mapeia para uma resposta padrão
            response_text = STANDARD_REPLIES[intent]
        
        else: # Fallback para 'indefinido'
            response_text = STANDARD_REPLIES["indefinido"]

        MessageService().send_text_message(user, response_text, replied_to=incoming_message)

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
    API_VERSION = 'v20.0'
    BASE_URL = 'https://graph.facebook.com'

    def send_text_message(self, recipient: User, text: str, replied_to: Optional[Message] = None) -> Optional[Message]:
        """
        Envia uma mensagem de texto E salva um registro de SAÍDA (OUTBOUND) no banco.
        Retorna o objeto da mensagem salva.
        """
        if not recipient.phone_number:
            logger.error(f"MessageService: Attempted to send message to user {recipient.id} without a phone number.")
            return None

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
            
            outbound_message = Message.objects.create(
                whatsapp_message_id=sent_message_id, 
                sender=recipient,
                replied_to=replied_to, 
                direction='OUTBOUND',
                body=text, 
                timestamp=timezone.now()
            )
            logger.info(f"Outbound message for user {recipient.id} saved to database.")
            return outbound_message
        except requests.exceptions.RequestException:
            logger.error(f"MessageService: Failed to send message to {recipient.phone_number}.", exc_info=True)
            return None
        except (KeyError, IndexError):
            logger.error(f"MessageService: Unexpected response format from Meta API for user {recipient.id}.", exc_info=True)
            return None