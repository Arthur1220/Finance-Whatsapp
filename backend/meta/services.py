import requests
import json
from django.conf import settings
from typing import Union
from users.models import User

def send_whatsapp_message(recipient: Union[User, str], text_message: str):
    """
    Envia uma mensagem de texto para um usuário do WhatsApp via API da Meta.

    Args:
        recipient: O objeto User ou o número de telefone do destinatário no formato internacional (ex: 5511999998888).
        text_message: O conteúdo da mensagem a ser enviada.

    Returns:
        A resposta da API da Meta em formato JSON ou None em caso de erro.
    """
    
    # Verifique se o destinatário é um objeto de Usuário ou uma string
    if isinstance(recipient, User):
        recipient_phone_number = recipient.phone_number
        if not recipient_phone_number:
            print(f"Error: User {recipient.username} does not have a phone number.")
            return None
    else:
        recipient_phone_number = recipient

    api_version = 'v19.0'
    access_token = settings.META_ACCESS_TOKEN
    phone_number_id = settings.META_PHONE_NUMBER_ID
    
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone_number, # This now uses the extracted phone number
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text_message
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        
        print(f"Message sent successfully to {recipient_phone_number}!")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {recipient_phone_number}: {e}")
        if e.response:
            print(f"Error details: {e.response.text}")
        return None