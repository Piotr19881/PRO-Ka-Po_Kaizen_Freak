"""
AI Settings Tab - Karta ustawień AI w widoku Settings
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGroupBox, QMessageBox, QTextEdit,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont
from loguru import logger

from ..utils.i18n_manager import t, get_i18n
from ..config import AI_API_KEYS, AI_DEFAULT_PROVIDER, AI_SETTINGS_FILE, AI_CACHE_DIR, AI_TEMPERATURE, AI_TIMEOUT
from ..Modules.AI_module import get_ai_manager, AIProvider


class AITestThread(QThread):
    """Thread for testing API connection and fetching available models"""
    test_completed = pyqtSignal(bool, str)
    models_detected = pyqtSignal(list)
    
    def __init__(self, provider, api_key):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
    
    def run(self):
        """Fetch available models without testing generation"""
        try:
            # Create temporary provider instance just to get models list
            from ..Modules.AI_module.ai_logic import AIConfig, GeminiProvider, OpenAIProvider, GrokProvider, ClaudeProvider, DeepSeekProvider
            
            provider_map = {
                AIProvider.GEMINI: GeminiProvider,
                AIProvider.OPENAI: OpenAIProvider,
                AIProvider.GROK: GrokProvider,
                AIProvider.CLAUDE: ClaudeProvider,
                AIProvider.DEEPSEEK: DeepSeekProvider
            }
            
            temp_config = AIConfig(
                provider=self.provider,
                api_key=self.api_key
            )
            
            provider_class = provider_map.get(self.provider)
            if not provider_class:
                self.test_completed.emit(False, "Nieobsługiwany provider")
                return
                
            temp_provider = provider_class(temp_config)
            available_models = temp_provider.get_available_models()
            
            self.models_detected.emit(available_models)
            
            if available_models:
                self.test_completed.emit(True, f"✅ Znaleziono {len(available_models)} modeli")
            else:
                self.test_completed.emit(False, "⚠️ Brak dostępnych modeli")
                
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            self.test_completed.emit(False, f"❌ {str(e)}")
            self.models_detected.emit([])


class AIModelTestThread(QThread):
    """Thread for testing specific model with actual generation"""
    test_completed = pyqtSignal(bool, str)
    
    def __init__(self, provider, api_key, model):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model
    
    def run(self):
        """Test actual generation with selected model"""
        try:
            ai = get_ai_manager()
            ai.set_provider(provider=self.provider, api_key=self.api_key, model=self.model)
            response = ai.generate("Reply with just: OK", use_cache=False)
            
            if response.error:
                self.test_completed.emit(False, f"❌ {response.error}")
            else:
                self.test_completed.emit(True, f"✅ Model działa! Odpowiedź: {response.text[:50]}")
        except Exception as e:
            logger.error(f"Model test error: {e}")
            self.test_completed.emit(False, f"❌ {str(e)}")


class AISettingsTab(QWidget):
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_thread = None
        self.model_test_thread = None
        self.current_settings = self._load_settings()
        self.available_models = []
        self._setup_ui()
        self._load_current_settings()
        get_i18n().language_changed.connect(self.update_translations)
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("Ustawienia AI")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        header.setFont(font)
        scroll_layout.addWidget(header)
        self.header = header
        
        # Provider group
        provider_group = QGroupBox("Wybór Providera AI")
        self.provider_group = provider_group
        provider_layout = QVBoxLayout()
        
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Google Gemini", AIProvider.GEMINI.value)
        self.provider_combo.addItem("OpenAI (GPT)", AIProvider.OPENAI.value)
        self.provider_combo.addItem("Grok (X.AI)", AIProvider.GROK.value)
        self.provider_combo.addItem("Claude (Anthropic)", AIProvider.CLAUDE.value)
        self.provider_combo.addItem("DeepSeek", AIProvider.DEEPSEEK.value)
        provider_row.addWidget(self.provider_combo, 1)
        provider_layout.addLayout(provider_row)
        
        self.provider_desc = QLabel("")
        self.provider_desc.setWordWrap(True)
        provider_layout.addWidget(self.provider_desc)
        provider_group.setLayout(provider_layout)
        scroll_layout.addWidget(provider_group)
        
        # API Key group
        api_group = QGroupBox("Klucz API")
        self.api_group = api_group
        api_layout = QVBoxLayout()
        
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(self.api_key_input, 1)
        self.show_key_btn = QPushButton("👁️")
        self.show_key_btn.setFixedWidth(40)
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(lambda c: self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        key_row.addWidget(self.show_key_btn)
        api_layout.addLayout(key_row)
        
        self.get_key_label = QLabel("")
        self.get_key_label.setOpenExternalLinks(True)
        api_layout.addWidget(self.get_key_label)
        
        self.test_button = QPushButton("Test Połączenia")
        self.test_button.clicked.connect(self._test_connection)
        api_layout.addWidget(self.test_button)
        
        self.models_label = QLabel("")
        self.models_label.setStyleSheet("color: #2196F3;")
        api_layout.addWidget(self.models_label)
        
        # Model selection (shown after successful test)
        self.model_selection_widget = QWidget()
        model_selection_layout = QVBoxLayout(self.model_selection_widget)
        model_selection_layout.setContentsMargins(0, 10, 0, 0)
        
        self.model_label = QLabel("Wybierz model:")
        self.model_label.setStyleSheet("font-weight: bold;")
        model_selection_layout.addWidget(self.model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(30)
        model_selection_layout.addWidget(self.model_combo)
        
        # Test selected model button
        self.test_model_button = QPushButton("🧪 Test wybranego modelu")
        self.test_model_button.clicked.connect(self._test_selected_model)
        self.test_model_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        model_selection_layout.addWidget(self.test_model_button)
        
        # Model test result label
        self.model_test_label = QLabel("")
        self.model_test_label.setWordWrap(True)
        model_selection_layout.addWidget(self.model_test_label)
        
        api_layout.addWidget(self.model_selection_widget)
        self.model_selection_widget.setVisible(False)  # Hidden by default
        
        api_group.setLayout(api_layout)
        scroll_layout.addWidget(api_group)
        
        # System Prompt group
        prompt_group = QGroupBox("Własny Prompt Systemowy")
        self.prompt_group = prompt_group
        prompt_layout = QVBoxLayout()
        
        prompt_layout.addWidget(QLabel("Dodaj własny tekst do wszystkich promptów:"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlaceholderText("np. 'Odpowiadaj zawsze w języku polskim...'")
        self.system_prompt_input.setMinimumHeight(100)
        self.system_prompt_input.setMaximumHeight(200)
        prompt_layout.addWidget(self.system_prompt_input)
        
        prompt_group.setLayout(prompt_layout)
        scroll_layout.addWidget(prompt_group)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.status_label)
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.clear_cache_btn = QPushButton("Wyczyść Cache")
        self.clear_cache_btn.clicked.connect(self._clear_cache)
        buttons.addWidget(self.clear_cache_btn)
        self.save_button = QPushButton("Zapisz")
        self.save_button.clicked.connect(self._save_settings)
        buttons.addWidget(self.save_button)
        scroll_layout.addLayout(buttons)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Connect signals
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self._on_provider_changed(0)
        
        # Initialize translations
        self.update_translations()
    
    def _on_provider_changed(self, index):
        provider = AIProvider(self.provider_combo.itemData(index))
        
        # Update description with translation
        desc_keys = {
            AIProvider.GEMINI: "ai.desc_gemini",
            AIProvider.OPENAI: "ai.desc_openai",
            AIProvider.GROK: "ai.desc_grok",
            AIProvider.CLAUDE: "ai.desc_claude",
            AIProvider.DEEPSEEK: "ai.desc_deepseek"
        }
        self.provider_desc.setText(t(desc_keys.get(provider, "")))
        
        # Update API key link
        links = {
            AIProvider.GEMINI: "https://makersuite.google.com/app/apikey",
            AIProvider.OPENAI: "https://platform.openai.com/api-keys",
            AIProvider.GROK: "https://console.x.ai",
            AIProvider.CLAUDE: "https://console.anthropic.com/account/keys",
            AIProvider.DEEPSEEK: "https://platform.deepseek.com/api_keys"
        }
        link = links.get(provider, "")
        self.get_key_label.setText(f'<a href="{link}">{t("ai.get_key")}</a>' if link else "")
        
        saved_key = self.current_settings.get('api_keys', {}).get(provider.value, "")
        self.api_key_input.setText(saved_key)
    
    def _test_connection(self):
        provider = AIProvider(self.provider_combo.currentData())
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self._show_status(f"❌ {t('ai.no_api_key')}", False)
            return
        
        self.test_button.setEnabled(False)
        self.test_button.setText(t("ai.testing"))
        self.test_thread = AITestThread(provider, api_key)
        self.test_thread.test_completed.connect(self._on_test_completed)
        self.test_thread.models_detected.connect(self._on_models_detected)
        self.test_thread.start()
    
    def _test_selected_model(self):
        """Test the selected model with actual generation"""
        provider = AIProvider(self.provider_combo.currentData())
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            self._show_status(f"❌ {t('ai.no_api_key')}", False)
            return
        
        if self.model_combo.count() == 0:
            self.model_test_label.setText("⚠️ Brak wybranego modelu")
            return
        
        selected_model = self.model_combo.currentData()
        
        self.test_model_button.setEnabled(False)
        self.test_model_button.setText(t("ai.testing_model"))
        self.model_test_label.setText("⏳ Testowanie modelu...")
        
        self.model_test_thread = AIModelTestThread(provider, api_key, selected_model)
        self.model_test_thread.test_completed.connect(self._on_model_test_completed)
        self.model_test_thread.start()
    
    def _on_model_test_completed(self, success, message):
        """Handle model test completion"""
        self.test_model_button.setEnabled(True)
        self.test_model_button.setText(t("ai.test_model"))
        
        if success:
            self.model_test_label.setText(message)
            self.model_test_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.model_test_label.setText(message)
            self.model_test_label.setStyleSheet("color: #f44336; font-weight: bold;")
    
    def _on_test_completed(self, success, message):
        self.test_button.setEnabled(True)
        self.test_button.setText(t("ai.btn_test"))
        if success:
            self._show_status(t("ai.test_success"), True)
        else:
            self._show_status(f"{t('ai.test_failed')}: {message}", False)
    
    def _on_models_detected(self, models):
        """Handle detected models - populate combo box for user selection"""
        self.available_models = models
        if models:
            # Show summary
            models_text = ', '.join(models[:3]) + (f' (+{len(models)-3} więcej)' if len(models) > 3 else '')
            self.models_label.setText(f"✅ {t('ai.available_models')} {models_text}")
            
            # Populate model selection combo
            self.model_combo.clear()
            for model in models:
                self.model_combo.addItem(model, model)
            
            # Try to select previously saved model if available
            saved_model = self.current_settings.get('model')
            if saved_model and saved_model in models:
                index = self.model_combo.findData(saved_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
            
            # Show model selection widget
            self.model_selection_widget.setVisible(True)
        else:
            self.models_label.setText(f"⚠️ {t('ai.no_models')}")
            self.model_selection_widget.setVisible(False)
    
    def _clear_cache(self):
        reply = QMessageBox.question(
            self, 
            t("ai.clear_cache"), 
            t("ai.clear_cache_confirm")
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                get_ai_manager().clear_cache()
                if AI_CACHE_DIR.exists():
                    for f in AI_CACHE_DIR.glob("*.json"):
                        f.unlink()
                self._show_status(t("ai.cache_cleared"), True)
            except Exception as e:
                self._show_status(f"{t('ai.cache_clear_error')}: {e}", False)
    
    def _save_settings(self):
        try:
            provider = AIProvider(self.provider_combo.currentData())
            api_key = self.api_key_input.text().strip()
            system_prompt = self.system_prompt_input.toPlainText().strip()
            
            if not api_key:
                QMessageBox.warning(self, t("ai.validation_error"), t("ai.no_api_key"))
                return
            
            # Get selected model from combo (if visible)
            selected_model = None
            if self.model_selection_widget.isVisible() and self.model_combo.count() > 0:
                selected_model = self.model_combo.currentData()
            
            if not selected_model and not self.available_models:
                QMessageBox.warning(
                    self, 
                    t("ai.validation_error"), 
                    t("ai.test_first")
                )
                return
            
            if 'api_keys' not in self.current_settings:
                self.current_settings['api_keys'] = {}
            
            self.current_settings['provider'] = provider.value
            self.current_settings['api_keys'][provider.value] = api_key
            self.current_settings['system_prompt'] = system_prompt
            
            # Save selected model per provider
            if 'models' not in self.current_settings:
                self.current_settings['models'] = {}
            if selected_model:
                self.current_settings['models'][provider.value] = selected_model
            
            AI_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AI_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=2)
            
            # Configure AI with selected model
            ai = get_ai_manager()
            ai.set_provider(provider=provider, api_key=api_key, model=selected_model)
            ai.set_cache_dir(AI_CACHE_DIR)
            
            self._show_status(t("ai.settings_saved"), True)
            self.settings_changed.emit(self.current_settings)
            
        except Exception as e:
            QMessageBox.critical(self, t("common.error"), f"{t('ai.save_error')}: {e}")
    
    def _show_status(self, message, success):
        self.status_label.setText(message)
        color = "#4CAF50" if success else "#f44336"
        self.status_label.setStyleSheet(f"background-color: {color}; color: white; padding: 8px; border-radius: 4px;")
        if success:
            QTimer.singleShot(5000, lambda: self.status_label.setText(""))
    
    def _load_settings(self):
        if not AI_SETTINGS_FILE.exists():
            return {'provider': AI_DEFAULT_PROVIDER, 'api_keys': {}, 'system_prompt': ''}
        try:
            with open(AI_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _load_current_settings(self):
        """Load and restore saved settings including provider and selected model"""
        provider_value = self.current_settings.get('provider', AI_DEFAULT_PROVIDER)
        index = self.provider_combo.findData(provider_value)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)
        
        system_prompt = self.current_settings.get('system_prompt', '')
        self.system_prompt_input.setPlainText(system_prompt)
        
        # If there's a saved model for this provider, try to load available models
        saved_model = self.current_settings.get('models', {}).get(provider_value)
        if saved_model:
            # Auto-test to get models if we have API key
            api_key = self.current_settings.get('api_keys', {}).get(provider_value)
            if api_key:
                # Silently load models in background
                QTimer.singleShot(500, lambda: self._silent_test_connection(provider_value, api_key))
    
    def _silent_test_connection(self, provider_value, api_key):
        """Silently test connection and load models without showing messages"""
        try:
            provider = AIProvider(provider_value)
            ai = get_ai_manager()
            ai.set_provider(provider=provider, api_key=api_key)
            models = ai.get_available_models()
            if models:
                self._on_models_detected(models)
        except:
            pass  # Silent fail - user can manually test later
    
    def update_translations(self):
        """Update all UI text with current translations"""
        # Header
        if hasattr(self, 'header'):
            self.header.setText(t("ai.title"))
        
        # Provider group
        if hasattr(self, 'provider_group'):
            self.provider_group.setTitle(t("ai.provider_selection"))
        
        # API Key group  
        if hasattr(self, 'api_group'):
            self.api_group.setTitle(t("ai.api_key_section"))
        
        # API Key placeholder
        if hasattr(self, 'api_key_input'):
            self.api_key_input.setPlaceholderText(t("ai.api_key_placeholder"))
        
        # Show key button tooltip
        if hasattr(self, 'show_key_btn'):
            self.show_key_btn.setToolTip(t("ai.show_key"))
        
        # System Prompt group
        if hasattr(self, 'prompt_group'):
            self.prompt_group.setTitle(t("ai.system_prompt_section"))
        
        # System Prompt placeholder
        if hasattr(self, 'system_prompt_input'):
            self.system_prompt_input.setPlaceholderText(t("ai.system_prompt_placeholder"))
        
        # Model selection label
        if hasattr(self, 'model_label'):
            self.model_label.setText(t("ai.select_model"))
        
        # Model test button
        if hasattr(self, 'test_model_button'):
            self.test_model_button.setText(t("ai.test_model"))
        
        # Buttons
        if hasattr(self, 'test_button'):
            self.test_button.setText(t("ai.btn_test"))
        if hasattr(self, 'clear_cache_btn'):
            self.clear_cache_btn.setText(t("ai.clear_cache"))
        if hasattr(self, 'save_button'):
            self.save_button.setText(t("button.save"))
        
        # Provider descriptions
        self._update_provider_description()
    
    def _update_provider_description(self):
        """Update provider description with current translation"""
        provider = AIProvider(self.provider_combo.currentData())
        desc_keys = {
            AIProvider.GEMINI: "ai.desc_gemini",
            AIProvider.OPENAI: "ai.desc_openai",
            AIProvider.GROK: "ai.desc_grok",
            AIProvider.CLAUDE: "ai.desc_claude",
            AIProvider.DEEPSEEK: "ai.desc_deepseek"
        }
        if hasattr(self, 'provider_desc'):
            self.provider_desc.setText(t(desc_keys.get(provider, "")))
        
        link_keys = {
            AIProvider.GEMINI: "https://makersuite.google.com/app/apikey",
            AIProvider.OPENAI: "https://platform.openai.com/api-keys",
            AIProvider.GROK: "https://console.x.ai",
            AIProvider.CLAUDE: "https://console.anthropic.com/account/keys",
            AIProvider.DEEPSEEK: "https://platform.deepseek.com/api_keys"
        }
        if hasattr(self, 'get_key_label'):
            link = link_keys.get(provider, "")
            self.get_key_label.setText(f'<a href="{link}">{t("ai.get_key")}</a>' if link else "")


def initialize_ai_from_settings():
    """Initialize AI from saved settings including selected model"""
    try:
        if not AI_SETTINGS_FILE.exists():
            return
        with open(AI_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        provider_value = settings.get('provider')
        if not provider_value:
            return
        provider = AIProvider(provider_value)
        api_key = settings.get('api_keys', {}).get(provider_value)
        if not api_key:
            return
        
        # Get saved model for this provider
        saved_model = settings.get('models', {}).get(provider_value)
        
        ai = get_ai_manager()
        ai.set_provider(provider=provider, api_key=api_key, model=saved_model)
        ai.set_cache_dir(AI_CACHE_DIR)
        logger.info(f"AI initialized: provider={provider_value}, model={saved_model or 'default'}")
    except Exception as e:
        logger.error(f"Error initializing AI: {e}")
