import uuid
from django.db import models
from django.conf import settings

class Income(models.Model):
    INCOME_TYPE_CHOICES = [
        ('FIXA', 'Fixa'),
        ('VARIAVEL', 'Variável'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incomes')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da entrada")
    description = models.CharField(max_length=255, help_text="Descrição da entrada (ex: Salário, Freelance)")
    income_type = models.CharField(max_length=10, choices=INCOME_TYPE_CHOICES, default='VARIAVEL')
    transaction_date = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"R${self.amount} - {self.description} ({self.get_income_type_display()})"

    class Meta:
        ordering = ['-transaction_date']