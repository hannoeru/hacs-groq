"""Config flow for Groq AI integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
)
import voluptuous as vol

from groq import APIError, AsyncGroq, AuthenticationError

from .const import (
    CHAT_MODELS,
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_RECOMMENDED,
    CONF_STT_MODEL,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_TTS_MODEL,
    CONF_TTS_VOICE,
    DEFAULT_PROMPT,
    DEFAULT_TITLE,
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_STT_MODEL,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
    RECOMMENDED_TTS_MODEL,
    RECOMMENDED_TTS_VOICE,
    STT_MODELS,
    TTS_MODELS,
    TTS_VOICES_ARABIC,
    TTS_VOICES_ENGLISH,
)
from .helpers import get_available_models

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    client = AsyncGroq(api_key=data[CONF_API_KEY])
    # Test the API key by listing models
    await client.models.list()


class GroqConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Groq AI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(user_input)
            try:
                await validate_input(self.hass, user_input)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except APIError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                if self.source == SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data=user_input,
                    )
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data=user_input,
                    options=RECOMMENDED_CONVERSATION_OPTIONS,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={"api_key_url": "https://console.groq.com/keys"},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle configuration by re-auth."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is not None:
            return await self.async_step_user()

        reauth_entry = self._get_reauth_entry()
        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={
                CONF_NAME: reauth_entry.title,
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return GroqOptionsFlow(config_entry)


class GroqOptionsFlow(OptionsFlow):
    """Handle options flow for Groq AI."""

    last_rendered_recommended = False

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is None:
            options = self.config_entry.options.copy()
            self.last_rendered_recommended = options.get(CONF_RECOMMENDED, False)
        else:
            if user_input[CONF_RECOMMENDED] == self.last_rendered_recommended:
                if not user_input.get(CONF_LLM_HASS_API):
                    user_input.pop(CONF_LLM_HASS_API, None)
                return self.async_create_entry(title="", data=user_input)

            # Re-render the options again, now with the recommended options shown/hidden
            self.last_rendered_recommended = user_input[CONF_RECOMMENDED]
            options = user_input

        schema = await groq_config_option_schema(self.hass, options, self.config_entry)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )


async def groq_config_option_schema(
    hass: HomeAssistant, options: Mapping[str, Any], config_entry=None
) -> dict:
    """Return a schema for Groq completion options."""
    hass_apis: list[SelectOptionDict] = [
        SelectOptionDict(
            label=api.name,
            value=api.id,
        )
        for api in llm.async_get_apis(hass)
    ]

    if (suggested_llm_apis := options.get(CONF_LLM_HASS_API)) and isinstance(
        suggested_llm_apis, str
    ):
        suggested_llm_apis = [suggested_llm_apis]

    # Fetch available models dynamically if we have a config entry
    chat_models = CHAT_MODELS
    stt_models = STT_MODELS
    tts_models = TTS_MODELS

    if config_entry is not None:
        try:
            client = AsyncGroq(api_key=config_entry.data[CONF_API_KEY])
            chat_models, stt_models, tts_models = await get_available_models(client)
        except Exception:
            # Fall back to static lists if fetching fails
            pass

    chat_model_options = [
        SelectOptionDict(label=model, value=model) for model in chat_models
    ]

    stt_model_options = [
        SelectOptionDict(label=model, value=model) for model in stt_models
    ]

    tts_model_options = [
        SelectOptionDict(label=model, value=model) for model in tts_models
    ]

    schema: dict[vol.Required | vol.Optional, Any] = {
        vol.Optional(
            CONF_PROMPT,
            description={"suggested_value": options.get(CONF_PROMPT, DEFAULT_PROMPT)},
        ): TemplateSelector(),
        vol.Optional(
            CONF_LLM_HASS_API,
            description={"suggested_value": suggested_llm_apis},
        ): SelectSelector(SelectSelectorConfig(options=hass_apis, multiple=True)),
        vol.Required(
            CONF_RECOMMENDED, default=options.get(CONF_RECOMMENDED, False)
        ): bool,
    }

    if not options.get(CONF_RECOMMENDED):
        # Get voice options based on TTS model
        tts_model = options.get(CONF_TTS_MODEL, RECOMMENDED_TTS_MODEL)
        if "arabic" in tts_model.lower():
            voice_options = [
                SelectOptionDict(label=voice, value=voice)
                for voice in TTS_VOICES_ARABIC
            ]
        else:
            voice_options = [
                SelectOptionDict(label=voice, value=voice)
                for voice in TTS_VOICES_ENGLISH
            ]

        schema.update(
            {
                vol.Optional(
                    CONF_CHAT_MODEL,
                    description={"suggested_value": options.get(CONF_CHAT_MODEL)},
                    default=RECOMMENDED_CHAT_MODEL,
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN, options=chat_model_options
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE,
                    description={"suggested_value": options.get(CONF_TEMPERATURE)},
                    default=RECOMMENDED_TEMPERATURE,
                ): NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.05)),
                vol.Optional(
                    CONF_TOP_P,
                    description={"suggested_value": options.get(CONF_TOP_P)},
                    default=RECOMMENDED_TOP_P,
                ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    description={"suggested_value": options.get(CONF_MAX_TOKENS)},
                    default=RECOMMENDED_MAX_TOKENS,
                ): NumberSelector(NumberSelectorConfig(min=1, max=32768, step=1)),
                vol.Optional(
                    CONF_STT_MODEL,
                    description={"suggested_value": options.get(CONF_STT_MODEL)},
                    default=RECOMMENDED_STT_MODEL,
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN, options=stt_model_options
                    )
                ),
                vol.Optional(
                    CONF_TTS_MODEL,
                    description={"suggested_value": options.get(CONF_TTS_MODEL)},
                    default=RECOMMENDED_TTS_MODEL,
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN, options=tts_model_options
                    )
                ),
                vol.Optional(
                    CONF_TTS_VOICE,
                    description={"suggested_value": options.get(CONF_TTS_VOICE)},
                    default=RECOMMENDED_TTS_VOICE,
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN, options=voice_options
                    )
                ),
            }
        )

    return schema
