import uuid
from django.db import models
from django.conf import settings

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Garante que um usuário não possa ter duas categorias com o mesmo nome
        unique_together = ('user', 'name')
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da despesa")
    description = models.CharField(max_length=255, help_text="Descrição da despesa")
    transaction_date = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"R${self.amount} - {self.description}"

    class Meta:
        ordering = ['-transaction_date']