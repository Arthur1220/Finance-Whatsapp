import logging
from celery import shared_task
from . import services

# Boa prática: inicializar o logger para este módulo.
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_webhook_payload(self, payload: dict):
    """
    Tarefa assíncrona do Celery que recebe o payload completo do webhook da Meta e o delega para a camada de serviço para processamento em segundo plano.

    O `bind=True` nos dá acesso à instância da tarefa (`self`), permitindo obter informações como o ID da tarefa para logs mais detalhados.
    """
    task_id = self.request.id
    logger.info(f"Task {task_id}: Starting webhook payload processing.")

    try:
        # A lógica de negócio é delegada para a camada de serviço.
        # Isso mantém a tarefa simples e focada em sua responsabilidade: gerenciar a execução.
        services.process_webhook_message(payload)
        
        logger.info(f"Task {task_id}: Successfully processed by the service layer.")
        return f"Task {task_id}: Payload processed successfully."

    except Exception as e:
        # Captura qualquer exceção inesperada que possa ocorrer na camada de serviço.
        logger.error(
            f"Task {task_id}: An unexpected error occurred during processing.",
            exc_info=True  # Inclui o traceback completo do erro no log para depuração.
        )
        # Re-lança a exceção para que o Celery marque a tarefa como 'FAILURE'.
        # Isso é importante para monitoramento e possíveis novas tentativas (retries).
        raise e