"""
AI Module for PRO-Ka-Po Application

Provides unified interface for multiple AI providers:
- Google Gemini
- OpenAI (GPT-4, GPT-3.5)
- Grok (X.AI)
- Claude (Anthropic)
- DeepSeek
"""

from .ai_logic import (
    # Main manager
    AIManager,
    get_ai_manager,
    
    # Enums
    AIProvider,
    AIModel,
    
    # Data classes
    AIConfig,
    AIResponse,
    
    # Prompt templates
    PromptTemplates,
    
    # Provider implementations
    BaseAIProvider,
    GeminiProvider,
    OpenAIProvider,
    GrokProvider,
    ClaudeProvider,
    DeepSeekProvider
)

__all__ = [
    # Main
    'AIManager',
    'get_ai_manager',
    
    # Enums
    'AIProvider',
    'AIModel',
    
    # Data classes
    'AIConfig',
    'AIResponse',
    
    # Prompts
    'PromptTemplates',
    
    # Providers
    'BaseAIProvider',
    'GeminiProvider',
    'OpenAIProvider',
    'GrokProvider',
    'ClaudeProvider',
    'DeepSeekProvider'
]
