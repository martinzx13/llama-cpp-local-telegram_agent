from openai import AsyncOpenAI
from typing import Dict, Any, List, Optional
from bot.config import get_settings
import json
import logging

logger = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self):
        self.config = get_settings()
        self.local_client = AsyncOpenAI(
            base_url=self.config.llm.base_url,
            api_key="local",
        )
        self.cloud_clients = {}
        if self.config.deepseek_api_key:
            self.cloud_clients["deepseek"] = AsyncOpenAI(
                base_url="https://api.deepseek.com/v1",
                api_key=self.config.deepseek_api_key,
            )
        if self.config.openai_api_key:
            self.cloud_clients["openai"] = AsyncOpenAI(
                base_url="https://api.openai.com/v1",
                api_key=self.config.openai_api_key,
            )

    async def parse_intent(self, text: str, user_role: str, skills: List[str]) -> Dict[str, Any]:
        system_prompt = self._build_intent_prompt(skills, user_role)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        try:
            return await self._try_local(messages)
        except Exception as e:
            logger.warning(f"Local LLM failed: {e}, trying cloud")
            return await self._try_cloud(messages)

    async def _try_local(self, messages: List[Dict]) -> Dict[str, Any]:
        response = await self.local_client.chat.completions.create(
            model=self.config.llm.model,
            messages=messages,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            timeout=self.config.llm.timeout,
        )
        content = response.choices[0].message.content
        return self._parse_json_response(content)

    async def _try_cloud(self, messages: List[Dict]) -> Dict[str, Any]:
        for provider in self.config.routing.cloud_priority:
            if provider["provider"] not in self.cloud_clients:
                continue
            client = self.cloud_clients[provider["provider"]]
            try:
                response = await client.chat.completions.create(
                    model=provider["model"],
                    messages=messages,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                    timeout=self.config.llm.timeout,
                )
                content = response.choices[0].message.content
                return self._parse_json_response(content)
            except Exception as e:
                logger.warning(f"Cloud {provider['provider']} failed: {e}")
                continue
        raise RuntimeError("All LLM backends failed")

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        return {
            "intent": "unknown",
            "args": {},
            "confidence": "LOW",
            "reasoning": "Failed to parse LLM response",
        }

    def _build_intent_prompt(self, skills: List[str], user_role: str) -> str:
        skill_descriptions = {
            "certificados": "Generar certificados (laboral, tiempos, salario). Requiere PIN para salario.",
            "vacaciones": "Solicitar vacaciones, ver saldo, cancelar. Líder aprueba/rechaza.",
            "consulta": "Ver saldo vacaciones, horario semanal, perfil, equipo (líder), certificados mes (RRHH).",
        }
        desc = "\n".join(f"- {s}: {skill_descriptions.get(s, '')}" for s in skills)
        return (
            f"Eres el router de intenciones para un asistente de RRHH de una clínica colombiana.\n"
            f"Rol del usuario: {user_role}\n"
            f"Habilidades disponibles:\n{desc}\n\n"
            f"Clasifica el mensaje del usuario en UNA intención y extrae argumentos.\n"
            f"Responde SOLO con JSON válido:\n"
            f'{{"intent": "nombre_intencion", "args": {{...}}, "confidence": "HIGH|MEDIUM|LOW", "reasoning": "..."}}'
        )

    async def generate_response(self, prompt: str, system: str = "", use_cloud: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if use_cloud:
            return await self._try_cloud(messages)
        try:
            response = await self.local_client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
                timeout=self.config.llm.timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Local generation failed: {e}")
            return await self._try_cloud(messages)