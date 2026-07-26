"""
Shared AI client wrapper.

Centralizes AI client setup so nlp_parser, report_engine, and summary_generator
don't each duplicate the "is the key configured?" check and error handling.

Provider: Groq (free tier, no card required, no billing approval delays —
switched from Gemini after hitting Google's account-verification issues).
Groq is OpenAI-SDK-compatible and hosts open models like Llama 3.3.
"""
import logging
from typing import Optional
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class AIClient:
    def __init__(self):
        self._client: Optional[Groq] = None
        key = getattr(settings, "GROQ_API_KEY", None)
        if key and key != "your_groq_api_key_here":
            try:
                self._client = Groq(api_key=key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self._client = None
        else:
            logger.warning("GROQ_API_KEY not configured — AI features will use fallback logic.")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def generate(self, prompt: str, model: str = DEFAULT_MODEL, json_mode: bool = False) -> Optional[str]:
        if not self._client:
            return None
        try:
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            return None


ai_client = AIClient()