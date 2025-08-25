from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class UserAdmin(UserAdmin):
    """
    Configuração para exibir o modelo User customizado no painel de Admin.
    Herda de UserAdmin para manter a interface padrão de gerenciamento de usuários.
    """
    pass