import logging
import time
from typing import Optional
from pathlib import Path

from django.conf import settings
import google.generativeai as genai

from users.models import User
from meta.models import Message
from .models import AILog

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, user: User):
        self.user = user
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.critical(f"Falha ao configurar a API do Gemini: {e}")

    def get_ai_response(self, latest_message: Message) -> str:
        """
        Ponto de entrada principal para obter uma resposta da IA.
        """
        # 1. Carrega o prompt do arquivo.
        system_prompt = self._load_prompt_from_file('assistente_financeiro_v1')
        if not system_prompt:
            error_msg = "Prompt de sistema não encontrado. Não é possível gerar resposta."
            logger.error(error_msg)
            return "Desculpe, estou com um problema de configuração e não consigo responder agora."

        # 2. Busca o histórico de conversa.
        conversation_history = self._get_conversation_history(latest_message)

        # 3. Monta o prompt final.
        final_prompt = self._build_final_prompt(system_prompt, conversation_history)

        # 4. Chama a API do Gemini.
        ai_response_text = self._call_gemini_api(final_prompt)

        return ai_response_text

    def _load_prompt_from_file(self, prompt_name: str) -> Optional[str]:
        """
        Carrega o texto de um prompt a partir de um arquivo .txt na pasta /prompts.
        """
        try:
            # Constrói o caminho para o arquivo de forma segura
            file_path = Path(settings.BASE_DIR) / 'ai' / 'prompts' / f"{prompt_name}.txt"
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Arquivo de prompt não encontrado: {prompt_name}.txt")
            return None

    def _get_conversation_history(self, latest_message: Message, limit: int = 10) -> list[Message]:
        """
        Navega pela corrente de respostas para construir o histórico da conversa atual.
        """
        history = [latest_message]
        current_message = latest_message
        while current_message.replied_to and len(history) < limit:
            history.append(current_message.replied_to)
            current_message = current_message.replied_to
        return list(reversed(history))

    def _build_final_prompt(self, system_prompt: str, history: list[Message]) -> str:
        """
        Formata o histórico e o prompt do sistema no formato final para a IA.
        """
        formatted_history = "\n".join([
            f"{'user' if msg.direction == 'INBOUND' else 'model'}: {msg.body}"
            for msg in history
        ])
        # Adiciona informações do usuário ao prompt do sistema para personalização
        system_prompt_with_context = f"{system_prompt}\nInformações do usuário atual: Nome={self.user.first_name}, País={self.user.country_code}."

        final_prompt = f"{system_prompt_with_context}\n\n--- Histórico da Conversa ---\n{formatted_history}\nmodel:"
        logger.info(f"Prompt final criado para o usuário {self.user.id}")
        return final_prompt

    def _call_gemini_api(self, prompt: str) -> str:
        """
        Chama a API do Gemini, registra a interação e retorna a resposta em texto.
        """
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            start_time = time.time()
            response = model.generate_content(prompt)
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            AILog.objects.create(
                user=self.user,
                prompt_sent=prompt,
                response_received=response.text,
                duration_ms=duration_ms
            )
            logger.info(f"Chamada da API Gemini para o usuário {self.user.id} bem-sucedida. Duração: {duration_ms}ms.")
            return response.text
        except Exception as e:
            logger.error(f"Erro ao chamar a API Gemini para o usuário {self.user.id}: {e}", exc_info=True)
            return "Desculpe, não consegui processar sua solicitação no momento. Tente novamente mais tarde."