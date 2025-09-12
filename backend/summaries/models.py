import uuid
from django.db import models
from django.conf import settings

class MonthlySummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='summaries')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()

    # Dados calculados
    total_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Textos gerados pela IA
    summary_text = models.TextField(help_text="O texto completo do resumo formatado para o usuário.")
    insights_text = models.TextField(help_text="Os insights e dicas gerados pela IA.")

    # Controle de cache
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month', 'year') # Garante um único resumo por mês para cada usuário
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Resumo para {self.user.username} - {self.month}/{self.year}"