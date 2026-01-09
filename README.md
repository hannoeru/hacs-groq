# Groq AI Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/hannoeru/hacs-groq.svg)](https://github.com/hannoeru/hacs-groq/releases)
[![CI](https://github.com/hannoeru/hacs-groq/actions/workflows/ci.yml/badge.svg)](https://github.com/hannoeru/hacs-groq/actions/workflows/ci.yml)
[![Validate](https://github.com/hannoeru/hacs-groq/actions/workflows/validate.yml/badge.svg)](https://github.com/hannoeru/hacs-groq/actions/workflows/validate.yml)

A Home Assistant custom integration that brings Groq's ultra-fast LLM inference, speech-to-text, and text-to-speech capabilities to your smart home.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hannoeru&repository=hacs-groq&category=integration)

## Features

- **🤖 Conversation Agent**: Use Groq's lightning-fast language models (LLaMA, Mixtral, Gemma) as a conversation agent with Home Assistant Assist
- **🎤 Speech-to-Text**: Transcribe audio using Groq's Whisper models (fastest Whisper inference available)
- **🔊 Text-to-Speech**: Generate natural-sounding speech with Groq's Orpheus TTS models
- **🔧 Tool Use**: Full support for Home Assistant's tool calling API for controlling devices
- **⚡ Ultra-Fast**: Groq's LPU™ inference engine delivers responses at incredible speeds

## Supported Models

The integration dynamically fetches available models from the Groq API, ensuring you always have access to the latest models. Common models include:

### Chat Models
- `llama-3.3-70b-versatile` (Recommended)
- `llama-3.1-70b-versatile`
- `llama-3.1-8b-instant`
- `mixtral-8x7b-32768`
- `gemma2-9b-it`
- And more...

### Speech-to-Text Models
- `whisper-large-v3-turbo` (Recommended - faster)
- `whisper-large-v3` (More accurate)

### Text-to-Speech Models
- `canopylabs/orpheus-v1-english` (Recommended)
- `canopylabs/orpheus-arabic-saudi`

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hannoeru&repository=hacs-groq&category=integration)

**Or manually:**

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/hannoeru/hacs-groq`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Groq AI" in the integration list and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/groq` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Groq AI"
4. Enter your Groq API key (get one at [https://console.groq.com/keys](https://console.groq.com/keys))
5. Click **Submit**

### Getting a Groq API Key

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key and use it in the integration setup

## Usage

### Conversation Agent

Once installed and configured, you can:

1. Go to **Settings** → **Voice Assistants** → **Add Assistant**
2. Configure your assistant with:
   - **Conversation agent**: Select "Groq AI"
   - **Speech-to-text**: Select "Groq STT" (optional)
   - **Text-to-speech**: Select "Groq TTS" (optional)

You can now use Groq AI with:
- Voice commands
- The conversation integration
- Assist in the mobile app

### Advanced Configuration

Click **Configure** on the Groq AI integration to customize:

- **Prompt**: System prompt for the conversation agent
- **LLM Hass API**: Enable tool calling to control Home Assistant devices
- **Chat Model**: Choose from available language models
- **Temperature**: Control response randomness (0-2)
- **Top P**: Nucleus sampling parameter (0-1)
- **Max Tokens**: Maximum response length
- **STT Model**: Whisper model for speech recognition
- **TTS Model**: Orpheus model for speech synthesis
- **TTS Voice**: Voice selection (English or Arabic)

## Tool Calling / Device Control

When you enable "LLM Hass API" in the configuration, the conversation agent can control your Home Assistant devices. For example:

- "Turn on the living room lights"
- "Set the thermostat to 72 degrees"
- "What's the temperature in the bedroom?"
- "Show me the front door camera"

## Performance

Groq's LPU™ (Language Processing Unit) technology delivers:
- **~300 tokens/second** for LLaMA models
- **~200x faster** than traditional GPU inference
- **Near-instant** speech-to-text transcription
- **Low latency** text-to-speech generation

## Troubleshooting

### API Key Invalid
- Verify your API key at [https://console.groq.com/keys](https://console.groq.com/keys)
- Make sure you copied the entire key without spaces

### Rate Limiting
- Groq has rate limits on the free tier
- Consider upgrading to a paid plan for higher limits
- Check [https://console.groq.com/settings/limits](https://console.groq.com/settings/limits)

### Entity Not Available
- Make sure the integration is properly loaded
- Check the Home Assistant logs for errors
- Try restarting Home Assistant

## Documentation

- [Groq Documentation](https://console.groq.com/docs)
- [Home Assistant Conversation](https://www.home-assistant.io/integrations/conversation/)
- [Home Assistant Voice Assistants](https://www.home-assistant.io/voice_control/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast dependency management.

```bash
# Install dependencies
uv sync

# Run linter
uv run ruff check custom_components/

# Format code
uv run ruff format custom_components/

# Type check
uv run mypy custom_components/groq/

# Or use make commands
make install    # Install dependencies
make lint       # Run linter
make format     # Format code
make typecheck  # Run type checker
make all        # Install and run all checks
```

## License

This project is licensed under the MIT License.

## Credits

- Built for [Home Assistant](https://www.home-assistant.io/)
- Powered by [Groq](https://groq.com/)
- Inspired by the [Google Generative AI Conversation](https://www.home-assistant.io/integrations/google_generative_ai_conversation/) integration

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Groq, Inc.
