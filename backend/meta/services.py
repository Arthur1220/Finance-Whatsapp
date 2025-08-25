import requests
import json
from django.conf import settings
from django.utils import timezone
from typing import Union

from users.models import User
from .models import Message

def send_whatsapp_message(recipient: Union[User, str], text_message: str, replied_to: Message = None):
    """
    Envia uma mensagem de texto e salva um registro dela no banco de dados.
    """
    if isinstance(recipient, User):
        # Certifique-se de que o objeto do usuário não seja nulo antes de acessar os atributos
        if recipient and recipient.phone_number:
            recipient_phone_number = recipient.phone_number
        else:
            print(f"Error: Invalid User object or user does not have a phone number.")
            return None
    else:
        recipient_phone_number = recipient

    api_version = 'v20.0' # Always good to check for the latest stable version
    access_token = settings.META_ACCESS_TOKEN
    phone_number_id = settings.META_PHONE_NUMBER_ID
    
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Inclui o ID da mensagem original se estivermos respondendo a uma
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone_number,
        "type": "text",
        "text": {"body": text_message}
    }
    if replied_to:
        payload['context'] = {'message_id': replied_to.whatsapp_message_id}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        
        response_data = response.json()
        sent_message_id = response_data['messages'][0]['id']
        print(f"Message sent successfully to {recipient_phone_number}! WAMID: {sent_message_id}")

        # Agora, salve a mensagem de saída no banco de dados
        user = recipient if isinstance(recipient, User) else User.objects.get(phone_number=recipient_phone_number)
        
        Message.objects.create(
            whatsapp_message_id=sent_message_id,
            sender=user, # The 'sender' is always the end-user/contact
            replied_to=replied_to,
            direction='OUTBOUND',
            body=text_message,
            message_type='text',
            timestamp=timezone.now()
        )
        print("Outbound message saved to database.")
        
        return response_data

    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {recipient_phone_number}: {e}")
        if e.response:
            print(f"Error details: {e.response.text}")
        return None