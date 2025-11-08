"""
AI Module - Universal AI Integration for PRO-Ka-Po Application

Supports multiple AI providers:
- Google Gemini
- OpenAI (GPT-4, GPT-3.5)
- Grok (X.AI)
- Claude (Anthropic)
- DeepSeek

Usage:
    from src.Modules.AI_module.ai_logic import get_ai_manager, AIProvider
    
    ai_manager = get_ai_manager()
    ai_manager.set_provider(AIProvider.GEMINI, api_key="your_key")
    response = ai_manager.generate("Your prompt here")
"""

import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from src.config import (
    AI_API_KEYS,
    AI_CACHE_DIR,
    AI_DEFAULT_PROVIDER,
    AI_MAX_TOKENS,
    AI_SETTINGS_FILE,
    AI_TEMPERATURE,
)

# ==================== ENUMS ====================

class AIProvider(Enum):
    """Supported AI providers"""
    GEMINI = "gemini"
    OPENAI = "openai"
    GROK = "grok"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"


class AIModel(Enum):
    """Available AI models per provider"""
    # Gemini models
    GEMINI_PRO = "gemini-pro"
    GEMINI_PRO_VISION = "gemini-pro-vision"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    
    # OpenAI models
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4O = "gpt-4o"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    
    # Grok models
    GROK_1 = "grok-1"
    GROK_BETA = "grok-beta"
    
    # Claude models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"
    
    # DeepSeek models
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_CODER = "deepseek-coder"


# ==================== DATA CLASSES ====================

@dataclass
class AIConfig:
    """Configuration for AI provider"""
    provider: AIProvider
    api_key: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """Standardized AI response"""
    text: str
    provider: AIProvider
    model: str
    timestamp: datetime
    usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "text": self.text,
            "provider": self.provider.value,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "usage": self.usage,
            "metadata": self.metadata,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIResponse':
        """Create from dictionary"""
        return cls(
            text=data["text"],
            provider=AIProvider(data["provider"]),
            model=data["model"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            usage=data.get("usage"),
            metadata=data.get("metadata", {}),
            error=data.get("error")
        )


# ==================== ABSTRACT BASE CLASS ====================

class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.logger = logging.getLogger(f"AI.{config.provider.value}")
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """
        Generate AI response from prompt
        
        Args:
            prompt: Input text prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            AIResponse object with generated text and metadata
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass
    
    def _create_response(self, text: str, model: str, 
                        usage: Optional[Dict] = None,
                        error: Optional[str] = None) -> AIResponse:
        """Helper to create standardized response"""
        return AIResponse(
            text=text,
            provider=self.config.provider,
            model=model,
            timestamp=datetime.now(),
            usage=usage,
            error=error
        )


# ==================== PROVIDER IMPLEMENTATIONS ====================

class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider using REST API"""
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
    
    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using Gemini REST API"""
        try:
            model_name = self.config.model or AIModel.GEMINI_1_5_FLASH.value
            url = f"{self.BASE_URL}/models/{model_name}:generateContent?key={self.config.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "maxOutputTokens": kwargs.get("max_tokens", self.config.max_tokens or 2048),
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                
                return self._create_response(
                    text=text,
                    model=model_name,
                    usage={
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0)
                    } if usage else None
                )
            else:
                raise Exception("No candidates in response")
            
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            return self._create_response(
                text="",
                model=self.config.model or "gemini-1.5-flash",
                error=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available Gemini models by querying API"""
        try:
            url = f"{self.BASE_URL}/models?key={self.config.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model in data.get("models", []):
                model_name = model.get("name", "").replace("models/", "")
                if "gemini" in model_name.lower() and "generateContent" in model.get("supportedGenerationMethods", []):
                    models.append(model_name)
            
            return models if models else [
                AIModel.GEMINI_PRO.value,
                AIModel.GEMINI_PRO_VISION.value,
                AIModel.GEMINI_1_5_PRO.value,
                AIModel.GEMINI_1_5_FLASH.value
            ]
        except:
            return [
                AIModel.GEMINI_PRO.value,
                AIModel.GEMINI_PRO_VISION.value,
                AIModel.GEMINI_1_5_PRO.value,
                AIModel.GEMINI_1_5_FLASH.value
            ]


class OpenAIProvider(BaseAIProvider):
    """OpenAI (GPT) Provider using REST API"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
    
    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using OpenAI REST API"""
        try:
            model_name = self.config.model or AIModel.GPT_4O.value
            url = f"{self.BASE_URL}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
            
            if self.config.max_tokens:
                payload["max_tokens"] = kwargs.get("max_tokens", self.config.max_tokens)
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            usage = data.get("usage", {})
            
            return self._create_response(
                text=data["choices"][0]["message"]["content"],
                model=model_name,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                } if usage else None
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return self._create_response(
                text="",
                model=self.config.model or "gpt-4o",
                error=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available OpenAI models"""
        try:
            url = f"{self.BASE_URL}/models"
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model in data.get("data", []):
                model_id = model.get("id", "")
                if "gpt" in model_id.lower():
                    models.append(model_id)
            
            return models if models else [
                AIModel.GPT_4.value,
                AIModel.GPT_4_TURBO.value,
                AIModel.GPT_4O.value,
                AIModel.GPT_3_5_TURBO.value
            ]
        except:
            return [
                AIModel.GPT_4.value,
                AIModel.GPT_4_TURBO.value,
                AIModel.GPT_4O.value,
                AIModel.GPT_3_5_TURBO.value
            ]


class GrokProvider(BaseAIProvider):
    """Grok (X.AI) Provider using OpenAI-compatible REST API"""
    
    BASE_URL = "https://api.x.ai/v1"
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
    
    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using Grok REST API"""
        try:
            model_name = self.config.model or AIModel.GROK_BETA.value
            url = f"{self.BASE_URL}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
            
            if self.config.max_tokens:
                payload["max_tokens"] = kwargs.get("max_tokens", self.config.max_tokens)
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            usage = data.get("usage", {})
            
            return self._create_response(
                text=data["choices"][0]["message"]["content"],
                model=model_name,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                } if usage else None
            )
            
        except Exception as e:
            self.logger.error(f"Grok API error: {e}")
            return self._create_response(
                text="",
                model=self.config.model or "grok-beta",
                error=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available Grok models"""
        return [
            AIModel.GROK_1.value,
            AIModel.GROK_BETA.value
        ]


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude Provider using REST API"""
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
    
    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using Claude REST API"""
        try:
            model_name = self.config.model or AIModel.CLAUDE_3_5_SONNET.value
            url = f"{self.BASE_URL}/messages"
            
            headers = {
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_name,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens or 1024),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            usage = data.get("usage", {})
            
            return self._create_response(
                text=data["content"][0]["text"],
                model=model_name,
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                } if usage else None
            )
            
        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            return self._create_response(
                text="",
                model=self.config.model or "claude-3-5-sonnet",
                error=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available Claude models"""
        return [
            AIModel.CLAUDE_3_OPUS.value,
            AIModel.CLAUDE_3_SONNET.value,
            AIModel.CLAUDE_3_HAIKU.value,
            AIModel.CLAUDE_3_5_SONNET.value
        ]


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek AI Provider using OpenAI-compatible REST API"""
    
    BASE_URL = "https://api.deepseek.com/v1"
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
    
    def generate_response(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using DeepSeek REST API"""
        try:
            model_name = self.config.model or AIModel.DEEPSEEK_CHAT.value
            url = f"{self.BASE_URL}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
            
            if self.config.max_tokens:
                payload["max_tokens"] = kwargs.get("max_tokens", self.config.max_tokens)
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            usage = data.get("usage", {})
            
            return self._create_response(
                text=data["choices"][0]["message"]["content"],
                model=model_name,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                } if usage else None
            )
            
        except Exception as e:
            self.logger.error(f"DeepSeek API error: {e}")
            return self._create_response(
                text="",
                model=self.config.model or "deepseek-chat",
                error=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available DeepSeek models"""
        return [
            AIModel.DEEPSEEK_CHAT.value,
            AIModel.DEEPSEEK_CODER.value
        ]


# ==================== AI MANAGER ====================

class AIManager:
    """
    Central AI Manager - Singleton
    
    Manages AI provider selection, configuration, and response generation.
    Handles caching and provider switching.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.logger = logging.getLogger("AIManager")
            self._current_provider: Optional[BaseAIProvider] = None
            self._config: Optional[AIConfig] = None
            self._cache_dir: Optional[Path] = None
            self._response_cache: Dict[str, AIResponse] = {}
            self._initialized = True
    
    def set_provider(self, 
                     provider: AIProvider, 
                     api_key: str,
                     model: Optional[str] = None,
                     temperature: float = 0.7,
                     max_tokens: Optional[int] = None,
                     **kwargs) -> None:
        """
        Set and configure AI provider
        
        Args:
            provider: AIProvider enum
            api_key: API key for the provider
            model: Specific model to use (optional)
            temperature: Response randomness (0.0-1.0)
            max_tokens: Maximum response length
            **kwargs: Additional provider-specific parameters
        """
        config = AIConfig(
            provider=provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=kwargs
        )
        
        self._config = config
        
        # Create appropriate provider instance
        provider_map = {
            AIProvider.GEMINI: GeminiProvider,
            AIProvider.OPENAI: OpenAIProvider,
            AIProvider.GROK: GrokProvider,
            AIProvider.CLAUDE: ClaudeProvider,
            AIProvider.DEEPSEEK: DeepSeekProvider
        }
        
        provider_class = provider_map.get(provider)
        if provider_class:
            self._current_provider = provider_class(config)
            self.logger.info(f"AI Provider set to: {provider.value}")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate(self, 
                prompt: str, 
                use_cache: bool = True,
                **kwargs) -> AIResponse:
        """
        Generate AI response
        
        Args:
            prompt: Input prompt text
            use_cache: Whether to use cached responses
            **kwargs: Additional generation parameters
            
        Returns:
            AIResponse object
            
        Raises:
            ValueError: If no provider is configured
        """
        if self._current_provider is None:
            raise ValueError(
                "No AI provider configured. Call set_provider() first."
            )
        
        # Check cache
        cache_key = self._get_cache_key(prompt)
        if use_cache and cache_key in self._response_cache:
            self.logger.debug(f"Using cached response for prompt")
            return self._response_cache[cache_key]
        
        # Generate new response
        response = self._current_provider.generate_response(prompt, **kwargs)
        
        # Cache successful responses
        if not response.error and use_cache:
            self._response_cache[cache_key] = response
            self._save_to_cache(cache_key, response)
        
        return response
    
    def get_available_models(self) -> List[str]:
        """Get available models for current provider"""
        if self._current_provider is None:
            return []
        return self._current_provider.get_available_models()
    
    def get_current_provider(self) -> Optional[AIProvider]:
        """Get currently configured provider"""
        return self._config.provider if self._config else None
    
    def transcribe_audio(self, audio_file_path: str, language: str = "pl") -> str:
        """
        Transkrybuj plik audio używając skonfigurowanego AI providera.
        
        Obsługiwane providery:
        - Google Gemini (gemini-1.5-pro, gemini-1.5-flash)
        - OpenAI Whisper
        
        Args:
            audio_file_path: Ścieżka do pliku audio
            language: Kod języka (domyślnie "pl" dla polskiego)
            
        Returns:
            Transkrybowany tekst
            
        Raises:
            ValueError: Jeśli provider nie jest skonfigurowany lub nie obsługuje transkrypcji
            FileNotFoundError: Jeśli plik audio nie istnieje
        """
        from pathlib import Path
        import mimetypes
        
        # Sprawdź czy plik istnieje
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Sprawdź czy provider jest skonfigurowany
        if self._config is None:
            raise ValueError(
                "No AI provider configured. "
                "Call set_provider() first."
            )
        
        provider = self._config.provider
        
        # === GOOGLE GEMINI ===
        if provider == AIProvider.GEMINI:
            try:
                import base64
                
                # Użyj modelu z konfiguracji, jeśli nie ma - spróbuj załadować z ustawień
                model_name = self._config.model
                if not model_name:
                    # Próba załadowania z pliku ustawień
                    settings = load_ai_settings()
                    model_name = settings.get('models', {}).get('gemini')
                
                # Jeśli nadal brak - użyj domyślnego
                if not model_name:
                    model_name = "gemini-1.5-flash"
                    self.logger.warning(
                        f"[AIManager] No Gemini model configured, using default: {model_name}"
                    )
                
                # Sprawdź czy model obsługuje audio
                if not any(version in model_name for version in ["1.5", "2.0", "2.5"]):
                    raise ValueError(
                        f"Model {model_name} does not support audio transcription.\n"
                        f"Supported Gemini models: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash, gemini-2.5-pro"
                    )
                
                self.logger.info(f"Transcribing audio with Gemini ({model_name}): {audio_path.name}")
                
                # Wczytaj plik audio i zakoduj do base64
                with open(audio_file_path, 'rb') as audio_file:
                    audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
                
                # Określ MIME type
                mime_type, _ = mimetypes.guess_type(audio_file_path)
                if not mime_type:
                    # Domyślne MIME types dla popularnych formatów
                    ext = audio_path.suffix.lower()
                    mime_types_map = {
                        '.mp3': 'audio/mp3',
                        '.wav': 'audio/wav',
                        '.m4a': 'audio/mp4',
                        '.amr': 'audio/amr',
                        '.ogg': 'audio/ogg',
                        '.flac': 'audio/flac'
                    }
                    mime_type = mime_types_map.get(ext, 'audio/mpeg')
                
                # Stwórz prompt do transkrypcji
                prompt = f"""Dokonaj transkrypcji tego nagrania audio na język polski.

Zasady:
1. Transkrybuj dokładnie wszystkie wypowiedziane słowa
2. Zachowaj naturalny podział na zdania i akapity
3. Użyj poprawnej interpunkcji polskiej
4. Jeśli w nagraniu jest kilka osób, oznacz kto mówi (np. "Osoba 1:", "Osoba 2:")
5. W przypadku niezrozumiałych fragmentów użyj [niezrozumiałe]

Zwróć tylko czystą transkrypcję bez dodatkowych komentarzy."""
                
                # Przygotuj request do Gemini API
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers = {
                    'Content-Type': 'application/json'
                }
                params = {
                    'key': self._config.api_key
                }
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": audio_data
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 8192,
                    }
                }
                
                # Wyślij request
                response = requests.post(url, headers=headers, params=params, json=payload, timeout=120)
                response.raise_for_status()
                
                # Parsuj odpowiedź
                result = response.json()
                self.logger.debug(f"Gemini API response: {result}")
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    
                    # Sprawdź różne formaty odpowiedzi
                    transcription_text = None
                    
                    # Format 1: content.parts[0].text
                    if 'content' in candidate and 'parts' in candidate['content']:
                        parts = candidate['content']['parts']
                        if len(parts) > 0 and 'text' in parts[0]:
                            transcription_text = parts[0]['text']
                    
                    # Format 2: text bezpośrednio w candidate
                    elif 'text' in candidate:
                        transcription_text = candidate['text']
                    
                    # Format 3: output/generated_text
                    elif 'output' in candidate:
                        transcription_text = candidate['output']
                    
                    if transcription_text and transcription_text.strip():
                        self.logger.info(f"Gemini transcription completed: {len(transcription_text)} characters")
                        return transcription_text
                    else:
                        # Pusta odpowiedź - może być thinking tokens bez output
                        self.logger.warning(f"Gemini returned empty transcription. Model: {model_name}, Response: {result}")
                        # Rzuć wyjątek żeby można było spróbować fallback
                        raise ValueError(f"Model {model_name} returned empty transcription (may not support audio properly)")
                
                # Jeśli nie udało się pobrać tekstu
                self.logger.error(f"Unexpected response format from Gemini API: {result}")
                raise ValueError(f"Unexpected response format - no candidates in response")
                
            except requests.RequestException as e:
                self.logger.error(f"Gemini API request failed: {e}")
                raise ValueError(f"Gemini API request failed: {str(e)}")
            except Exception as e:
                self.logger.error(f"Gemini transcription failed: {e}")
                raise
        
        # === OPENAI WHISPER ===
        elif provider == AIProvider.OPENAI:
            try:
                import openai
                
                # Konfiguracja OpenAI
                openai.api_key = self._config.api_key
                
                # Otwórz plik audio
                with open(audio_file_path, 'rb') as audio_file:
                    # Wywołaj Whisper API
                    self.logger.info(f"Transcribing audio with Whisper: {audio_path.name}")
                    
                    response = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=language,
                        response_format="text"
                    )
                    
                    transcription_text = response if isinstance(response, str) else response.text
                    
                    self.logger.info(f"Whisper transcription completed: {len(transcription_text)} characters")
                    return transcription_text
                    
            except ImportError:
                raise ValueError(
                    "OpenAI library not installed. "
                    "Install it with: pip install openai"
                )
            except Exception as e:
                self.logger.error(f"Whisper transcription failed: {e}")
                raise
        
        # === INNE PROVIDERY (NIE OBSŁUGUJĄ) ===
        else:
            raise ValueError(
                f"Provider '{provider.value}' does not support audio transcription.\n\n"
                f"Polecani dostawcy z obsługą transkrypcji:\n"
                f"• Google Gemini (gemini-1.5-pro, gemini-1.5-flash)\n"
                f"• OpenAI Whisper\n\n"
                f"Skonfiguruj innego dostawcę w Ustawieniach → AI"
            )
    
    def summarize_audio(self, 
                       audio_file_path: str, 
                       additional_prompt: str = "", 
                       language: str = "pl") -> str:
        """
        Podsumuj plik audio używając skonfigurowanego AI providera.
        
        Jeśli provider obsługuje audio bezpośrednio (Gemini 1.5+), wyśle plik.
        W przeciwnym razie najpierw transkrybuje, a potem podsumowuje.
        
        Args:
            audio_file_path: Ścieżka do pliku audio
            additional_prompt: Dodatkowy prompt od użytkownika
            language: Kod języka (domyślnie "pl")
            
        Returns:
            Tekst podsumowania w formacie JSON z polami "summary" i "tasks"
        """
        import base64
        import mimetypes
        from pathlib import Path
        
        # Sprawdź czy plik istnieje
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Sprawdź czy provider jest skonfigurowany
        if self._config is None:
            raise ValueError("No AI provider configured.")
        
        provider = self._config.provider
        
        # === GEMINI - obsługuje audio bezpośrednio ===
        if provider == AIProvider.GEMINI:
            try:
                model_name = self._config.model
                if not model_name:
                    settings = load_ai_settings()
                    model_name = settings.get('models', {}).get('gemini', 'gemini-1.5-flash')
                
                # Sprawdź czy model obsługuje audio
                if not any(version in model_name for version in ["1.5", "2.0", "2.5"]):
                    # Fallback - transkrybuj a potem podsumuj
                    self.logger.info(f"Model {model_name} doesn't support audio, falling back to transcription")
                    transcription = self.transcribe_audio(audio_file_path, language)
                    return self._summarize_text(transcription, additional_prompt)
                
                self.logger.info(f"Summarizing audio with Gemini ({model_name}): {audio_path.name}")
                
                # Wczytaj audio jako base64
                with open(audio_file_path, 'rb') as audio_file:
                    audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
                
                # MIME type
                mime_type, _ = mimetypes.guess_type(audio_file_path)
                if not mime_type:
                    ext = audio_path.suffix.lower()
                    mime_types_map = {
                        '.mp3': 'audio/mp3',
                        '.wav': 'audio/wav',
                        '.m4a': 'audio/mp4',
                        '.amr': 'audio/amr',
                        '.ogg': 'audio/ogg',
                        '.flac': 'audio/flac'
                    }
                    mime_type = mime_types_map.get(ext, 'audio/mpeg')
                
                # Prompt do podsumowania
                standard_prompt = """Przeanalizuj to nagranie rozmowy i stwórz:

1. PODSUMOWANIE - zwięzłe podsumowanie rozmowy (2-3 akapity) zawierające:
   - główne tematy omawiane w rozmowie
   - kluczowe ustalenia i decyzje
   - ważne informacje przekazane przez uczestników

2. ZADANIA - listę konkretnych zadań do wykonania wynikających z rozmowy:
   - każde zadanie w osobnej linii
   - używaj formatu: "- [konkretne zadanie]"
   - wypisz TYLKO zadania które wynikają bezpośrednio z rozmowy

Zwróć odpowiedź w formacie JSON:
{
  "summary": "tekst podsumowania",
  "tasks": ["zadanie 1", "zadanie 2", "zadanie 3"]
}
"""
                
                if additional_prompt:
                    standard_prompt += f"\n\nDodatkowe instrukcje:\n{additional_prompt}"
                
                # Request do Gemini
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                params = {'key': self._config.api_key}
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": standard_prompt},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": audio_data
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 8192,
                    }
                }
                
                response = requests.post(url, params=params, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    summary_text = result['candidates'][0]['content']['parts'][0]['text']
                    self.logger.info(f"Gemini audio summary completed")
                    return summary_text
                
                raise ValueError(f"Unexpected Gemini response: {result}")
                
            except Exception as e:
                self.logger.error(f"Gemini audio summary failed: {e}")
                raise
        
        # === INNE PROVIDERY - transkrybuj najpierw ===
        else:
            self.logger.info(f"Provider {provider.value} doesn't support audio directly, transcribing first")
            transcription = self.transcribe_audio(audio_file_path, language)
            return self._summarize_text(transcription, additional_prompt)
    
    def _summarize_text(self, text: str, additional_prompt: str = "") -> str:
        """Podsumuj tekst używając aktywnego providera."""
        standard_prompt = f"""Przeanalizuj tę transkrypcję rozmowy:

{text}

Stwórz:

1. PODSUMOWANIE - zwięzłe podsumowanie (2-3 akapity) zawierające:
   - główne tematy
   - kluczowe ustalenia
   - ważne informacje

2. ZADANIA - lista zadań do wykonania:
   - format: "- [zadanie]"
   - tylko zadania wynikające z rozmowy

Zwróć JSON:
{{
  "summary": "podsumowanie",
  "tasks": ["zadanie 1", "zadanie 2"]
}}
"""
        
        if additional_prompt:
            standard_prompt += f"\n\nDodatkowe instrukcje:\n{additional_prompt}"
        
        response = self.generate(standard_prompt, use_cache=False)
        
        if response.error:
            raise ValueError(f"AI summarization failed: {response.error}")
        
        return response.text
    
    def clear_cache(self) -> None:
        """Clear response cache"""
        self._response_cache.clear()
        self.logger.info("Response cache cleared")
    
    def set_cache_dir(self, cache_dir: Path) -> None:
        """Set directory for persistent cache"""
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt"""
        import hashlib
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def _save_to_cache(self, key: str, response: AIResponse) -> None:
        """Save response to persistent cache"""
        if self._cache_dir is None:
            return
        
        try:
            cache_file = self._cache_dir / f"{key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(response.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
    
    def _load_from_cache(self, key: str) -> Optional[AIResponse]:
        """Load response from persistent cache"""
        if self._cache_dir is None:
            return None
        
        try:
            cache_file = self._cache_dir / f"{key}.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AIResponse.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load cache: {e}")
        
        return None


# ==================== GLOBAL INSTANCE ====================

_ai_manager_instance: Optional[AIManager] = None


def get_ai_manager() -> AIManager:
    """Get global AI Manager instance (Singleton)"""
    global _ai_manager_instance
    if _ai_manager_instance is None:
        _ai_manager_instance = AIManager()
    return _ai_manager_instance


def load_ai_settings() -> Dict[str, Any]:
    """Load persisted AI settings from disk."""
    if AI_SETTINGS_FILE.exists():
        try:
            with open(AI_SETTINGS_FILE, 'r', encoding='utf-8') as handle:
                return json.load(handle)
        except Exception as exc:  # pragma: no cover - defensive
            logging.getLogger("AIManager").error(f"Failed to load AI settings: {exc}")
    return {}


def configure_ai_manager_from_settings(
    force_reload: bool = False,
) -> Tuple[Optional[AIManager], Dict[str, Any], Optional[str]]:
    """Configure AI manager using stored settings.

    Returns a tuple of (manager, settings, error_message). If configuration fails,
    manager will be None and error_message will contain the reason (e.g. 'missing_api_key').
    """

    settings = load_ai_settings()
    provider_value = settings.get('provider', AI_DEFAULT_PROVIDER)

    try:
        provider = AIProvider(provider_value)
    except ValueError:
        return None, settings, f"unsupported_provider:{provider_value}"

    api_keys = settings.get('api_keys', {})
    api_key = api_keys.get(provider_value) or AI_API_KEYS.get(provider_value, '')
    if not api_key:
        return None, settings, "missing_api_key"

    selected_model = settings.get('models', {}).get(provider_value)
    temperature = settings.get('temperature', AI_TEMPERATURE)
    max_tokens = settings.get('max_tokens', AI_MAX_TOKENS)

    manager = get_ai_manager()
    current_provider = manager.get_current_provider()

    if force_reload or current_provider != provider:
        try:
            manager.set_provider(
                provider=provider,
                api_key=api_key,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            manager.set_cache_dir(AI_CACHE_DIR)
        except Exception as exc:
            logging.getLogger("AIManager").error(f"Failed to configure AI manager: {exc}")
            return None, settings, str(exc)

    return manager, settings, None


# ==================== PROMPT TEMPLATES ====================

class PromptTemplates:
    """Predefined prompt templates for different modules"""
    
    @staticmethod
    def alarm_suggestion(context: str) -> str:
        """Generate prompt for alarm suggestions"""
        return f"""
You are an AI assistant helping with task and alarm management.

Context: {context}

Based on the context, suggest 3-5 relevant alarms or reminders that would help the user stay organized.
For each suggestion, provide:
1. Alarm title (brief, clear)
2. Recommended time
3. Brief justification

Format your response as a JSON array.
"""
    
    @staticmethod
    def pomodoro_analysis(session_data: str) -> str:
        """Generate prompt for Pomodoro session analysis"""
        return f"""
You are a productivity coach analyzing Pomodoro sessions.

Session Data: {session_data}

Analyze the user's productivity patterns and provide:
1. Key insights about focus and break patterns
2. Suggestions for improvement
3. Optimal work/break duration recommendations

Be concise and actionable.
"""
    
    @staticmethod
    def task_prioritization(tasks: List[str]) -> str:
        """Generate prompt for task prioritization"""
        tasks_text = "\n".join([f"- {task}" for task in tasks])
        return f"""
You are a productivity expert helping prioritize tasks.

Tasks:
{tasks_text}

Analyze and suggest:
1. Priority order (with reasoning)
2. Estimated time for each task
3. Potential dependencies or blockers

Provide your analysis in a structured format.
"""
    
    @staticmethod
    def custom(module: str, context: str, instruction: str) -> str:
        """Generate custom prompt for any module"""
        return f"""
Module: {module}
Context: {context}

Instruction: {instruction}

Provide a helpful, concise response.
"""


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Example: How to use the AI Manager
    
    # Get manager instance
    ai = get_ai_manager()
    
    # Configure Gemini provider
    ai.set_provider(
        provider=AIProvider.GEMINI,
        api_key="your-api-key-here",
        model=AIModel.GEMINI_1_5_FLASH.value,
        temperature=0.7
    )
    
    # Generate response
    prompt = PromptTemplates.alarm_suggestion("User has a meeting tomorrow at 10 AM")
    response = ai.generate(prompt)
    
    if response.error:
        print(f"Error: {response.error}")
    else:
        print(f"Response: {response.text}")
        print(f"Model: {response.model}")
        print(f"Usage: {response.usage}")
