"""Text-to-speech support for Groq AI."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.tts import (
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from groq import AsyncGroq

from .const import (
    CONF_TTS_MODEL,
    CONF_TTS_VOICE,
    DOMAIN,
    LOGGER,
    RECOMMENDED_TTS_MODEL,
    RECOMMENDED_TTS_VOICE,
    TTS_VOICES_ARABIC,
    TTS_VOICES_ENGLISH,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Groq TTS entities."""
    async_add_entities([GroqTTSEntity(config_entry)])


class GroqTTSEntity(TextToSpeechEntity):
    """Groq text-to-speech entity."""

    _attr_has_entity_name = True
    _attr_name = "Text to Speech"
    _attr_supported_options = [ATTR_VOICE]

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the TTS entity."""
        self.entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_tts"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.title,
            "manufacturer": "Groq",
            "model": "Text to Speech",
            "entry_type": "service",
        }
        self._update_voice_list()

    def _update_voice_list(self) -> None:
        """Update the voice list based on the configured model."""
        options = self.entry.options
        model = options.get(CONF_TTS_MODEL, RECOMMENDED_TTS_MODEL)

        if "arabic" in model.lower():
            voices = TTS_VOICES_ARABIC
            self._attr_supported_languages = ["ar"]
            self._attr_default_language = "ar"
        else:
            voices = TTS_VOICES_ENGLISH
            self._attr_supported_languages = ["en"]
            self._attr_default_language = "en"

        self._supported_voices = [Voice(voice, voice.title()) for voice in voices]

    @property
    def client(self) -> AsyncGroq:
        """Return the Groq client."""
        return self.entry.runtime_data

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return a list of supported voices for a language."""
        self._update_voice_list()
        return self._supported_voices

    @property
    def default_options(self) -> Mapping[str, Any]:
        """Return a mapping with the default options."""
        options = self.entry.options
        default_voice = options.get(CONF_TTS_VOICE, RECOMMENDED_TTS_VOICE)
        return {ATTR_VOICE: default_voice}

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Load TTS audio file from the engine."""
        config_options = self.entry.options
        model = config_options.get(CONF_TTS_MODEL, RECOMMENDED_TTS_MODEL)
        voice = options.get(
            ATTR_VOICE, config_options.get(CONF_TTS_VOICE, RECOMMENDED_TTS_VOICE)
        )

        try:
            # Create speech using Groq's TTS API (Orpheus)
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=message,
                response_format="wav",
            )

            # The response is the audio content
            if hasattr(response, "read"):
                audio_data = await response.read()
            elif isinstance(response, bytes):
                audio_data = response
            else:
                # Response might have a write_to_file method, so we need to get the content
                audio_data = (
                    response.content
                    if hasattr(response, "content")
                    else bytes(response)
                )

            return "wav", audio_data

        except Exception as err:
            LOGGER.error("Error during TTS: %s", err)
            raise HomeAssistantError(f"Error generating speech: {err}") from err
