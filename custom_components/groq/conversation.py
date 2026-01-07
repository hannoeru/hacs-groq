"""Conversation support for the Groq AI integration."""

from __future__ import annotations

from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid

from groq import AsyncGroq
from groq.types.chat import ChatCompletion

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DOMAIN,
    LOGGER,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Groq conversation entities."""
    async_add_entities([GroqConversationEntity(config_entry)])


class GroqConversationEntity(
    ConversationEntity, conversation.AbstractConversationAgent
):
    """Groq conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.entry = entry
        self.history: dict[str, list[dict[str, Any]]] = {}
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Groq",
            "model": "Conversation Agent",
            "entry_type": "service",
        }
        if self.entry.options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        # Reload to pick up new options
        await hass.config_entries.async_reload(entry.entry_id)

    @property
    def client(self) -> AsyncGroq:
        """Return the Groq client."""
        return self.entry.runtime_data

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        options = self.entry.options
        intent_response = intent.IntentResponse(language=user_input.language)
        llm_api: llm.APIInstance | None = None
        tools: list[dict] | None = None
        llm_context = user_input.as_llm_context(DOMAIN)

        if options.get(CONF_LLM_HASS_API):
            try:
                llm_api = await llm.async_get_api(
                    self.hass,
                    options[CONF_LLM_HASS_API],
                    llm_context,
                )
            except HomeAssistantError as err:
                LOGGER.error("Error getting LLM API: %s", err)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Error preparing LLM API: {err}",
                )
                return conversation.ConversationResult(
                    response=intent_response, conversation_id=user_input.conversation_id
                )

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in llm_api.tools
            ]

        if user_input.conversation_id is None:
            conversation_id = ulid.ulid_now()
            messages = []
        else:
            conversation_id = user_input.conversation_id
            messages = self.history.get(conversation_id, []).copy()

        if not messages:
            if system_prompt := options.get(CONF_PROMPT):
                try:
                    prompt = self._async_generate_prompt(system_prompt, llm_context)
                except HomeAssistantError as err:
                    LOGGER.error("Error rendering prompt: %s", err)
                    intent_response.async_set_error(
                        intent.IntentResponseErrorCode.UNKNOWN,
                        f"Error rendering prompt: {err}",
                    )
                    return conversation.ConversationResult(
                        response=intent_response,
                        conversation_id=conversation_id,
                    )
                messages.append({"role": "system", "content": prompt})

        messages.append({"role": "user", "content": user_input.text})

        LOGGER.debug("Prompt for %s: %s", self.entry.title, messages)

        # Get model parameters
        model = options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)
        temperature = options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE)
        top_p = options.get(CONF_TOP_P, RECOMMENDED_TOP_P)
        max_tokens = options.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS)

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                tools=tools if tools else None,
            )
        except Exception as err:
            LOGGER.error("Error talking to Groq API: %s", err)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Error talking to Groq API: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        LOGGER.debug("Response from Groq: %s", response)

        choice = response.choices[0]
        message = choice.message

        # Handle tool calls
        if message.tool_calls and llm_api:
            tool_messages = []
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                LOGGER.debug(
                    "Tool call: %s with args: %s",
                    tool_name,
                    tool_args,
                )

                try:
                    tool_result = await llm_api.async_call_tool(tool_call.model_dump())
                except HomeAssistantError as err:
                    tool_result = {"error": str(err)}

                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result),
                    }
                )

            # Add assistant message and tool responses to history
            messages.append(message.model_dump(exclude_unset=True))
            messages.extend(tool_messages)

            # Make another API call with tool results
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                message = choice.message
            except Exception as err:
                LOGGER.error("Error in second Groq API call: %s", err)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Error in second Groq API call: {err}",
                )
                return conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )

        # Store the conversation history
        messages.append({"role": "assistant", "content": message.content})
        self.history[conversation_id] = messages

        intent_response.async_set_speech(message.content or "")
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    def _async_generate_prompt(
        self, prompt_template: str, llm_context: llm.LLMContext
    ) -> str:
        """Generate a prompt from a template."""
        return llm.async_render_prompt(self.hass, prompt_template, llm_context)
