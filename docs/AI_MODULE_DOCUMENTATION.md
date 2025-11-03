# AI Module Documentation

## Overview

The AI Module provides a unified, **lightweight** interface for integrating multiple AI providers into the PRO-Ka-Po application using only HTTP REST APIs. **No heavy SDK dependencies required!**

Supported providers:

- **Google Gemini** - Fast and versatile AI models
- **OpenAI (GPT)** - Industry-standard language models  
- **Grok (X.AI)** - Fast and efficient AI
- **Claude (Anthropic)** - Strong reasoning capabilities
- **DeepSeek** - Cost-effective AI solution

## Installation

### Install Required Packages

The AI module requires **only** the `requests` library:

```bash
pip install requests>=2.31.0
```

Or install from the AI requirements file:
```bash
pip install -r requirements_ai.txt
```

**No provider-specific SDKs needed!** The module uses direct REST API calls for all providers.

### Configure API Keys

You can configure API keys in two ways:

#### Option 1: Environment Variables (Recommended)
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-key"
$env:OPENAI_API_KEY="your-openai-key"
$env:GROK_API_KEY="your-grok-key"
$env:CLAUDE_API_KEY="your-claude-key"
$env:DEEPSEEK_API_KEY="your-deepseek-key"

# Linux/Mac
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
```

#### Option 2: UI Settings
Use the AI Settings tab in the application Settings view to enter API keys securely.

## Usage

### Basic Usage

```python
from src.Modules.AI_module import get_ai_manager, AIProvider

# Get the AI manager singleton
ai = get_ai_manager()

# Configure provider
ai.set_provider(
    provider=AIProvider.GEMINI,
    api_key="your-api-key",
    model="gemini-1.5-flash",  # Optional, uses default if not specified
    temperature=0.7,
    max_tokens=2048
)

# Generate response
response = ai.generate("What is the meaning of life?")

if response.error:
    print(f"Error: {response.error}")
else:
    print(f"Response: {response.text}")
    print(f"Model: {response.model}")
    print(f"Usage: {response.usage}")
```

### Using Different Providers

```python
from src.Modules.AI_module import get_ai_manager, AIProvider, AIModel

ai = get_ai_manager()

# Gemini
ai.set_provider(
    provider=AIProvider.GEMINI,
    api_key="your-key",
    model=AIModel.GEMINI_1_5_FLASH.value
)

# OpenAI GPT-4
ai.set_provider(
    provider=AIProvider.OPENAI,
    api_key="your-key",
    model=AIModel.GPT_4O.value
)

# Claude
ai.set_provider(
    provider=AIProvider.CLAUDE,
    api_key="your-key",
    model=AIModel.CLAUDE_3_5_SONNET.value
)

# Grok
ai.set_provider(
    provider=AIProvider.GROK,
    api_key="your-key",
    model=AIModel.GROK_BETA.value
)

# DeepSeek
ai.set_provider(
    provider=AIProvider.DEEPSEEK,
    api_key="your-key",
    model=AIModel.DEEPSEEK_CHAT.value
)
```

### Using Prompt Templates

```python
from src.Modules.AI_module import get_ai_manager, PromptTemplates

ai = get_ai_manager()

# Alarm suggestions
prompt = PromptTemplates.alarm_suggestion(
    context="User has a dentist appointment tomorrow at 2 PM"
)
response = ai.generate(prompt)

# Pomodoro analysis
prompt = PromptTemplates.pomodoro_analysis(
    session_data="10 sessions completed, average focus time: 23 minutes"
)
response = ai.generate(prompt)

# Task prioritization
prompt = PromptTemplates.task_prioritization([
    "Write report",
    "Review code",
    "Team meeting",
    "Fix bug"
])
response = ai.generate(prompt)

# Custom prompt
prompt = PromptTemplates.custom(
    module="Alarms",
    context="User wants to improve morning routine",
    instruction="Suggest 5 morning alarms with optimal timing"
)
response = ai.generate(prompt)
```

### Caching Responses

```python
ai = get_ai_manager()

# Enable caching (default)
response = ai.generate("What is Python?", use_cache=True)

# Disable caching for this request
response = ai.generate("What time is it?", use_cache=False)

# Clear cache
ai.clear_cache()
```

### Advanced Configuration

```python
from pathlib import Path

ai = get_ai_manager()

# Set custom cache directory
ai.set_cache_dir(Path.home() / ".my_app_cache")

# Get available models for current provider
models = ai.get_available_models()
print(f"Available models: {models}")

# Get current provider
current = ai.get_current_provider()
print(f"Current provider: {current}")
```

## Integration with Modules

### Alarms Module Integration

```python
from src.Modules.AI_module import get_ai_manager, PromptTemplates

def suggest_alarms_for_task(task_description: str):
    """Get AI suggestions for alarms related to a task"""
    ai = get_ai_manager()
    
    prompt = PromptTemplates.alarm_suggestion(
        context=f"Task: {task_description}"
    )
    
    response = ai.generate(prompt)
    return response.text if not response.error else None
```

### Pomodoro Module Integration

```python
from src.Modules.AI_module import get_ai_manager, PromptTemplates

def analyze_productivity(sessions_data: list):
    """Analyze Pomodoro sessions and get AI insights"""
    ai = get_ai_manager()
    
    # Format session data
    data_summary = f"{len(sessions_data)} sessions completed"
    
    prompt = PromptTemplates.pomodoro_analysis(data_summary)
    
    response = ai.generate(prompt)
    return response.text if not response.error else None
```

## UI Settings

The AI Settings dialog provides a user-friendly interface for:

1. **Provider Selection** - Choose your preferred AI provider
2. **API Key Management** - Securely store API keys
3. **Model Selection** - Pick specific models for each provider
4. **Parameter Tuning** - Adjust temperature, max tokens, timeout
5. **Cache Management** - Enable/disable caching, clear cache
6. **Connection Testing** - Test API connection before saving

### Opening AI Settings

```python
from src.ui.ai_settings import AISettingsDialog

# In your main window or menu
def open_ai_settings(self):
    dialog = AISettingsDialog(self)
    dialog.settings_changed.connect(self.on_ai_settings_changed)
    dialog.exec()

def on_ai_settings_changed(self):
    print("AI settings have been updated!")
```

## Available Models

### Gemini Models
- `gemini-pro` - Standard Gemini model
- `gemini-pro-vision` - Vision-enabled model
- `gemini-1.5-pro` - Advanced reasoning
- `gemini-1.5-flash` - Fast responses (recommended)

### OpenAI Models
- `gpt-4` - Most capable model
- `gpt-4-turbo-preview` - Faster GPT-4
- `gpt-4o` - Optimized GPT-4 (recommended)
- `gpt-3.5-turbo` - Fast and cost-effective

### Grok Models
- `grok-1` - Standard model
- `grok-beta` - Latest beta version

### Claude Models
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fastest
- `claude-3-5-sonnet-20240620` - Latest (recommended)

### DeepSeek Models
- `deepseek-chat` - General chat model
- `deepseek-coder` - Code-optimized model

## Best Practices

1. **Store API Keys Securely** - Use environment variables or the UI settings, never hardcode keys
2. **Use Caching** - Enable caching for repeated queries to save costs
3. **Choose Appropriate Models** - Use faster/cheaper models for simple tasks
4. **Set Reasonable Limits** - Configure max_tokens to prevent excessive costs
5. **Handle Errors** - Always check `response.error` before using the response
6. **Monitor Usage** - Check `response.usage` to track token consumption

## Troubleshooting

### Import Errors
```
ImportError: google.generativeai not installed
```
**Solution:** Install the required package: `pip install google-generativeai`

### API Key Errors
```
Error: Invalid API key
```
**Solution:** Check your API key in the settings or environment variables

### Timeout Errors
```
Error: Request timeout
```
**Solution:** Increase timeout value in settings or check your internet connection

### Rate Limit Errors
```
Error: Rate limit exceeded
```
**Solution:** Wait a few seconds and retry, or upgrade your API plan

## Configuration Reference

### config.py Settings

```python
# AI Provider API Keys
AI_API_KEYS = {
    'gemini': os.getenv('GEMINI_API_KEY', ''),
    'openai': os.getenv('OPENAI_API_KEY', ''),
    'grok': os.getenv('GROK_API_KEY', ''),
    'claude': os.getenv('CLAUDE_API_KEY', ''),
    'deepseek': os.getenv('DEEPSEEK_API_KEY', '')
}

# Default provider
AI_DEFAULT_PROVIDER = 'gemini'

# Response cache directory
AI_CACHE_DIR = LOCAL_DB_DIR / 'ai_cache'

# Default temperature (0.0 - 1.0)
AI_TEMPERATURE = 0.7

# Max tokens
AI_MAX_TOKENS = 2048

# Request timeout (seconds)
AI_TIMEOUT = 30
```

## API Provider Documentation

- **Gemini:** https://ai.google.dev/docs
- **OpenAI:** https://platform.openai.com/docs
- **Grok:** https://docs.x.ai/
- **Claude:** https://docs.anthropic.com/
- **DeepSeek:** https://platform.deepseek.com/docs
