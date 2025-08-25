from django.db import models
from django.conf import settings
import uuid

class AILog(models.Model):
    """
    Registra cada interação com a API da IA para depuração, análise e custos.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Vincula o log ao usuário que interagiu
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    # O prompt completo que foi enviado para a API da IA
    prompt_sent = models.TextField()
    # A resposta exata que a IA retornou
    response_received = models.TextField()
    # Métricas de performance e custo (opcionais)
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    duration_ms = models.PositiveIntegerField(help_text="Duração da chamada da API em milissegundos.")
    # Timestamp de quando a interação ocorreu
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Log for {self.user} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']