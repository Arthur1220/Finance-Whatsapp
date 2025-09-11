from typing import List
from django.utils import timezone
from django.db.models import Sum

from expenses.models import Category, Expense 
from users.models import User 

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
        "• `saldo`: Consulta o saldo atual (em breve).\n"
        "• `extrato`: Mostra o extrato de despesas (em breve).\n"
        "• `resumo`: Fornece um resumo das despesas (em breve).\n\n"
        "Para registrar uma despesa, envie uma mensagem no formato: `VALOR DESCRIÇÃO` (ex: `15,90 padaria`)."
    ),
    #"pedir_saldo": "A funcionalidade de consulta de saldo ainda está em desenvolvimento. Logo teremos novidades! 🚀",
    #"pedir_extrato": "A funcionalidade de extrato ainda está em desenvolvimento. Logo teremos novidades! 🚀",
    #"pedir_resumo": "A funcionalidade de resumo ainda está em desenvolvimento. Logo teremos novidades! 🚀",
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
    Busca todas as despesas do usuário no mês corrente, calcula os totais
    e formata uma mensagem de resumo.
    """
    # Pega o primeiro dia do mês e ano atuais
    now = timezone.now()
    
    # 1. Busca todas as despesas do usuário no mês e ano atuais.
    expenses = Expense.objects.filter(
        user=user,
        transaction_date__year=now.year,
        transaction_date__month=now.month
    )

    if not expenses.exists():
        return "Você ainda não registrou nenhuma despesa este mês. Para começar, envie `VALOR DESCRIÇÃO`! 😉"

    # 2. Calcula o total gasto no mês.
    total_spent = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # 3. Calcula o total gasto por categoria.
    summary_by_category = expenses.values(
        'category__name' # Agrupa pelo nome da categoria
    ).annotate(
        total_per_category=Sum('amount') # Soma os valores para cada grupo
    ).order_by(
        '-total_per_category' # Ordena da categoria mais cara para a mais barata
    )

    # 4. Monta a mensagem de resposta.
    month_name = now.strftime("%B").capitalize() # Pega o nome do mês em português
    response_lines = [
        f"📊 *Resumo de Despesas de {month_name}*\n",
        f"💰 *Total Gasto:* R$ {total_spent:.2f}\n",
        "➡️ *Gastos por Categoria:*",
    ]

    for category_summary in summary_by_category:
        category_name = category_summary['category__name'] or "Sem Categoria"
        category_total = category_summary['total_per_category']
        response_lines.append(f"• {category_name}: R$ {category_total:.2f}")

    return "\n".join(response_lines)