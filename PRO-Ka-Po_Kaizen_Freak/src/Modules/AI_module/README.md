# AI Module 🤖

Universal AI integration module for PRO-Ka-Po application supporting multiple AI providers.

## Features ✨

- **Multi-Provider Support**: Gemini, OpenAI, Grok, Claude, DeepSeek
- **Unified Interface**: Single API for all providers
- **Smart Caching**: Reduces costs by caching repeated queries
- **Async Support**: Background processing for better UX
- **User-Friendly UI**: Configure providers via settings dialog
- **Prompt Templates**: Pre-built prompts for common tasks
- **Error Handling**: Graceful fallbacks and error messages
- **Token Tracking**: Monitor API usage and costs

## Quick Start 🚀

### 1. Install Dependencies

```bash
# Install all providers
pip install -r requirements_ai.txt

# Or install specific providers
pip install google-generativeai  # Gemini
pip install openai              # OpenAI, Grok, DeepSeek
pip install anthropic           # Claude
```

### 2. Set API Key

```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-api-key-here"

# Linux/Mac
export GEMINI_API_KEY="your-api-key-here"
```

### 3. Use in Code

```python
from src.Modules.AI_module import get_ai_manager, AIProvider

# Get manager
ai = get_ai_manager()

# Configure provider
ai.set_provider(
    provider=AIProvider.GEMINI,
    api_key="your-key"
)

# Generate response
response = ai.generate("Your prompt here")
print(response.text)
```

## Supported Providers 🌐

| Provider | Models | Best For | Cost |
|----------|--------|----------|------|
| **Gemini** | `gemini-1.5-flash`, `gemini-1.5-pro` | General use, fast | Free tier |
| **OpenAI** | `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo` | Industry standard | $$ |
| **Grok** | `grok-beta` | Fast responses | $ |
| **Claude** | `claude-3-5-sonnet`, `claude-3-opus` | Reasoning, analysis | $$ |
| **DeepSeek** | `deepseek-chat`, `deepseek-coder` | Cost-effective | $ |

## Usage Examples 📚

### Basic Usage

```python
from src.Modules.AI_module import get_ai_manager, AIProvider

ai = get_ai_manager()
ai.set_provider(AIProvider.GEMINI, api_key="your-key")

response = ai.generate("Explain Pomodoro technique")
if not response.error:
    print(response.text)
```

### Using Prompt Templates

```python
from src.Modules.AI_module import PromptTemplates

# Alarm suggestions
prompt = PromptTemplates.alarm_suggestion(
    context="User has meeting at 10 AM"
)

# Pomodoro analysis
prompt = PromptTemplates.pomodoro_analysis(
    session_data="8 sessions, 23 min avg"
)

# Task prioritization
prompt = PromptTemplates.task_prioritization([
    "Fix bug",
    "Write docs",
    "Team meeting"
])
```

### Switching Providers

```python
# Try Gemini first
ai.set_provider(AIProvider.GEMINI, api_key=gemini_key)
response = ai.generate(prompt)

# Fallback to OpenAI if needed
if response.error:
    ai.set_provider(AIProvider.OPENAI, api_key=openai_key)
    response = ai.generate(prompt)
```

### Caching Responses

```python
# First call generates new response
response1 = ai.generate("What is AI?", use_cache=True)

# Second call uses cached response (faster, cheaper)
response2 = ai.generate("What is AI?", use_cache=True)

# Clear cache when needed
ai.clear_cache()
```

## Configuration ⚙️

### Via Code

```python
ai.set_provider(
    provider=AIProvider.GEMINI,
    api_key="your-key",
    model="gemini-1.5-flash",
    temperature=0.7,        # 0.0-1.0 (creativity)
    max_tokens=2048,        # Response length
    timeout=30              # Request timeout (seconds)
)
```

### Via UI

Open AI Settings dialog:
```python
from src.ui.ai_settings import AISettingsDialog

dialog = AISettingsDialog(parent=self)
dialog.exec()
```

### Via Environment Variables

```bash
# API Keys
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
CLAUDE_API_KEY=your-key
GROK_API_KEY=your-key
DEEPSEEK_API_KEY=your-key

# Default Settings
AI_DEFAULT_PROVIDER=gemini
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=2048
AI_TIMEOUT=30
```

## Integration Examples 🔗

### Alarms Module

```python
def suggest_alarms_for_task(task: str):
    """Get AI-powered alarm suggestions"""
    ai = get_ai_manager()
    prompt = PromptTemplates.alarm_suggestion(
        context=f"Task: {task}"
    )
    response = ai.generate(prompt)
    return response.text if not response.error else None
```

### Pomodoro Module

```python
def analyze_productivity(sessions: list):
    """Analyze Pomodoro sessions with AI"""
    ai = get_ai_manager()
    
    data = f"{len(sessions)} sessions completed"
    prompt = PromptTemplates.pomodoro_analysis(data)
    
    response = ai.generate(prompt)
    return response.text if not response.error else None
```

## Best Practices 💡

1. **Secure API Keys**: Use environment variables, never hardcode
2. **Enable Caching**: Reuse responses for identical prompts
3. **Handle Errors**: Always check `response.error`
4. **Monitor Usage**: Check `response.usage` for token counts
5. **Choose Right Model**: Use faster models for simple tasks
6. **Set Limits**: Configure `max_tokens` to control costs
7. **Test Connection**: Use AI Settings dialog to verify API keys

## Error Handling 🛡️

```python
response = ai.generate(prompt)

if response.error:
    # Handle error
    print(f"AI Error: {response.error}")
    # Fallback logic
    default_response = "AI unavailable"
else:
    # Use response
    print(response.text)
    print(f"Tokens used: {response.usage}")
```

## API Reference 📖

### AIManager

- `set_provider(provider, api_key, model=None, temperature=0.7, max_tokens=None, **kwargs)` - Configure AI provider
- `generate(prompt, use_cache=True, **kwargs)` - Generate AI response
- `get_available_models()` - List models for current provider
- `get_current_provider()` - Get active provider
- `clear_cache()` - Clear response cache
- `set_cache_dir(path)` - Set cache directory

### AIResponse

- `text` - Generated response text
- `provider` - Provider used
- `model` - Model used
- `timestamp` - When generated
- `usage` - Token usage stats
- `error` - Error message (if any)

### PromptTemplates

- `alarm_suggestion(context)` - Generate alarm suggestions
- `pomodoro_analysis(session_data)` - Analyze Pomodoro data
- `task_prioritization(tasks)` - Prioritize task list
- `custom(module, context, instruction)` - Custom prompt

## Testing 🧪

Run examples:
```bash
python examples/ai_usage_examples.py
```

Test specific provider:
```python
from examples.ai_usage_examples import example_basic_usage
example_basic_usage()
```

## Troubleshooting 🔧

### "Import could not be resolved"
```bash
pip install google-generativeai openai anthropic
```

### "Invalid API key"
- Check key in environment variables or settings
- Verify key is active on provider's website

### "Rate limit exceeded"
- Wait a few seconds between requests
- Consider upgrading API plan

### "Request timeout"
- Increase timeout in settings
- Check internet connection

## Documentation 📚

- [Full Documentation](../docs/AI_MODULE_DOCUMENTATION.md)
- [Usage Examples](../examples/ai_usage_examples.py)
- Provider Docs:
  - [Gemini](https://ai.google.dev/docs)
  - [OpenAI](https://platform.openai.com/docs)
  - [Grok](https://docs.x.ai/)
  - [Claude](https://docs.anthropic.com/)
  - [DeepSeek](https://platform.deepseek.com/docs)

## License 📄

Part of PRO-Ka-Po application.

---

**Made with ❤️ for PRO-Ka-Po**
