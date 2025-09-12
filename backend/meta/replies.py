from typing import List
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from expenses.models import Category, Expense 
from users.models import User 
from incomes.models import Income 

# O dicionário com as respostas de texto fixas.
TEXT_REPLIES = {
    "pedir_ajuda": (
        "Olá! Eu sou o Fin, seu assistente financeiro. Minha principal função é te ajudar a registrar suas finanças de forma simples. Veja como posso te ajudar:\n\n"
        "*🎯 Para Organizar seus Gastos:*\n"
        "A qualquer momento, me envie uma mensagem com um valor e uma descrição, e eu registro para você! Eu tento entender o que você escreve, por exemplo:\n"
        "  - `15,50 almoço no trabalho`\n"
        "  - `recebi 1200 de um freela`\n"
        "  - `paguei 350 no aluguel com pix`\n\n"
        "*✍️ Para Gerenciar seus Dados:*\n"
        "Cometeu um erro? É fácil de corrigir!\n"
        "  - `editar ultima 16,00 café da manhã`\n"
        "  - `apagar ultima despesa`\n"
        "  - `mudar categoria do ultimo para Lazer`\n\n"
        "*📊 Para Ver seus Relatórios:*\n"
        "Quer saber como andam suas finanças?\n"
        "  - `resumo do mês`\n\n"
        "Se quiser uma lista rápida de todos os comandos, é só me enviar a palavra `comandos`. 😉"
    ),
    "pedir_comandos": (
        "Aqui está a lista de comandos que eu entendo:\n\n"
        "*Registros:*\n"
        "• `[VALOR] [DESCRIÇÃO] [FORMA DE PAGAMENTO (opcional)]` - Registra uma despesa.\n"
        "• `recebi [VALOR] de [DESCRIÇÃO] [fixo/variavel (opcional)]` - Registra uma renda.\n\n"
        "*Gerenciamento do Último Registro:*\n"
        "• `editar ultima [NOVO VALOR] [NOVA DESCRIÇÃO]`\n"
        "• `apagar ultima` ou `deletar ultima`\n"
        "• `mudar categoria para [NOME DA CATEGORIA]`\n\n"
        "*Gerenciamento de Categorias:*\n"
        "• `criar categoria [NOME]`\n"
        "• `apagar categoria [NOME]`\n"
        "• `minhas categorias`\n\n"
        "*Relatórios:*\n"
        "• `resumo do mês`\n"
        "• `extrato`\n"
        "• `saldo`"
    ),
    "indefinido": (
        "Desculpe, não entendi o que você quis dizer. 🤔\n\n"
        "Lembre-se que posso registrar despesas e rendas. Se precisar de ajuda com os comandos, é só me enviar a palavra `ajuda`."
    ),
    "saudacao_novo_usuario": (
        "Olá, {}! 👋 Bem-vindo(a) ao Finance-Whatsapp!\n\n"
        "Eu sou o Fin, seu assistente financeiro pessoal. Minha missão é te ajudar a organizar suas finanças de forma simples, diretamente pelo WhatsApp.\n\n"
        "Para começar, que tal registrar sua primeira despesa? É só me enviar uma mensagem como:\n\n"
        "*15,50 almoço no restaurante*\n\n"
        "A qualquer momento, me envie `ajuda` para ver tudo que posso fazer!"
    ),
    "saudacao": "Olá, {}! 👋 Como posso te ajudar com suas finanças hoje?",
    "agradecimento": "De nada! 😊 Se precisar de mais alguma coisa, é só chamar.",
    "despedida": "Até mais! Se precisar de algo, estarei por aqui. 👋",
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
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

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