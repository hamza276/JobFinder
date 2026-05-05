"""
LLM Provider abstraction layer.
Never import Groq/Anthropic SDKs directly outside this package.
"""
from abc import ABC, abstractmethod
import json
import logging

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class BaseLLMProvider(ABC):

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> str:
        """Simple text completion. Returns string."""
        pass

    @abstractmethod
    async def complete_json(self, prompt: str, system: str = "", schema: dict = None) -> dict:
        """JSON completion. Returns parsed dict. Raises LLMError if invalid JSON."""
        pass


class GroqProvider(BaseLLMProvider):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        from groq import AsyncGroq
        from app.core.config import settings
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = model or "llama-3.3-70b-versatile"

    async def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await self.client.chat.completions.create(
                model=self.model, messages=messages, timeout=30
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise LLMError(f"Groq error: {e}") from e

    async def complete_json(self, prompt: str, system: str = "", schema: dict = None) -> dict:
        json_system = (system + "\nAlways respond with valid JSON only. No markdown, no backticks.").strip()
        text = await self.complete(prompt, json_system)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM returned invalid JSON: {text[:200]}") from e


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, model: str = "claude-opus-4-5"):
        import anthropic
        from app.core.config import settings
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or "claude-opus-4-5"

    async def complete(self, prompt: str, system: str = "") -> str:
        try:
            kwargs = {"model": self.model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
            if system:
                kwargs["system"] = system
            msg = await self.client.messages.create(**kwargs)
            return msg.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic error: {e}") from e

    async def complete_json(self, prompt: str, system: str = "", schema: dict = None) -> dict:
        json_system = (system + "\nAlways respond with valid JSON only. No markdown, no backticks.").strip()
        text = await self.complete(prompt, json_system)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM returned invalid JSON: {text[:200]}") from e


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "llama3.1"):
        import httpx
        from app.core.config import settings
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = model or "llama3.1"
        self.client = httpx.AsyncClient(timeout=60)

    async def complete(self, prompt: str, system: str = "") -> str:
        payload = {
            "model": self.model,
            "prompt": f"{system}\n\n{prompt}" if system else prompt,
            "stream": False,
        }
        try:
            resp = await self.client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()["response"]
        except Exception as e:
            raise LLMError(f"Ollama error: {e}") from e

    async def complete_json(self, prompt: str, system: str = "", schema: dict = None) -> dict:
        json_prompt = prompt + "\n\nRespond with valid JSON only."
        text = await self.complete(json_prompt, system)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            raise LLMError(f"Ollama returned invalid JSON: {text[:200]}") from e


def get_llm_provider() -> BaseLLMProvider:
    from app.core.config import settings
    provider = settings.LLM_PROVIDER.lower()
    model = settings.LLM_MODEL or ""
    if provider == "groq":
        return GroqProvider(model=model)
    elif provider == "anthropic":
        return AnthropicProvider(model=model)
    elif provider == "ollama":
        return OllamaProvider(model=model)
    raise ValueError(f"Unknown LLM provider: {provider}. Use 'groq', 'anthropic', or 'ollama'.")
