"""Config flow for Groq AI integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_NAME
from homeassistant.core import HomeAssistant, callback
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
    CONF_STT_MODEL,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_TTS_MODEL,
    CONF_TTS_VOICE,
    DEFAULT_CONVERSATION_NAME,
    DEFAULT_PROMPT,
    DEFAULT_STT_NAME,
    DEFAULT_STT_PROMPT,
    DEFAULT_TITLE,
    DEFAULT_TTS_NAME,
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_STT_MODEL,
    RECOMMENDED_STT_OPTIONS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
    RECOMMENDED_TTS_MODEL,
    RECOMMENDED_TTS_OPTIONS,
    RECOMMENDED_TTS_VOICE,
    STT_MODELS,
    TTS_MODELS,
    TTS_VOICES_ARABIC,
    TTS_VOICES_ENGLISH,
)
from .helpers import get_available_models

STEP_API_DATA_SCHEMA = vol.Schema(
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

    async def async_step_api(
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
                    subentries=[
                        {
                            "subentry_type": "conversation",
                            "data": RECOMMENDED_CONVERSATION_OPTIONS,
                            "title": DEFAULT_CONVERSATION_NAME,
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "tts",
                            "data": RECOMMENDED_TTS_OPTIONS,
                            "title": DEFAULT_TTS_NAME,
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "stt",
                            "data": RECOMMENDED_STT_OPTIONS,
                            "title": DEFAULT_STT_NAME,
                            "unique_id": None,
                        },
                    ],
                )
        return self.async_show_form(
            step_id="api",
            data_schema=STEP_API_DATA_SCHEMA,
            description_placeholders={"api_key_url": "https://console.groq.com/keys"},
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self.async_step_api()

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
            return await self.async_step_api()

        reauth_entry = self._get_reauth_entry()
        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={
                CONF_NAME: reauth_entry.title,
                CONF_API_KEY: reauth_entry.data.get(CONF_API_KEY, ""),
            },
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,  # noqa: ARG003
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            "conversation": GroqSubentryFlowHandler,
            "stt": GroqSubentryFlowHandler,
            "tts": GroqSubentryFlowHandler,
        }


class GroqSubentryFlowHandler(ConfigSubentryFlow):
    """Flow for managing Groq subentries."""

    @property
    def _groq_client(self) -> AsyncGroq:
        """Return the Groq client."""
        return self._get_entry().runtime_data

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == "user"

    async def async_step_set_options(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Set subentry options."""
        # Abort if entry is not loaded
        if self._get_entry().state != ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        errors: dict[str, str] = {}

        if user_input is None:
            if self._is_new:
                options: dict[str, Any]
                if self._subentry_type == "tts":
                    options = RECOMMENDED_TTS_OPTIONS.copy()
                elif self._subentry_type == "stt":
                    options = RECOMMENDED_STT_OPTIONS.copy()
                else:
                    options = RECOMMENDED_CONVERSATION_OPTIONS.copy()
            else:
                # If this is a reconfiguration, copy existing options
                options = self._get_reconfigure_subentry().data.copy()

        else:
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)

            if self._is_new:
                return self.async_create_entry(
                    title=user_input.pop(CONF_NAME),
                    data=user_input,
                )

            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                data=user_input,
            )

        schema = await groq_config_option_schema(
            self.hass, self._is_new, self._subentry_type, options, self._groq_client
        )
        return self.async_show_form(
            step_id="set_options", data_schema=vol.Schema(schema), errors=errors
        )

    async_step_reconfigure = async_step_set_options
    async_step_user = async_step_set_options


async def groq_config_option_schema(  # noqa: PLR0912
    hass: HomeAssistant,
    is_new: bool,
    subentry_type: str,
    options: Mapping[str, Any],
    groq_client: AsyncGroq,
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

    if is_new:
        if CONF_NAME in options:
            default_name = options[CONF_NAME]
        elif subentry_type == "tts":
            default_name = DEFAULT_TTS_NAME
        elif subentry_type == "stt":
            default_name = DEFAULT_STT_NAME
        else:
            default_name = DEFAULT_CONVERSATION_NAME
        schema: dict[vol.Required | vol.Optional, Any] = {
            vol.Required(CONF_NAME, default=default_name): str,
        }
    else:
        schema = {}

    if subentry_type == "conversation":
        schema.update(
            {
                vol.Optional(
                    CONF_PROMPT,
                    description={
                        "suggested_value": options.get(CONF_PROMPT, DEFAULT_PROMPT)
                    },
                ): TemplateSelector(),
                vol.Optional(
                    CONF_LLM_HASS_API,
                    description={"suggested_value": suggested_llm_apis},
                ): SelectSelector(
                    SelectSelectorConfig(options=hass_apis, multiple=True)
                ),
            }
        )
    elif subentry_type == "stt":
        schema.update(
            {
                vol.Optional(
                    CONF_PROMPT,
                    description={
                        "suggested_value": options.get(CONF_PROMPT, DEFAULT_STT_PROMPT)
                    },
                ): TemplateSelector(),
            }
        )

    # Fetch available models dynamically (needed for model selection)
    try:
        chat_models, stt_models, tts_models = await get_available_models(groq_client)
    except Exception:
        # Fall back to static lists if fetching fails
        chat_models = CHAT_MODELS
        stt_models = STT_MODELS
        tts_models = TTS_MODELS

    chat_model_options = [
        SelectOptionDict(label=model, value=model) for model in chat_models
    ]

    stt_model_options = [
        SelectOptionDict(label=model, value=model) for model in stt_models
    ]

    tts_model_options = [
        SelectOptionDict(label=model, value=model) for model in tts_models
    ]

    # Determine the appropriate model field and default based on subentry type
    if subentry_type == "tts":
        default_model = RECOMMENDED_TTS_MODEL
        model_field = CONF_TTS_MODEL
        model_options = tts_model_options
    elif subentry_type == "stt":
        default_model = RECOMMENDED_STT_MODEL
        model_field = CONF_STT_MODEL
        model_options = stt_model_options
    else:
        default_model = RECOMMENDED_CHAT_MODEL
        model_field = CONF_CHAT_MODEL
        model_options = chat_model_options

    # Always show model selector
    # This allows users to choose the model when adding a service
    schema.update(
        {
            vol.Optional(
                model_field,
                description={"suggested_value": options.get(model_field)},
                default=default_model,
            ): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    options=model_options,
                )
            ),
        }
    )

    # For TTS, also add voice selector
    if subentry_type == "tts":
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

    # Always show all advanced parameters
    schema.update(
        {
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
        }
    )

    return schema
