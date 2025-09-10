import logging
import time
import json
import re
from typing import Optional, Dict
from pathlib import Path

from django.conf import settings
import google.generativeai as genai

from users.models import User
from .models import AILog

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, user: User):
        self.user = user
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.critical(f"Falha ao configurar a API do Gemini: {e}")

    def extract_expense_data(self, message_text: str) -> Dict:
        """
        Usa a IA para extrair dados de despesa (valor e descrição) de uma string de texto.
        """
        system_prompt = self._load_prompt_from_file('extrator_de_despesas_v1')
        if not system_prompt:
            return {"amount": None, "description": None}

        # Para extração, não precisamos de um histórico longo, apenas o texto da mensagem.
        final_prompt = f"{system_prompt}\n\nTexto do usuário: {message_text}\nSua saída:"
        
        response_str = self._call_gemini_api(final_prompt)
        
        try:
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group(0))
                logger.info(f"Dados extraídos para o usuário {self.user.id}: {extracted_data}")
                return extracted_data
            else:
                raise json.JSONDecodeError("Nenhum JSON encontrado na resposta da IA.")
        except (json.JSONDecodeError, AttributeError):
            logger.error(f"Falha ao parsear JSON de extração para o usuário {self.user.id}. Raw: '{response_str}'")
            return {"amount": None, "description": None}
    
    def _load_prompt_from_file(self, prompt_name: str) -> Optional[str]:
        try:
            file_path = Path(settings.BASE_DIR) / 'ai' / 'prompts' / f"{prompt_name}.txt"
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Arquivo de prompt não encontrado: {prompt_name}.txt")
            return None

    def _call_gemini_api(self, prompt: str) -> str:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            # Logamos a interação aqui, pois é a única chamada
            AILog.objects.create(
                user=self.user, prompt_sent=prompt, response_received=response.text, duration_ms=0
            )
            return response.text
        except Exception as e:
            logger.error(f"Erro ao chamar a API Gemini para o usuário {self.user.id}: {e}", exc_info=True)
            return "{}" # Retorna um JSON vazio em caso de erro na API
        """
        Cria uma resposta de fallback segura caso a IA falhe ou não retorne um JSON válido.
        """
        return {
            "user_intent": "fallback",
            "response_text": text, # Para o caso da IA retornar texto em vez de JSON
            "conversation_action": "CONTINUE_CONVERSATION"
        }