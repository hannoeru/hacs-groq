"""Conversation support for the Groq AI integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
from typing import Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from groq import AsyncGroq
from groq.types.chat import ChatCompletionChunk

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
from .voluptuous_to_jsonschema import convert

# Max number of back and forth with the LLM to generate a response
MAX_TOOL_ITERATIONS = 10


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Groq conversation entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "conversation":
            continue

        async_add_entities(
            [GroqConversationEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


def _convert_messages(
    chat_log: conversation.ChatLog,
) -> list[dict]:
    """Convert chat log to Groq message format."""
    messages = []

    for content in chat_log.content:
        if content.role == "system":
            messages.append({"role": "system", "content": content.content})
        elif content.role == "user":
            messages.append({"role": "user", "content": content.content})
        elif content.role == "assistant":
            msg = {"role": "assistant"}
            if content.content:
                msg["content"] = content.content
            if content.tool_calls:
                msg["tool_calls"] = [  # type: ignore[assignment]
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.tool_name,
                            "arguments": json.dumps(tool_call.tool_args),
                        },
                    }
                    for tool_call in content.tool_calls
                ]
            messages.append(msg)
        elif content.role == "tool_result":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": content.tool_call_id,
                    "content": json.dumps(content.tool_result),
                }
            )

    return messages


def _format_tool(tool: llm.Tool, custom_serializer) -> dict:
    """Format tool specification for Groq API."""

    # `tool.parameters` is a Voluptuous schema in HA. Convert it into JSON schema.
    # We avoid depending on external `voluptuous_openapi` because it's not
    # guaranteed to be present in the HA runtime.
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": convert(tool.parameters, custom_serializer=custom_serializer),
        },
    }


async def _transform_stream(  # noqa: PLR0912
    stream: AsyncGenerator[ChatCompletionChunk],
) -> AsyncGenerator[
    conversation.AssistantContentDeltaDict | conversation.ToolResultContentDeltaDict
]:
    """Transform Groq stream to Home Assistant format."""
    current_tool_calls: dict[int, dict] = {}

    async for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        # Handle content delta
        if delta.content:
            yield {"content": delta.content}

        # Handle tool calls
        if delta.tool_calls:
            for tool_call_delta in delta.tool_calls:
                idx = tool_call_delta.index
                if idx not in current_tool_calls:
                    current_tool_calls[idx] = {
                        "id": tool_call_delta.id or "",
                        "name": "",
                        "arguments": "",
                    }

                if tool_call_delta.id:
                    current_tool_calls[idx]["id"] = tool_call_delta.id
                if tool_call_delta.function:
                    if tool_call_delta.function.name:
                        current_tool_calls[idx]["name"] = tool_call_delta.function.name
                    if tool_call_delta.function.arguments:
                        current_tool_calls[idx]["arguments"] += (
                            tool_call_delta.function.arguments
                        )

        # Check if we have complete tool calls
        finish_reason = chunk.choices[0].finish_reason
        if finish_reason == "tool_calls" and current_tool_calls:
            tool_inputs = []
            for tool_call in current_tool_calls.values():
                if tool_call["id"] and tool_call["name"] and tool_call["arguments"]:
                    try:
                        tool_inputs.append(
                            llm.ToolInput(
                                id=tool_call["id"],
                                tool_name=tool_call["name"],
                                tool_args=json.loads(tool_call["arguments"]),
                            )
                        )
                    except json.JSONDecodeError:
                        LOGGER.warning(
                            "Failed to parse tool arguments: %s", tool_call["arguments"]
                        )
            if tool_inputs:
                yield {"tool_calls": tool_inputs}


class GroqConversationEntity(
    ConversationEntity, conversation.AbstractConversationAgent
):
    """Groq conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supports_streaming = True

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the agent."""
        self.entry = entry
        self.subentry = subentry
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="Groq",
            model=subentry.data.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL),
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        if self.subentry.data.get(CONF_LLM_HASS_API):
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
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    @property
    def client(self) -> AsyncGroq:
        """Return the Groq client."""
        return self.entry.runtime_data

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process the user input and call the API."""
        options = self.subentry.data

        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                options.get(CONF_LLM_HASS_API),
                options.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        await self._async_handle_chat_log(chat_log)

        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    async def _async_handle_chat_log(
        self,
        chat_log: conversation.ChatLog,
    ) -> None:
        """Generate an answer for the chat log."""
        options = self.subentry.data

        messages = _convert_messages(chat_log)

        model = options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)
        temperature = options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE)
        top_p = options.get(CONF_TOP_P, RECOMMENDED_TOP_P)
        max_tokens = int(options.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS))

        tools = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]

        # To prevent infinite loops, we limit the number of iterations
        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                # Use streaming for better UX
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    tools=tools if tools else None,  # type: ignore[arg-type]
                    stream=True,
                )
            except Exception as err:
                LOGGER.error("Error talking to Groq API: %s", err)
                raise HomeAssistantError("Error talking to Groq API") from err

            # Process the stream through ChatLog
            async for content in chat_log.async_add_delta_content_stream(
                self.entity_id,
                _transform_stream(stream),  # type: ignore[arg-type]
            ):
                # Add streamed content to messages for next iteration
                if content.role == "assistant":
                    msg = {"role": "assistant"}
                    if content.content:
                        msg["content"] = content.content
                    if content.tool_calls:
                        msg["tool_calls"] = [  # type: ignore[assignment]
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.tool_name,
                                    "arguments": json.dumps(tool_call.tool_args),
                                },
                            }
                            for tool_call in content.tool_calls
                        ]
                    messages.append(msg)
                elif content.role == "tool_result":
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": content.tool_call_id,
                            "content": json.dumps(content.tool_result),
                        }
                    )

            # If no unresponded tool results, we're done
            if not chat_log.unresponded_tool_results:
                break
