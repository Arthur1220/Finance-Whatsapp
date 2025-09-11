from django.contrib import admin
from .models import Category, Expense

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name',)
    list_filter = ('user',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'user', 'amount', 'description', 'category')
    search_fields = ('description', 'user__username')
    list_filter = ('user', 'category', 'transaction_date')
    raw_id_fields = ('user', 'category')