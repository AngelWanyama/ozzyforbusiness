"""
Shared AI client wrapper.

Centralizes AI client setup so chat_engine, report_engine, invoice_parser, receipt_scanner,
and summary_generator don't each duplicate the "is the key configured?" check and error
handling.

Provider: OpenAI (paid — approved deliberately by Angel on 2026-08-30, see CLAUDE.md Rule 1).
Model: gpt-4o-mini for every text/vision call, per Appendix A of the Ozzy Behaviour
Intelligence Brain (brain-spec/Ozzy_Behaviour_Intelligence_Brain_v1.md). Do not switch to
gpt-4o or a larger/costlier model without a specific, tested reason.

TEMPORARY FALLBACK (2026-08-30): Angel doesn't have an OPENAI_API_KEY to test with yet, so
if it's unset this falls back to Groq — which exposes an OpenAI-compatible endpoint, so the
same client class and the same tool-calling code in chat_engine.py work unchanged either way.
This does NOT change CLAUDE.md Rule 2 (OpenAI is still the intended provider) — remove this
fallback once a real OPENAI_API_KEY is set. OpenAI always wins if both keys are present.
"""
import logging
from typing import Optional
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TRANSCRIPTION_MODEL = "whisper-1"

# Groq fallback only — see module docstring.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_VISION_MODEL = "qwen/qwen3.6-27b"
GROQ_TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"


class AIClient:
    def __init__(self):
        self._client: Optional[OpenAI] = None
        self._provider: Optional[str] = None
        self._model = OPENAI_MODEL
        self._vision_model = OPENAI_MODEL
        self._transcription_model = OPENAI_TRANSCRIPTION_MODEL

        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        groq_key = getattr(settings, "GROQ_API_KEY", None)

        if openai_key and openai_key != "your_openai_api_key_here":
            try:
                self._client = OpenAI(api_key=openai_key)
                self._provider = "openai"
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        elif groq_key and groq_key != "your_groq_api_key_here":
            try:
                self._client = OpenAI(api_key=groq_key, base_url=GROQ_BASE_URL)
                self._provider = "groq"
                self._model = GROQ_MODEL
                self._vision_model = GROQ_VISION_MODEL
                self._transcription_model = GROQ_TRANSCRIPTION_MODEL
                logger.warning("Using Groq as a temporary fallback — no OPENAI_API_KEY configured. See ai_client.py docstring.")
            except Exception as e:
                logger.error(f"Failed to initialize Groq fallback client: {e}")
        else:
            logger.warning("Neither OPENAI_API_KEY nor GROQ_API_KEY is configured — AI features will use fallback logic.")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    @property
    def provider(self) -> Optional[str]:
        return self._provider

    def generate(self, prompt: str, model: Optional[str] = None, json_mode: bool = False) -> Optional[str]:
        if not self._client:
            return None
        try:
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(
                model=model or self._model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as e:
            logger.error(f"AI call failed ({self._provider}): {e}")
            return None

    def chat(
        self,
        messages: list,
        tools: Optional[list] = None,
        tool_choice: str = "auto",
        model: Optional[str] = None,
    ):
        """
        Low-level chat call that supports tool/function calling. Returns the raw response
        message (with .content and .tool_calls), or None if unconfigured/on failure — callers
        should treat a tool-call round and a plain-text round the same way at this layer.
        """
        if not self._client:
            return None
        try:
            kwargs = {}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
            response = self._client.chat.completions.create(
                model=model or self._model,
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message
        except Exception as e:
            logger.error(f"AI chat call failed ({self._provider}): {e}")
            return None

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> Optional[str]:
        """Transcribes a short voice recording to text via Whisper (OpenAI's whisper-1, or
        Groq's whisper-large-v3-turbo under the temporary fallback). Returns None if
        unconfigured, on failure, or if nothing was heard."""
        if not self._client:
            return None
        try:
            result = self._client.audio.transcriptions.create(
                model=self._transcription_model,
                file=(filename, audio_bytes),
                response_format="text",
            )
            text = (result or "").strip() if isinstance(result, str) else (getattr(result, "text", "") or "").strip()
            return text or None
        except Exception as e:
            logger.error(f"AI transcription failed ({self._provider}): {e}")
            return None

    def generate_from_image(
        self,
        prompt: str,
        image_base64: str,
        mime_type: str = "image/jpeg",
        model: Optional[str] = None,
        json_mode: bool = False,
    ) -> Optional[str]:
        """Same as generate(), but sends an image alongside the text prompt to a vision-capable
        model (gpt-4o-mini handles vision natively; the Groq fallback uses its own vision model)."""
        if not self._client:
            return None
        try:
            vision_model = model or self._vision_model
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    ],
                }],
                **kwargs,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as e:
            logger.error(f"AI vision call failed ({self._provider}): {e}")
            return None


ai_client = AIClient()
