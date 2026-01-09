"""Constants for the Groq AI integration."""

import logging

from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.helpers import llm

LOGGER = logging.getLogger(__package__)

DOMAIN = "groq"
DEFAULT_TITLE = "Groq AI"

DEFAULT_CONVERSATION_NAME = "Groq Conversation"
DEFAULT_STT_NAME = "Groq STT"
DEFAULT_TTS_NAME = "Groq TTS"

CONF_PROMPT = "prompt"
DEFAULT_PROMPT = llm.DEFAULT_INSTRUCTIONS_PROMPT
DEFAULT_STT_PROMPT = "Transcribe the attached audio"

CONF_RECOMMENDED = "recommended"
CONF_CHAT_MODEL = "chat_model"

# Chat models
RECOMMENDED_CHAT_MODEL = "llama-3.3-70b-versatile"
CHAT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

# STT models
CONF_STT_MODEL = "stt_model"
RECOMMENDED_STT_MODEL = "whisper-large-v3-turbo"
STT_MODELS = [
    "whisper-large-v3-turbo",
    "whisper-large-v3",
]

# TTS models
CONF_TTS_MODEL = "tts_model"
CONF_TTS_VOICE = "tts_voice"
RECOMMENDED_TTS_MODEL = "canopylabs/orpheus-v1-english"
RECOMMENDED_TTS_VOICE = "troy"
TTS_MODELS = [
    "canopylabs/orpheus-v1-english",
    "canopylabs/orpheus-arabic-saudi",
]
TTS_VOICES_ENGLISH = [
    "troy",
    "clara",
    "emily",
    "james",
    "emma",
]
TTS_VOICES_ARABIC = [
    "fatimah",
    "ahmad",
]

# Model parameters
CONF_TEMPERATURE = "temperature"
RECOMMENDED_TEMPERATURE = 1.0
CONF_TOP_P = "top_p"
RECOMMENDED_TOP_P = 1.0
CONF_MAX_TOKENS = "max_tokens"
RECOMMENDED_MAX_TOKENS = 4096

# Timeouts
TIMEOUT_SECONDS = 30

# Default options
RECOMMENDED_CONVERSATION_OPTIONS = {
    CONF_PROMPT: DEFAULT_PROMPT,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
    CONF_TEMPERATURE: RECOMMENDED_TEMPERATURE,
    CONF_TOP_P: RECOMMENDED_TOP_P,
    CONF_MAX_TOKENS: RECOMMENDED_MAX_TOKENS,
    CONF_RECOMMENDED: True,
}

RECOMMENDED_STT_OPTIONS = {
    CONF_STT_MODEL: RECOMMENDED_STT_MODEL,
    CONF_PROMPT: DEFAULT_STT_PROMPT,
    CONF_RECOMMENDED: True,
}

RECOMMENDED_TTS_OPTIONS = {
    CONF_TTS_MODEL: RECOMMENDED_TTS_MODEL,
    CONF_TTS_VOICE: RECOMMENDED_TTS_VOICE,
    CONF_RECOMMENDED: True,
}
