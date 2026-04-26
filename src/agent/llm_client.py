import logging

from .. import config

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        config.setup_logging()
        self._provider = config.get_provider()

        if self._provider == "groq":
            import groq
            self._client = groq.Groq(api_key=config.GROQ_API_KEY)
            self._model = config.GROQ_MODEL
        else:
            self._model = config.OLLAMA_MODEL

        logger.info("LLMClient initialized with provider=%s", self._provider)

    def complete(self, system_prompt: str, user_prompt: str = "") -> str:
        messages = [{"role": "system", "content": system_prompt}]
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})

        try:
            if self._provider == "groq":
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=1000,
                )
                return resp.choices[0].message.content
            else:
                import ollama
                resp = ollama.chat(model=self._model, messages=messages)
                return resp["message"]["content"]
        except Exception as exc:
            logger.error("LLM request failed: %s", exc)
            raise RuntimeError(f"LLM request failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            response = self.complete("you are a test", "respond with the single word: ok")
            return "ok" in response.lower()
        except Exception:
            return False
