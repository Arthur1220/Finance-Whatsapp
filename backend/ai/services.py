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
    """
    Serviço responsável por analisar o texto das mensagens dos usuários.
    Sua principal função é interpretar a intenção do usuário e extrair dados,
    atuando como um filtro inteligente antes de qualquer ação do sistema.
    """
    def __init__(self, user: User):
        self.user = user
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.critical(f"Falha ao configurar a API do Gemini: {e}")

    def interpret_message(self, message_text: str) -> Dict:
        """
        Usa a IA para interpretar a intenção do usuário e extrair dados, retornando um JSON.
        """
        system_prompt = self._load_prompt_from_file('interprete_de_comandos_v1')
        if not system_prompt:
            return {"intent": "indefinido"}

        final_prompt = f"{system_prompt}\n\nTexto do usuário: {message_text}\nSua saída:"
        
        response_str = self._call_gemini_api(final_prompt)
        logger.info(f"--- RESPOSTA BRUTA DA IA ---\n{response_str}\n-----------------------------")
        
        try:
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            raise json.JSONDecodeError
        except (json.JSONDecodeError, AttributeError):
            logger.error(f"Failed to parse JSON from AI response for user {self.user.id}. Raw: '{response_str}'")
            return {"intent": "indefinido"}

    def _load_prompt_from_file(self, prompt_name: str) -> Optional[str]:
        """
        Carrega o conteúdo de um arquivo de prompt localizado na pasta 'ai/prompts'.
        """
        try:
            file_path = Path(settings.BASE_DIR) / 'ai' / 'prompts' / f"{prompt_name}.txt"
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_name}.txt")
            return None

    def _call_gemini_api(self, prompt: str) -> str:
        """
        Chama a API Gemini com o prompt fornecido e retorna a resposta como string.
        """
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            start_time = time.time()
            response = model.generate_content(prompt)
            end_time = time.time()
            duration_ms = max(0, int((end_time - start_time) * 1000))
            # Criamos o log aqui para registrar toda e qualquer chamada à IA
            AILog.objects.create(
                user=self.user, 
                prompt_sent=prompt, 
                response_received=response.text, 
                duration_ms=duration_ms
            )

            logger.info(f"Main AI call for user {self.user.id} successful. Duration: {duration_ms}ms.")
            return response.text
        except Exception:
            logger.error(f"Error calling Gemini API for user {self.user.id}.", exc_info=True)
            return "{}" # Retorna um JSON vazio em caso de erro