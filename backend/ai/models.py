from django.db import models
from django.conf import settings
import uuid

class AILog(models.Model):
    """
    Registra cada interação com a API da IA para depuração, análise e custos.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    prompt_sent = models.TextField()
    response_received = models.TextField()
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    duration_ms = models.PositiveIntegerField(help_text="Duração da chamada da API em milissegundos.")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Log for {self.user} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']