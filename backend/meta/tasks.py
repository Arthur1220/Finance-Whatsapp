from celery import shared_task
from datetime import datetime
from django.utils import timezone
import phonenumbers
from phonenumbers import geocoder

from .models import Message
from users.models import User
from .services import send_whatsapp_message

@shared_task
def process_webhook_payload(payload: dict):
    """
    Asynchronous task to process the entire webhook payload.
    """
    print("Celery worker started processing payload...")
    
    if payload.get('object') == 'whatsapp_business_account' and payload.get('entry'):
        for entry in payload['entry']:
            for change in entry.get('changes', []):
                if change.get('field') == 'messages' and 'value' in change:
                    value = change['value']
                    contact_info = value.get('contacts', [{}])[0]
                    contact_name = contact_info.get('profile', {}).get('name', None)
                    sender_wa_id = contact_info.get('wa_id', None)

                    for message_data in value.get('messages', []):
                        message_type = message_data.get('type')
                        
                        if message_type == 'text':
                            # Pass the correct sender_wa_id
                            handle_text_message(message_data, contact_name, sender_wa_id)
                        else:
                            # Pass the correct sender_wa_id
                            handle_unsupported_message(message_data, contact_name, message_type, sender_wa_id)
    
    print("Celery worker finished processing.")
    return "Payload processed successfully"

def handle_text_message(message_data: dict, contact_name: str = None, sender_wa_id: str = None):
    whatsapp_id = message_data.get('id')
    text_body = message_data.get('text', {}).get('body')
    timestamp_str = message_data.get('timestamp')
    replied_to_wamid = message_data.get('context', {}).get('id')

    if not all([whatsapp_id, sender_wa_id, text_body, timestamp_str]):
        return

    # Use the reliable sender_wa_id to get/create the user
    user, _ = get_or_create_user_from_phone(sender_wa_id, contact_name)
    timestamp_dt = datetime.fromtimestamp(int(timestamp_str), tz=timezone.get_current_timezone())

    original_message = None
    if replied_to_wamid:
        original_message = Message.objects.filter(whatsapp_message_id=replied_to_wamid).first()

    try:
        incoming_message, _ = Message.objects.get_or_create(
            whatsapp_message_id=whatsapp_id,
            defaults={
                'sender': user, 'body': text_body, 'timestamp': timestamp_dt,
                'message_type': 'text', 'direction': 'INBOUND', 'replied_to': original_message
            }
        )
        print(f"Inbound message from {user.username} saved by worker.")
        
        texto_de_resposta = f"Olá, {user.first_name}! Sua mensagem foi recebida e está sendo processada."
        # Use sender_wa_id as the first argument, as the service expects
        send_whatsapp_message(sender_wa_id, texto_de_resposta, user_object=user, replied_to=incoming_message)
    except Exception as e:
        print(f"Worker error processing text message: {e}")

def handle_unsupported_message(message_data: dict, contact_name: str, message_type: str, sender_wa_id: str = None):
    # Removed 'self' from the function signature
    if not sender_wa_id:
        return

    user, _ = get_or_create_user_from_phone(sender_wa_id, contact_name)
    
    whatsapp_id = message_data.get('id')
    timestamp_str = message_data.get('timestamp')
    timestamp_dt = datetime.fromtimestamp(int(timestamp_str), tz=timezone.get_current_timezone())
    
    Message.objects.get_or_create(
        whatsapp_message_id=whatsapp_id,
        defaults={
            'sender': user, 'timestamp': timestamp_dt,
            'message_type': message_type, 'direction': 'INBOUND'
        }
    )
    print(f"Unsupported message of type '{message_type}' from {user.username} was recorded.")
    
    texto_de_resposta = "Desculpe, no momento só aceitamos mensagens de texto. Por favor, envie sua solicitação em formato de texto."
    # Use sender_wa_id as the first argument
    send_whatsapp_message(sender_wa_id, texto_de_resposta, user_object=user)

def get_or_create_user_from_phone(phone_number: str, full_name: str = None):
    # Removed 'self' from the function signature
    first_name = "" # Default to empty string instead of None
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