"""The Groq AI integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from groq import APIError, AsyncGroq, AuthenticationError  # type: ignore[attr-defined]

from .const import DOMAIN, LOGGER

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = (
    Platform.CONVERSATION,
    Platform.STT,
    Platform.TTS,
)

type GroqConfigEntry = ConfigEntry[AsyncGroq]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Groq AI."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GroqConfigEntry) -> bool:
    """Set up Groq AI from a config entry."""

    try:
        client = AsyncGroq(api_key=entry.data[CONF_API_KEY])

        # Test the API key by listing models
        await client.models.list()

    except AuthenticationError as err:
        raise ConfigEntryAuthFailed(f"Invalid API key: {err}") from err
    except APIError as err:
        raise ConfigEntryNotReady(f"API error: {err}") from err
    except Exception as err:
        LOGGER.exception("Unexpected error setting up Groq AI")
        raise ConfigEntryNotReady(f"Unexpected error: {err}") from err
    else:
        entry.runtime_data = client

    # Create parent integration device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Groq",
        model="AI Services",
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GroqConfigEntry) -> bool:
    """Unload Groq AI."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: GroqConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
