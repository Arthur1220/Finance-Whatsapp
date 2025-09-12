import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum

from users.models import User
from expenses.models import Expense
from incomes.models import Income
from ai.services import AIService
from .models import MonthlySummary

logger = logging.getLogger(__name__)

def generate_or_get_monthly_summary(user: User, force_regenerate: bool = False) -> MonthlySummary:
    """
    Função principal que gera ou busca do cache um resumo mensal para o usuário.
    """
    now = timezone.now()
    month, year = now.month, now.year

    # 1. Lógica de Cache que você pediu
    expenses_qs = Expense.objects.filter(user=user, transaction_date__year=year, transaction_date__month=month)
    last_expense = Expense.objects.filter(user=user, transaction_date__year=year, transaction_date__month=month).order_by('-transaction_date').first()
    summary = MonthlySummary.objects.filter(user=user, month=month, year=year).first()

    if not force_regenerate and summary and last_expense and last_expense.transaction_date < summary.generated_at:
        logger.info(f"Retornando resumo do cache para o usuário {user.id} para {month}/{year}.")
        return summary

    # 2. Se não houver cache ou houver novos gastos, calcula tudo.
    logger.info(f"Gerando novo resumo para o usuário {user.id} para {month}/{year}.")

    total_income = Income.objects.filter(user=user, transaction_date__year=year, transaction_date__month=month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    balance = total_income - total_expenses

    summary_by_category = Expense.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    summary_by_payment = expenses_qs.values('payment_method__name').annotate(total=Sum('amount')).order_by('-total')

    # 3. Prepara os dados e chama a IA para gerar os insights.
    ai_service = AIService(user=user)
    insights_data = {
        "total_income": f"{total_income:.2f}",
        "total_expenses": f"{total_expenses:.2f}",
        "balance": f"{balance:.2f}",
        "categories": [
            {"name": item['category__name'], "total": f"{item['total']:.2f}"} 
            for item in summary_by_category
        ],
        "payment_methods": [
            {"name": item['payment_method__name'], "total": f"{item['total']:.2f}"}
            for item in summary_by_payment
        ]
    }
    insights_text = ai_service.generate_insight(insights_data) # (Precisaremos criar este método na AIService)

    # 4. Formata a mensagem final para o usuário.
    summary_text = _format_summary_message(month_name=now.strftime("%B").capitalize(), data=insights_data, insights=insights_text)

    # 5. Salva ou atualiza o resumo no banco.
    summary_obj, _ = MonthlySummary.objects.update_or_create(
        user=user, month=month, year=year,
        defaults={
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': balance,
            'summary_text': summary_text,
            'insights_text': insights_text
        }
    )
    return summary_obj

def _format_summary_message(month_name: str, data: dict, insights: str) -> str:
    """
    Formata os dados calculados e os insights da IA em uma única string para o WhatsApp.
    """
    # Converte os totais para Decimal para garantir os cálculos corretos
    total_income = Decimal(data.get('total_income', '0.00'))
    total_expenses = Decimal(data.get('total_expenses', '0.00'))
    balance = total_income - total_expenses
    
    # Calcula a porcentagem gasta de forma segura
    percent_spent = (total_expenses / total_income * 100) if total_income > 0 else 0

    # Monta a mensagem linha por linha
    response_lines = [
        f"📊 *Resumo Financeiro de {month_name}*\n",
        f"✅ *Total de Entradas:* R$ {total_income:.2f}",
        f"❌ *Total de Saídas:* R$ {total_expenses:.2f}",
        "---",
        f"⚖️ *Balanço do Mês:* R$ {balance:.2f}",
        f"📈 _Você gastou {percent_spent:.1f}% da sua renda este mês._\n"
    ]

    # Adiciona a quebra de gastos por categoria, se houver
    categories_summary = data.get('categories')
    if categories_summary:
        response_lines.append("➡️ *Principais Categorias de Gasto:*")
        for category_data in categories_summary:
            category_name = category_data.get('name', 'Sem Categoria')
            category_total = Decimal(category_data.get('total', '0.00'))
            response_lines.append(f"• {category_name}: R$ {category_total:.2f}")

    # Adiciona a quebra de gastos por forma de pagamento, se houver
    payment_summary = data.get('payment_methods')
    if payment_summary:
        response_lines.append("\n💳 *Gastos por Forma de Pagamento:*")
        for pm_data in payment_summary:
            pm_name = pm_data.get('name', 'N/A')
            pm_total = Decimal(pm_data.get('total', '0.00'))
            response_lines.append(f"• {pm_name}: R$ {pm_total:.2f}")

    # Adiciona o insight gerado pela IA
    if insights:
        response_lines.append(f"\n💡 *Análise do Fin:*")
        response_lines.append(f"_{insights}_")

    return "\n".join(response_lines)