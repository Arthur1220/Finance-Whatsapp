# backend/expenses/services.py
import logging
from decimal import Decimal
from typing import Optional

from users.models import User
from .models import Expense, Category
from payments.models import PaymentMethod

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

    logger.info(f"Standard categories created for user {user.id}")

def create_expense_from_ai_plan(user: User, ai_plan: dict) -> Expense | None:
    """
    Cria e salva um novo registro de despesa a partir do plano da IA.
    """
    amount = ai_plan.get("amount")
    description = ai_plan.get("description")
    category_name = ai_plan.get("category")
    payment_method_name = ai_plan.get("payment_method")
    payment_method = None

    if not (amount and description and category_name):
        return None

    if payment_method_name:
        # Busca ou cria a forma de pagamento pelo nome extraído
        payment_method, _ = PaymentMethod.objects.get_or_create(user=user, name=payment_method_name.capitalize())
    else:
        # Se a IA não extraiu, usa a padrão do usuário
        payment_method = user.default_payment_method

    # Busca a categoria específica do usuário pelo nome retornado pela IA.
    category, _ = Category.objects.get_or_create(user=user, name=category_name)
    
    expense = Expense.objects.create(
        user=user,
        amount=Decimal(amount),
        description=description,
        category=category,
        payment_method=payment_method
    )
    logger.info(f"New expense registered for user {user.id}: R${amount} in '{description}' (Cat: {category.name})")
    return expense

def delete_last_expense(user: User) -> Optional[Expense]:
    """
    Encontra e apaga a última despesa registrada por um usuário.
    Retorna o objeto da despesa apagada, ou None se nenhuma for encontrada.
    """
    last_expense = Expense.objects.filter(user=user).order_by('-transaction_date').first()
    
    if last_expense:
        logger.info(f"Deleting the last expense (ID: {last_expense.id}) for user {user.id}.")
        last_expense.delete()
        return last_expense

    logger.warning(f"Attempted to delete, but no expense was found for user {user.id}.")
    return None

def edit_last_expense(user: User, ai_plan: dict) -> Optional[Expense]:
    """
    Encontra e edita a última despesa registrada com os novos dados do plano da IA.
    Permite edições parciais (apenas valor, apenas descrição, ou ambos).
    """
    try:
        last_expense = Expense.objects.filter(user=user).latest('transaction_date')
    except Expense.DoesNotExist:
        logger.warning(f"Attempted to edit, but no expense was found for user {user.id}.")
        return None

    new_amount = ai_plan.get("amount")
    new_description = ai_plan.get("description")

    if not new_amount and not new_description:
        logger.warning(f"Attempted to edit expense {last_expense.id}, but no new data was provided.")
        return None

    fields_to_update = []
    if new_amount:
        last_expense.amount = Decimal(new_amount)
        fields_to_update.append('amount')
    
    if new_description:
        last_expense.description = new_description
        fields_to_update.append('description')
    
    last_expense.save(update_fields=fields_to_update)

    logger.info(f"Expense (ID: {last_expense.id}) successfully edited for user {user.id}. Updated fields: {fields_to_update}")
    return last_expense

def change_last_expense_category(user: User, ai_plan: dict) -> Optional[Expense]:
    """
    Encontra a última despesa e altera sua categoria para a nova categoria fornecida pelo plano da IA.
    Se a categoria não existir para o usuário, ela é criada.
    """
    new_category_name = ai_plan.get("category")
    if not new_category_name:
        logger.warning(f"Attempted to change category, but no new category name was provided.")
        return None

    try:
        last_expense = Expense.objects.filter(user=user).latest('transaction_date')
    except Expense.DoesNotExist:
        logger.warning(f"Attempted to change category, but no expense was found for user {user.id}.")
        return None
    
    # Capitaliza o nome da categoria para manter um padrão (ex: "lazer" -> "Lazer")
    new_category_name = new_category_name.capitalize()

    # Busca a categoria pelo nome. Se não existir para este usuário, cria uma nova.
    new_category, created = Category.objects.get_or_create(
        user=user, 
        name=new_category_name
    )
    if created:
        logger.info(f"New category '{new_category_name}' created for user {user.id}.")

    # Atribui a nova categoria e salva a alteração.
    last_expense.category = new_category
    last_expense.save(update_fields=['category'])

    logger.info(f"Category of expense (ID: {last_expense.id}) changed to '{new_category_name}' for user {user.id}.")
    return last_expense

def create_new_category(user: User, ai_plan: dict) -> tuple[Optional[Category], bool]:
    """
    Cria uma nova categoria de despesa para o usuário.
    Retorna a categoria e um booleano indicando se foi criada.
    """
    category_name = ai_plan.get("category")
    if not category_name:
        return None, False

    # Capitaliza o nome para manter um padrão
    category_name = category_name.capitalize()
    
    category, created = Category.objects.get_or_create(
        user=user,
        name__iexact=category_name, # __iexact busca ignorando maiúsculas/minúsculas
        defaults={'name': category_name}
    )
    
    if created:
        logger.info(f"Nova categoria '{category_name}' criada para o usuário {user.id}.")
    else:
        logger.info(f"Categoria '{category_name}' já existia para o usuário {user.id}.")

    return category, created

def delete_category_by_name(user: User, ai_plan: dict) -> bool:
    """
    Deleta uma categoria de despesa pelo nome.
    Despesas que pertenciam a esta categoria são movidas para "Outros".
    Retorna True se a categoria foi deletada, False caso contrário.
    """
    category_name = ai_plan.get("category")
    if not category_name:
        return False

    try:
        # Busca a categoria para deletar, ignorando maiúsculas/minúsculas
        category_to_delete = Category.objects.get(user=user, name__iexact=category_name)
        
        # Garante que a categoria "Outros" exista antes de mover as despesas
        other_category, _ = Category.objects.get_or_create(user=user, name="Outros")

        # Move todas as despesas da categoria antiga para "Outros"
        Expense.objects.filter(category=category_to_delete).update(category=other_category)
        
        # Deleta a categoria
        category_to_delete.delete()
        logger.info(f"Categoria '{category_name}' deletada para o usuário {user.id}. Despesas movidas para 'Outros'.")
        return True

    except Category.DoesNotExist:
        logger.warning(f"Tentativa de deletar categoria '{category_name}' que não existe para o usuário {user.id}.")
        return False