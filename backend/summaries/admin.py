from django.contrib import admin
from .models import MonthlySummary

@admin.register(MonthlySummary)
class MonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'total_income', 'total_expenses', 'balance', 'generated_at')
    list_filter = ('user', 'year', 'month')