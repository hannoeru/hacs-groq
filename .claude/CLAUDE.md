# Groq HACS Integration Project

## Overview
A custom Home Assistant integration that provides Groq AI services including conversation agent, speech-to-text (STT), and text-to-speech (TTS) capabilities.

## Project Structure
```
hacs-groq/
├── custom_components/groq/         # Main integration code
│   ├── __init__.py                 # Integration setup and entry point
│   ├── config_flow.py              # Configuration flow UI
│   ├── const.py                    # Constants and configuration
│   ├── conversation.py             # Conversation agent implementation
│   ├── stt.py                      # Speech-to-text implementation
│   ├── tts.py                      # Text-to-speech implementation
│   ├── helpers.py                  # Helper functions (model caching, etc.)
│   ├── manifest.json               # Integration metadata
│   ├── strings.json                # UI strings
│   └── translations/               # Localization files
│       ├── en.json                 # English translations
│       └── zh-Hans.json            # Chinese (Simplified) translations
├── .vscode/                        # VS Code settings
│   ├── settings.json               # Editor and tool configurations
│   ├── extensions.json             # Recommended extensions
│   ├── launch.json                 # Debug configurations
│   └── tasks.json                  # Build and test tasks
├── hacs.json                       # HACS metadata
├── README.md                       # User documentation
├── LICENSE                         # MIT License
├── Makefile                        # Development commands
├── pyproject.toml                  # Python project configuration
└── .gitignore                      # Git ignore rules
```

## Key Features
1. **Conversation Agent**: Fast LLM-powered conversation with tool calling support
2. **Speech-to-Text**: Whisper-based audio transcription
3. **Text-to-Speech**: Orpheus-powered natural voice synthesis
4. **Multi-language Support**: English and Chinese UI translations
5. **HACS Compatible**: Ready for distribution via HACS
6. **Dynamic Model Fetching**: Automatically discovers and lists available Groq models

## Technical Details

### Supported Groq Models
Models are automatically fetched from the Groq API and cached for 60 minutes:
- **Chat**: All available chat/completion models (LLaMA, Mixtral, Gemma, etc.)
- **STT**: All Whisper models
- **TTS**: All Orpheus/TTS models

Hardcoded fallback lists are used if API fetching fails.

### Dependencies
- `groq==0.11.0` - Official Groq Python SDK
- Home Assistant 2024.1.0 or later

### Integration Points
- Home Assistant Conversation API
- Home Assistant STT API
- Home Assistant TTS API
- LLM Tool Calling API

## Configuration
The integration supports two configuration modes:
1. **Recommended Mode**: Uses optimal default settings
2. **Advanced Mode**: Full control over all model parameters

## Development Notes
- Based on Home Assistant's Google Generative AI Conversation integration pattern
- Follows HACS integration requirements
- Uses async/await throughout
- Implements proper error handling and logging
- Dynamic model fetching with intelligent caching (60-minute TTL)
- Model categorization based on ID patterns (whisper=STT, orpheus=TTS, others=chat)
- Uses `uv` for fast dependency management
- Development tools: ruff (linting/formatting), mypy (type checking), pytest (testing)

## Development Setup
```bash
# Install dependencies
uv sync

# Or use make commands
make install    # Install dependencies
make lint       # Run linter
make format     # Format code
make typecheck  # Run type checker
make all        # Install and run all checks
```

### VS Code Integration
The project includes VS Code configurations for an optimal development experience:
- **Auto-formatting** on save with Ruff
- **Linting** with Ruff (runs on save)
- **Type checking** with MyPy
- **Debugging** configurations for Python and Pytest
- **Tasks** for common operations (Cmd+Shift+P → "Tasks: Run Task")
- **Recommended extensions** (VS Code will prompt to install)

Install recommended extensions when prompted, or manually install:
- Python, Pylance, Ruff, MyPy Type Checker
- Home Assistant extension
- YAML, Prettier, GitLens

## Testing Checklist
- [ ] Installation via HACS
- [ ] API key validation
- [ ] Dynamic model fetching and caching
- [ ] Model list displays correctly in UI
- [ ] Conversation agent responses
- [ ] Tool calling functionality
- [ ] STT transcription
- [ ] TTS audio generation
- [ ] Configuration options
- [ ] Re-authentication flow
- [ ] Fallback to hardcoded models on API errors

## API Reference
- Groq Docs: https://console.groq.com/docs
- HACS Publish: https://hacs.xyz/docs/publish/
- HA Conversation: https://developers.home-assistant.io/docs/conversation

## Future Enhancements
- AI Task support (like Google Generative AI integration)
- Streaming responses
- Vision/image input support
- Advanced safety controls
- Usage statistics and monitoring
