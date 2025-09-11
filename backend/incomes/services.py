import logging
from decimal import Decimal
from users.models import User
from .models import Income

logger = logging.getLogger(__name__)

def create_income_from_ai_plan(user: User, ai_plan: dict) -> Income | None:
    """
    Cria e salva um novo registro de renda a partir do plano da IA.
    """
    amount = ai_plan.get("amount")
    description = ai_plan.get("description")
    income_type = ai_plan.get("income_type", "VARIAVEL").upper() # Padrão para VARIÁVEL se não especificado

    if not (amount and description):
        return None

    income = Income.objects.create(
        user=user,
        amount=Decimal(amount),
        description=description,
        income_type=income_type if income_type in ['FIXA', 'VARIAVEL'] else 'VARIAVEL'
    )
    logger.info(f"Nova renda registrada para o usuário {user.id}: R${amount} de '{description}'")
    return income