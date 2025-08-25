import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords

class User(AbstractUser):
    """
    Modelo de usuário customizado que substitui o padrão do Django.
    Herda de AbstractUser para manter toda a estrutura de autenticação do Django.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    # Código de país ISO 3166-1 alfa-2 (ex: 'BR', 'US').
    country_code = models.CharField(max_length=2, null=True, blank=True)

    # Histórico de alterações
    history = HistoricalRecords()
    
    def __str__(self):
        return self.username