from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Personaliza a exibição do modelo Message no painel de administração do Django.
    """
    # Define as colunas exibidas na lista de mensagens.
    list_display = ('sender', 'body', 'timestamp', 'created_at')

    # Adiciona uma barra de pesquisa para pesquisar nesses campos.
    search_fields = ('body', 'sender__username', 'sender__phone_number')

    # Adiciona uma barra lateral de filtro.
    list_filter = ('timestamp', 'sender')

    # Torna esses campos somente leitura na visualização de detalhes.
    readonly_fields = ('id', 'whatsapp_message_id', 'timestamp', 'created_at', 'updated_at')
    
    # Melhora o desempenho para campos ForeignKey com muitas entradas.
    raw_id_fields = ('sender',)