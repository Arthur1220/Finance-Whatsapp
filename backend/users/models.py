import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords
from payments.models import PaymentMethod

class User(AbstractUser):
    """
    Modelo de usuário customizado que substitui o padrão do Django.
    Herda de AbstractUser para manter toda a estrutura de autenticação do Django.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    # Código de país ISO 3166-1 alfa-2 (ex: 'BR', 'US').
    country_code = models.CharField(max_length=2, null=True, blank=True)

    default_payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_users')

    # Histórico de alterações
    history = HistoricalRecords()
    
    def __str__(self):
        return self.username