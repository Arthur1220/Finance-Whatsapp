import logging
from users.models import User
from .models import PaymentMethod

logger = logging.getLogger(__name__)

DEFAULT_PAYMENT_METHODS = [
    {"name": "Crédito", "due_date": 10},
    {"name": "Débito"},
    {"name": "Pix"},
    {"name": "Dinheiro"},
]

def create_default_payment_methods_for_user(user: User):
    """
    Cria as formas de pagamento padrão para um usuário recém-criado
    e define a primeira como padrão.
    """
    created_methods = []
    for method_data in DEFAULT_PAYMENT_METHODS:
        method, created = PaymentMethod.objects.get_or_create(user=user, name=method_data['name'], defaults=method_data)
        if created:
            created_methods.append(method)
    
    # Define a primeira forma de pagamento da lista como a padrão do usuário
    if created_methods:
        user.default_payment_method = created_methods[0]
        user.save()
        
    logger.info(f"Formas de pagamento padrão criadas para o usuário {user.id}.")