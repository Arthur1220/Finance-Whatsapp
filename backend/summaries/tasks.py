from celery import shared_task
from users.models import User
from .services import generate_or_get_monthly_summary

@shared_task
def generate_monthly_summaries_for_all_users():
    """
    Tarefa periódica que gera o resumo do mês para todos os usuários ativos.
    """
    for user in User.objects.filter(is_active=True):
        generate_or_get_monthly_summary(user, force_regenerate=True)