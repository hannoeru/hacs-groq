"""Speech-to-text support for Groq AI."""

from __future__ import annotations

from collections.abc import AsyncIterable

from homeassistant.components import stt
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from groq import AsyncGroq

from .const import (
    CONF_STT_MODEL,
    DOMAIN,
    LOGGER,
    RECOMMENDED_STT_MODEL,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Groq STT entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "stt":
            continue

        async_add_entities(
            [GroqSTTEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class GroqSTTEntity(stt.SpeechToTextEntity):
    """Groq speech-to-text entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the STT entity."""
        self.entry = entry
        self.subentry = subentry
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="Groq",
            model=subentry.data.get(CONF_STT_MODEL, RECOMMENDED_STT_MODEL),
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def client(self) -> AsyncGroq:
        """Return the Groq client."""
        return self.entry.runtime_data

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        # Whisper supports multilingual transcription
        return [
            "af",
            "ar",
            "hy",
            "az",
            "be",
            "bs",
            "bg",
            "ca",
            "zh",
            "hr",
            "cs",
            "da",
            "nl",
            "en",
            "et",
            "fi",
            "fr",
            "gl",
            "de",
            "el",
            "he",
            "hi",
            "hu",
            "is",
            "id",
            "it",
            "ja",
            "kn",
            "kk",
            "ko",
            "lv",
            "lt",
            "mk",
            "ms",
            "mr",
            "mi",
            "ne",
            "no",
            "fa",
            "pl",
            "pt",
            "ro",
            "ru",
            "sr",
            "sk",
            "sl",
            "es",
            "sw",
            "sv",
            "tl",
            "ta",
            "th",
            "tr",
            "uk",
            "ur",
            "vi",
            "cy",
        ]

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        """Return a list of supported formats."""
        return [
            stt.AudioFormats.WAV,
            stt.AudioFormats.OGG,
            stt.AudioFormats.FLAC,
        ]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        """Return a list of supported codecs."""
        return [
            stt.AudioCodecs.PCM,
            stt.AudioCodecs.OPUS,
            stt.AudioCodecs.FLAC,
        ]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        """Return a list of supported bit rates."""
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        """Return a list of supported sample rates."""
        return [
            stt.AudioSampleRates.SAMPLERATE_16000,
            stt.AudioSampleRates.SAMPLERATE_44100,
            stt.AudioSampleRates.SAMPLERATE_48000,
        ]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        """Return a list of supported channels."""
        return [
            stt.AudioChannels.CHANNEL_MONO,
            stt.AudioChannels.CHANNEL_STEREO,
        ]

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        """Process an audio stream to STT service."""
        # Collect all audio data
        audio_data = b""
        async for chunk in stream:
            audio_data += chunk

        if not audio_data:
            LOGGER.warning("Received empty audio stream")
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)

        # Get model from subentry data
        options = self.subentry.data
        model = options.get(CONF_STT_MODEL, RECOMMENDED_STT_MODEL)

        # Prepare the file for upload
        # Groq API expects a file-like object with a name attribute
        file_name = f"audio.{metadata.format.value}"

        try:
            # Create transcription using Groq's Whisper API
            transcription = await self.client.audio.transcriptions.create(
                model=model,
                file=(file_name, audio_data),
                response_format="text",
                language=metadata.language if metadata.language != "*" else None,
            )

            if transcription:
                return stt.SpeechResult(
                    transcription,
                    stt.SpeechResultState.SUCCESS,
                )
            else:
                LOGGER.warning("Empty transcription result from Groq")
                return stt.SpeechResult(None, stt.SpeechResultState.ERROR)

        except Exception as err:
            LOGGER.error("Error during STT processing: %s", err)
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
