from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Personaliza a exibição do modelo Message no painel de administração do Django.
    """
    list_display = ('sender', 'body', 'timestamp', 'created_at')
    search_fields = ('body', 'sender__username', 'sender__phone_number')
    list_filter = ('timestamp', 'sender')
    readonly_fields = ('id', 'whatsapp_message_id', 'created_at', 'timestamp')
    raw_id_fields = ('sender',)