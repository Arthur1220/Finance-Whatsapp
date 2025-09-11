from django.contrib import admin
from .models import Income

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'user', 'amount', 'description', 'income_type')
    search_fields = ('description', 'user__username')
    list_filter = ('user', 'income_type', 'transaction_date')
    raw_id_fields = ('user',)