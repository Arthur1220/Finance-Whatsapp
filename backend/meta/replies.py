from typing import List
from django.utils import timezone
from django.db.models import Sum

from expenses.models import Category, Expense 
from users.models import User 
from incomes.models import Income 

# O dicionário com as respostas de texto fixas.
TEXT_REPLIES = {
    "pedir_ajuda": (
        "Com certeza! Eu sou o Fin, seu assistente para registro de despesas. Veja o que você pode fazer:\n\n"
        "1️⃣ *Registrar uma Despesa:*\nBasta me enviar uma mensagem no formato `VALOR DESCRIÇÃO`.\nExemplo: `25,50 almoço`\n\n"
        "2️⃣ *Ver Comandos:*\nEnvie `comandos` ou `ajuda` a qualquer momento.\n\n"
        "Posso te ajudar com mais alguma coisa? 😉"
    ),
    "pedir_comandos": (
        "Aqui estão os comandos que você pode usar:\n\n"
        "• `ajuda` ou `comandos`: Mostra esta mensagem de ajuda.\n"
        "• `categorias`: Explica como as categorias de despesas funcionam.\n"
        "• `saldo`: Consulta o saldo atual.\n"
        "• `extrato`: Mostra o extrato de despesas.\n"
        "• `resumo`: Fornece um resumo das despesas.\n\n"
        "Para registrar uma despesa, envie uma mensagem no formato: `VALOR DESCRIÇÃO` (ex: `15,90 padaria`)."
    ),
    "indefinido": "Desculpe, não entendi. Para registrar uma despesa, por favor, envie no formato: `VALOR DESCRIÇÃO` (ex: `15,90 padaria`). Se precisar de ajuda, é só mandar `ajuda`.",
    "saudacao_novo_usuario": (
        "Olá, {}! 👋 Bem-vindo(a) ao Finance-Whatsapp!\n\n"
        "Eu sou o Fin, e vou te ajudar a registrar suas despesas de forma rápida e fácil. Quer entender como funciono? Basta enviar uma mensagem como:\n\n"
        "*Me explique o que pode fazer com o Fin*"
    ),
    "saudacao": "Olá! Sou o Fin, seu assistente de despesas. Como posso te ajudar hoje? Para registrar um gasto, é só me enviar `VALOR DESCRIÇÃO`.",
    "agradecimento": "De nada! 😊 Se precisar de mais alguma coisa, é só chamar.",
    "despedida": "Até a próxima! 👋",
}

def get_user_categories_reply(user) -> str:
    """
    Busca as categorias de despesa de um usuário e formata uma resposta amigável.
    """
    # Busca todas as categorias associadas ao usuário, ordenadas pelo nome.
    categories = Category.objects.filter(user=user).order_by('name')

    if not categories:
        return "Você ainda não tem nenhuma categoria de despesa registrada."

    # Formata a lista de categorias em uma string bonita
    category_list_str = "\n".join([f"• {cat.name}" for cat in categories])

    response = (
        "Aqui estão suas categorias de despesa atuais:\n\n"
        f"{category_list_str}\n\n"
        "Quando você registra uma despesa, eu tento associá-la a uma dessas categorias automaticamente! 📊"
    )
    return response

def get_monthly_summary_reply(user: User) -> str:
    """
    Busca todas as rendas e despesas do usuário no mês corrente e formata um resumo completo.
    """
    now = timezone.now()
    month_name = now.strftime("%B").capitalize()
    
    # 1. Busca e soma as rendas do mês
    incomes = Income.objects.filter(user=user, transaction_date__year=now.year, transaction_date__month=now.month)
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 2. Busca e soma as despesas do mês
    expenses = Expense.objects.filter(user=user, transaction_date__year=now.year, transaction_date__month=now.month)
    total_expenses = expenses.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    # 3. Calcula o balanço e a porcentagem
    balance = total_income - total_expenses
    percent_spent = (total_expenses / total_income * 100) if total_income > 0 else 0
    
    # 4. Monta a mensagem de resposta
    response_lines = [
        f"📊 *Resumo Financeiro de {month_name}*\n",
        f"✅ *Total de Entradas:* R$ {total_income:.2f}",
        f"❌ *Total de Saídas:* R$ {total_expenses:.2f}",
        "---",
        f"⚖️ *Balanço:* R$ {balance:.2f}",
        f"📈 _Você gastou {percent_spent:.1f}% da sua renda este mês._\n"
    ]

    if expenses.exists():
        response_lines.append("➡️ *Principais Categorias de Gasto:*")
        summary_by_category = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')[:3]
        for category_summary in summary_by_category:
            category_name = category_summary['category__name'] or "Sem Categoria"
            category_total = category_summary['total']
            response_lines.append(f"• {category_name}: R$ {category_total:.2f}")

    return "\n".join(response_lines)