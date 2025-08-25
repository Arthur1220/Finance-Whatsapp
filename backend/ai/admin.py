from django.contrib import admin
from .models import AILog

@admin.register(AILog)
class AILogAdmin(admin.ModelAdmin):
    """
    Configuração para exibir os logs de interação da IA no painel de Admin.
    """
    # Mostra estas colunas na lista de logs
    list_display = ('timestamp', 'user', 'duration_ms', 'cost')
    
    # Adiciona filtros na lateral direita
    list_filter = ('timestamp', 'user')
    
    # Define os campos que não podem ser editados
    readonly_fields = [field.name for field in AILog._meta.fields]

    def has_add_permission(self, request):
        # Impede a criação de logs manuais pelo admin
        return False

    def has_delete_permission(self, request, obj=None):
        # Impede a exclusão de logs pelo admin
        return False