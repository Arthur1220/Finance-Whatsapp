# backend/expenses/services.py
import logging
from decimal import Decimal
from users.models import User
from .models import Expense, Category

logger = logging.getLogger(__name__)

# Lista de categorias padrão que todo novo usuário receberá.
DEFAULT_CATEGORY_NAMES = [
    "Alimentação",
    "Transporte",
    "Moradia",
    "Lazer",
    "Compras",
    "Saúde",
    "Educação",
    "Outros",
]

def create_default_categories_for_user(user: User):
    """
    Cria as categorias padrão para um usuário recém-criado.
    """
    for category_name in DEFAULT_CATEGORY_NAMES:
        Category.objects.get_or_create(user=user, name=category_name)

    logger.info(f"Categorias padrão criadas para o novo usuário {user.id}")

def create_expense_from_ai_plan(user: User, ai_plan: dict) -> Expense | None:
    """
    Cria e salva um novo registro de despesa a partir do plano da IA.
    """
    amount = ai_plan.get("amount")
    description = ai_plan.get("description")
    category_name = ai_plan.get("category")

    if not (amount and description and category_name):
        return None

    # Busca a categoria específica do usuário pelo nome retornado pela IA.
    category, _ = Category.objects.get_or_create(user=user, name=category_name)
    
    expense = Expense.objects.create(
        user=user,
        amount=Decimal(amount),
        description=description,
        category=category
    )
    logger.info(f"Nova despesa registrada para o usuário {user.id}: R${amount} em '{description}' (Cat: {category.name})")
    return expense