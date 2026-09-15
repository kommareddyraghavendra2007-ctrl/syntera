"""OpenAI LLM provider using the official openai SDK."""
from __future__ import annotations

from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMResponse

logger = get_logger(__name__)


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        try:
            from openai import OpenAI  # noqa: PLC0415

            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url or "https://api.openai.com/v1",
                timeout=timeout,
            )
        except ImportError as e:
            raise RuntimeError(
                "openai package required. Install: pip install openai"
            ) from e
        self._model = model
        logger.info("openai_llm_provider_init", extra={"model": model})

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )
