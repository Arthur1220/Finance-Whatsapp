import requests
import json
from django.conf import settings
from django.utils import timezone

from users.models import User
from .models import Message

def send_whatsapp_message(recipient_wa_id: str, text_message: str, user_object: User, replied_to: Message = None):
    """
    Envia uma mensagem de texto e salva um registro dela no banco de dados.
    """
    api_version = 'v20.0'
    access_token = settings.META_ACCESS_TOKEN
    phone_number_id = settings.META_PHONE_NUMBER_ID
    
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_wa_id,
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
        print(f"Message sent successfully to {recipient_wa_id}! WAMID: {sent_message_id}")
        
        Message.objects.create(
            whatsapp_message_id=sent_message_id,
            sender=user_object,
            replied_to=replied_to,
            direction='OUTBOUND',
            body=text_message,
            message_type='text',
            timestamp=timezone.now()
        )
        print("Outbound message saved to database.")
        
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {recipient_wa_id}: {e}")
        if e.response:
            print(f"Error details: {e.response.text}")
        return None