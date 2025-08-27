import logging
import time
import json
import re
from typing import Optional, Dict, List
from pathlib import Path

from django.conf import settings
import google.generativeai as genai

from users.models import User
from meta.models import Message, Conversation
from .models import AILog

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, user: User, conversation: Conversation):
        self.user = user
        self.conversation = conversation
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.critical(f"Falha ao configurar a API do Gemini: {e}")

    def get_ai_plan(self) -> Dict:
        """
        Orquestra o processo de IA: classifica a intenção e depois gera a resposta.
        """
        history = self._get_conversation_history()
        
        # --- ETAPA 1: CLASSIFICAR A INTENÇÃO ---
        logger.info(f"--- Etapa 1: Classificando a intenção para o usuário {self.user.id} ---")
        intent_prompt_text = self._load_prompt_from_file('classificador_de_intencao_v1')
        final_intent_prompt = self._build_final_prompt(intent_prompt_text, history)
        
        logger.info(f"--- PROMPT ENVIADO PARA O CLASSIFICADOR ---\n{final_intent_prompt}\n-----------------------------------------")
        intent_json_str = self._call_gemini_api("classificador", final_intent_prompt, log_it=False)
        logger.info(f"--- RESPOSTA BRUTA DO CLASSIFICADOR ---\n{intent_json_str}\n---------------------------------------")
        
        try:
            json_match = re.search(r'\{.*\}', intent_json_str, re.DOTALL)
            json_str = json_match.group(0) if json_match else "{}"
            intent_data = json.loads(json_str)
            user_intent = intent_data.get("user_intent", "indefinido")
            logger.info(f"AI classified intent for user {self.user.id} as '{user_intent}'")
        except (json.JSONDecodeError, AttributeError):
            user_intent = "indefinido"
            logger.error(f"Failed to parse intent JSON from AI for user {self.user.id}. Raw: '{intent_json_str}'")

        # --- ETAPA 2: GERAR A RESPOSTA DE TEXTO ---
        logger.info(f"--- Etapa 2: Gerando texto com a intenção '{user_intent}' ---")
        writer_prompt_text = self._load_prompt_from_file('redator_conversacional_v1')
        context_for_writer = f"\nContexto Adicional: A intenção do usuário foi classificada como '{user_intent}'. Formule sua resposta de acordo."
        writer_system_prompt = writer_prompt_text + context_for_writer
        
        final_writer_prompt = self._build_final_prompt(writer_system_prompt, history)
        response_text = self._call_gemini_api("redator", final_writer_prompt, log_it=True)

        # --- ETAPA 3: DEFINIR A AÇÃO DA CONVERSA ---
        conversation_action = "END_CONVERSATION" if user_intent == "despedida" else "CONTINUE_CONVERSATION"

        return {
            "user_intent": user_intent,
            "response_text": response_text,
            "conversation_action": conversation_action
        }

    def _get_conversation_history(self, limit: int = 20) -> List[Message]:
        """
        Busca as últimas mensagens da conversa ATUAL, em ordem cronológica.
        """
        # 1. Busca as mensagens da conversa ordenando pela mais RECENTE primeiro.
        # 2. Aplica o limite para pegar apenas as X últimas.
        # 3. A lista resultante (recent_history) estará em ordem REVERSA (nova -> antiga).
        recent_history = self.conversation.messages.order_by('-timestamp')[:limit]
        
        # 4. Inverte a lista para que a ordem fique correta (antiga -> nova) para a IA.
        return list(reversed(recent_history))

    def _load_prompt_from_file(self, prompt_name: str) -> Optional[str]:
        """
        Carrega o texto de um prompt a partir de um arquivo .txt na pasta /prompts.
        """
        try:
            file_path = Path(settings.BASE_DIR) / 'ai' / 'prompts' / f"{prompt_name}.txt"
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Arquivo de prompt não encontrado: {prompt_name}.txt")
            return None

    def _build_final_prompt(self, system_prompt: str, history: List[Message]) -> str:
        """
        Formata o histórico e o prompt do sistema no formato final para a IA,
        incluindo as respostas do 'model'.
        """
        # Agora o 'history' que chega aqui está na ordem cronológica correta
        formatted_history = "\n".join([
            f"{'user' if msg.direction == 'INBOUND' else 'model'}: {msg.body}"
            for msg in history if msg.body # Garante que não adicionemos linhas vazias
        ])
        
        system_prompt_with_context = f"{system_prompt}\nInformações do usuário atual: Nome={self.user.first_name or 'não informado'}."
        final_prompt = f"{system_prompt_with_context}\n\n--- Histórico da Conversa ---\n{formatted_history}\nmodel:"
        return final_prompt
    
    def _call_gemini_api(self, prompt_type: str, prompt: str, log_it: bool = True) -> str:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            start_time = time.time()
            response = model.generate_content(prompt)
            end_time = time.time()
            duration_ms = max(0, int((end_time - start_time) * 1000))

            if log_it:
                AILog.objects.create(
                    user=self.user, 
                    prompt_sent=prompt,
                    response_received=response.text, 
                    duration_ms=duration_ms
                )
                logger.info(f"Main AI call for user {self.user.id} successful. Duration: {duration_ms}ms.")

            # Limpeza básica para garantir que a resposta não venha com markdown de JSON
            cleaned_text = re.sub(r'```json\s*|\s*```', '', response.text).strip()
            return cleaned_text
        except Exception as e:
            logger.error(f"Error calling Gemini API for user {self.user.id} (prompt_type: {prompt_type}): {e}", exc_info=True)
            return "Desculpe, não consegui processar sua solicitação no momento."
    
    
    def _get_fallback_response(self, text: str) -> dict:
        """
        Cria uma resposta de fallback segura caso a IA falhe ou não retorne um JSON válido.
        """
        return {
            "user_intent": "fallback",
            "response_text": text, # Para o caso da IA retornar texto em vez de JSON
            "conversation_action": "CONTINUE_CONVERSATION"
        }