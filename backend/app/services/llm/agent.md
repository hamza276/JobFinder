# LLM Service — Pluggable Provider Interface

## Purpose
Abstract away all LLM providers behind a single interface. No other service should ever import `openai`, `anthropic`, or any LLM SDK directly. Everything goes through `base.py`.

## Interface

```python
# base.py
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    
    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> str:
        """Simple text completion. Returns string response."""
        pass
    
    @abstractmethod
    async def complete_json(self, prompt: str, system: str = "", schema: dict = None) -> dict:
        """JSON completion. Returns parsed dict. Raises ValueError if not valid JSON."""
        pass
    
    @abstractmethod
    async def complete_with_tools(self, messages: list, tools: list) -> dict:
        """Tool-calling / function-calling completion. Used by ReAct agent."""
        pass
```

## Providers

### `openai_provider.py`
- Uses `openai` Python SDK
- Model: `gpt-4o` by default (configurable via `LLM_MODEL` env var)
- Implements all 3 methods

### `anthropic_provider.py`
- Uses `anthropic` Python SDK  
- Model: `claude-opus-4-5` by default
- Implements all 3 methods

### `ollama_provider.py`
- Uses `httpx` to call Ollama REST API (no official SDK needed)
- Model: `llama3.1` by default
- For local/offline use

## Factory Function
`get_llm_provider()` in `base.py` — reads `LLM_PROVIDER` env var and returns correct instance.
```python
def get_llm_provider() -> BaseLLMProvider:
    provider = settings.LLM_PROVIDER  # "openai" | "anthropic" | "ollama"
    if provider == "openai":
        return OpenAIProvider()
    elif provider == "anthropic":
        return AnthropicProvider()
    elif provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
```

## `email_composer.py`
Uses `BaseLLMProvider.complete()` to generate application emails.

Input:
```python
@dataclass
class EmailCompositionRequest:
    user_profile: UserProfile
    job: Job
    contact_email: str | None   # extracted from JD, may be None
```

Output:
```python
@dataclass
class ComposedEmail:
    to: str | None
    subject: str
    body: str
    generated_at: datetime
```

Prompt strategy:
- System: "You are a professional career coach writing a job application email on behalf of [name]."
- User: Full profile + Full JD + instruction to write concise, professional email
- Email should be 3 paragraphs: intro + skills match + call to action
- If no contact email found in JD, `to` field is None (user finds it themselves)

## Notes for Codex
- Always inject provider via dependency injection (FastAPI `Depends`) — never instantiate inside business logic.
- All LLM calls should have a timeout (30 seconds default).
- Log every LLM call: prompt token count, response token count, latency. Use structured logging.
- If LLM call fails, raise `LLMError` (custom exception) — never silently return empty string.
