"""Helper functions for the Groq AI integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from groq import AsyncGroq

from .const import (
    CHAT_MODELS,
    LOGGER,
    STT_MODELS,
    TTS_MODELS,
)


class ModelCache:
    """Cache for dynamically fetched models."""

    def __init__(self, ttl_minutes: int = 60):
        """Initialize the model cache.

        Args:
            ttl_minutes: Time-to-live for cached models in minutes.
        """
        self._chat_models: list[str] | None = None
        self._stt_models: list[str] | None = None
        self._tts_models: list[str] | None = None
        self._last_updated: datetime | None = None
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = asyncio.Lock()

    def is_expired(self) -> bool:
        """Check if the cache is expired."""
        if self._last_updated is None:
            return True
        return datetime.now() - self._last_updated > self._ttl

    async def get_models(
        self, client: AsyncGroq
    ) -> tuple[list[str], list[str], list[str]]:
        """Get cached or fetch models from API.

        Args:
            client: AsyncGroq client for API calls.

        Returns:
            Tuple of (chat_models, stt_models, tts_models).
        """
        async with self._lock:
            if self.is_expired():
                await self._fetch_models(client)

            return (
                self._chat_models or CHAT_MODELS,
                self._stt_models or STT_MODELS,
                self._tts_models or TTS_MODELS,
            )

    async def _fetch_models(self, client: AsyncGroq) -> None:
        """Fetch available models from Groq API."""
        try:
            LOGGER.debug("Fetching available models from Groq API")
            response = await client.models.list()

            chat_models = []
            stt_models = []
            tts_models = []

            for model in response.data:
                model_id = model.id
                model_lower = model_id.lower()

                # Categorize models based on their ID patterns
                if "whisper" in model_lower:
                    stt_models.append(model_id)
                elif "orpheus" in model_lower or "tts" in model_lower:
                    tts_models.append(model_id)
                else:
                    # Assume it's a chat model if not STT/TTS
                    chat_models.append(model_id)

            # Only update if we got results
            if chat_models:
                self._chat_models = sorted(chat_models)
                LOGGER.debug(f"Found {len(chat_models)} chat models: {chat_models}")

            if stt_models:
                self._stt_models = sorted(stt_models)
                LOGGER.debug(f"Found {len(stt_models)} STT models: {stt_models}")

            if tts_models:
                self._tts_models = sorted(tts_models)
                LOGGER.debug(f"Found {len(tts_models)} TTS models: {tts_models}")

            self._last_updated = datetime.now()

        except Exception as e:
            LOGGER.warning(f"Failed to fetch models from Groq API, using fallback: {e}")
            # Keep existing cache or use fallback constants
            if self._chat_models is None:
                self._chat_models = CHAT_MODELS
            if self._stt_models is None:
                self._stt_models = STT_MODELS
            if self._tts_models is None:
                self._tts_models = TTS_MODELS


# Global model cache instance
_model_cache = ModelCache()


async def get_available_models(
    client: AsyncGroq,
) -> tuple[list[str], list[str], list[str]]:
    """Get available models from cache or API.

    Args:
        client: AsyncGroq client for API calls.

    Returns:
        Tuple of (chat_models, stt_models, tts_models).
    """
    return await _model_cache.get_models(client)
