"""
ProMail AI Connector - Łączy moduł AI z klientem pocztowym

Funkcjonalność:
- Generowanie odpowiedzi na emaile za pomocą AI
- Zarządzanie źródłami prawdy (kontekst dla AI)
- Integracja z różnymi dostawcami AI (Gemini, OpenAI, etc.)
- Przetwarzanie załączników jako kontekst (PDF, TXT, CSV, JSON)

Autor: PRO-Ka-Po_Kaizen_Freak
Data: 2025-11-11
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from ..AI_module.ai_logic import get_ai_manager, AIProvider, AIResponse, configure_ai_manager_from_settings
except ImportError:
    # Fallback dla testów
    from src.Modules.AI_module.ai_logic import get_ai_manager, AIProvider, AIResponse, configure_ai_manager_from_settings

logger = logging.getLogger(__name__)


class ProMailAIConnector:
    """Konektor łączący AI z modułem ProMail"""
    
    def __init__(self):
        """Inicjalizacja konektora AI"""
        # Konfiguruj AI manager z ustawień użytkownika
        self.ai_manager, settings, error = configure_ai_manager_from_settings()
        
        if error:
            logger.warning(f"Failed to configure AI manager from settings: {error}")
            # Fallback do domyślnego managera
            self.ai_manager = get_ai_manager()
        else:
            logger.info(f"AI manager configured with provider: {settings.get('provider', 'unknown')}, model: {settings.get('models', {}).get(settings.get('provider', ''), 'default')}")
        
        self.default_prompts = self._load_default_prompts()
        
    def _load_default_prompts(self) -> Dict[str, str]:
        """Wczytuje domyślne prompty dla różnych scenariuszy"""
        return {
            "quick_response": """Jesteś profesjonalnym asystentem email. 
Przeanalizuj poniższą wiadomość i wygeneruj odpowiednią, uprzejmą i zwięzłą odpowiedź.
Dostosuj ton do kontekstu wiadomości.
Odpowiedź powinna być gotowa do wysłania.""",
            
            "formal_response": """Jesteś asystentem biznesowym.
Wygeneruj formalną, profesjonalną odpowiedź na poniższą wiadomość.
Zachowaj odpowiedni styl biznesowy i etykietę.""",
            
            "summarize": """Przeanalizuj poniższą wiadomość email i przygotuj jej zwięzłe streszczenie.
Wyodrębnij najważniejsze informacje, prośby lub pytania.""",
            
            "extract_action_items": """Przeanalizuj wiadomość i wyodrębnij wszystkie zadania, 
prośby lub elementy wymagające działania. Przedstaw je w formie listy."""
        }
    
    def generate_quick_response(
        self,
        email_content: str,
        base_prompt: Optional[str] = None,
        additional_prompt: Optional[str] = None,
        truth_sources: Optional[List[str]] = None,
        email_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Generuje szybką odpowiedź na email
        
        Args:
            email_content: Treść wiadomości do odpowiedzi
            base_prompt: Podstawowy prompt (jeśli None, użyje domyślnego)
            additional_prompt: Dodatkowy prompt od użytkownika
            truth_sources: Lista ścieżek do plików źródeł prawdy
            email_context: Dodatkowy kontekst (nadawca, temat, data, etc.)
            
        Returns:
            Tuple[bool, str, Dict]: (sukces, odpowiedź/błąd, metadane)
        """
        try:
            # Sprawdź czy AI manager jest skonfigurowany
            if self.ai_manager is None:
                return False, "AI manager is not configured. Please configure AI settings first.", {}
            
            # Buduj pełny prompt
            full_prompt = self._build_prompt(
                email_content=email_content,
                base_prompt=base_prompt or self.default_prompts["quick_response"],
                additional_prompt=additional_prompt,
                truth_sources=truth_sources,
                email_context=email_context
            )
            
            # Generuj odpowiedź
            response = self.ai_manager.generate(full_prompt)
            
            # AIResponse nie ma atrybutu 'success', sprawdzamy czy error jest None
            if response.error is None:
                metadata = {
                    "provider": response.provider.value,
                    "model": response.model,
                    "tokens_used": response.usage.get("total_tokens", 0) if response.usage else 0,
                    "timestamp": datetime.now().isoformat(),
                    "used_truth_sources": truth_sources or []
                }
                return True, response.text, metadata
            else:
                return False, response.error, {}
                
        except Exception as e:
            logger.error(f"Error generating quick response: {e}")
            return False, f"Error: {str(e)}", {}
    
    def _build_prompt(
        self,
        email_content: str,
        base_prompt: str,
        additional_prompt: Optional[str] = None,
        truth_sources: Optional[List[str]] = None,
        email_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Buduje pełny prompt dla AI
        
        Args:
            email_content: Treść emaila
            base_prompt: Podstawowy prompt
            additional_prompt: Dodatkowy prompt użytkownika
            truth_sources: Pliki ze źródłami prawdy
            email_context: Kontekst emaila (nadawca, temat, etc.)
            
        Returns:
            str: Pełny prompt gotowy do wysłania do AI
        """
        prompt_parts = []
        
        # Część 1: Podstawowy prompt
        prompt_parts.append(base_prompt)
        prompt_parts.append("\n" + "="*50 + "\n")
        
        # Część 2: Kontekst emaila (jeśli jest)
        if email_context:
            prompt_parts.append("KONTEKST WIADOMOŚCI:")
            if email_context.get("from"):
                prompt_parts.append(f"Od: {email_context['from']}")
            if email_context.get("to"):
                prompt_parts.append(f"Do: {email_context['to']}")
            if email_context.get("subject"):
                prompt_parts.append(f"Temat: {email_context['subject']}")
            if email_context.get("date"):
                prompt_parts.append(f"Data: {email_context['date']}")
            prompt_parts.append("")
        
        # Część 3: Treść emaila
        prompt_parts.append("TREŚĆ WIADOMOŚCI:")
        prompt_parts.append(email_content)
        prompt_parts.append("\n" + "="*50 + "\n")
        
        # Część 4: Źródła prawdy (jeśli są)
        if truth_sources:
            truth_content = self._load_truth_sources(truth_sources)
            if truth_content:
                prompt_parts.append("DODATKOWY KONTEKST (Źródła prawdy):")
                prompt_parts.append(truth_content)
                prompt_parts.append("\n" + "="*50 + "\n")
        
        # Część 5: Dodatkowy prompt użytkownika
        if additional_prompt:
            prompt_parts.append("DODATKOWE INSTRUKCJE:")
            prompt_parts.append(additional_prompt)
            prompt_parts.append("\n" + "="*50 + "\n")
        
        # Część 6: Finalna instrukcja
        prompt_parts.append("Wygeneruj odpowiedź na powyższą wiadomość.")
        
        return "\n".join(prompt_parts)
    
    def _load_truth_sources(self, file_paths: List[str]) -> str:
        """
        Wczytuje zawartość plików źródeł prawdy
        
        Args:
            file_paths: Lista ścieżek do plików
            
        Returns:
            str: Skonkatenowana zawartość plików
        """
        contents = []
        
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if not path.exists():
                    logger.warning(f"Truth source file not found: {file_path}")
                    continue
                
                # Obsługa różnych typów plików
                if path.suffix.lower() in ['.txt', '.md']:
                    content = self._read_text_file(path)
                elif path.suffix.lower() == '.json':
                    content = self._read_json_file(path)
                elif path.suffix.lower() == '.csv':
                    content = self._read_csv_file(path)
                elif path.suffix.lower() == '.pdf':
                    content = self._read_pdf_file(path)
                else:
                    logger.warning(f"Unsupported file type: {path.suffix}")
                    continue
                
                if content:
                    contents.append(f"\n--- Źródło: {path.name} ---\n{content}\n")
                    
            except Exception as e:
                logger.error(f"Error reading truth source {file_path}: {e}")
                continue
        
        return "\n".join(contents)
    
    def _read_text_file(self, path: Path) -> str:
        """Wczytuje plik tekstowy"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {path}: {e}")
            return ""
    
    def _read_json_file(self, path: Path) -> str:
        """Wczytuje plik JSON i formatuje jako tekst"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error reading JSON file {path}: {e}")
            return ""
    
    def _read_csv_file(self, path: Path) -> str:
        """Wczytuje plik CSV i formatuje jako tekst"""
        try:
            import csv
            lines = []
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    lines.append(" | ".join(row))
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error reading CSV file {path}: {e}")
            return ""
    
    def _read_pdf_file(self, path: Path) -> str:
        """Wczytuje plik PDF i ekstrahuje tekst"""
        try:
            # Wymaga PyPDF2 lub podobnej biblioteki
            import PyPDF2
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = []
                for page in reader.pages:
                    text.append(page.extract_text())
                return "\n".join(text)
        except ImportError:
            logger.warning("PyPDF2 not installed. Cannot read PDF files.")
            return ""
        except Exception as e:
            logger.error(f"Error reading PDF file {path}: {e}")
            return ""
    
    def summarize_email(self, email_content: str, email_context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Podsumowuje treść emaila
        
        Args:
            email_content: Treść emaila
            email_context: Kontekst emaila
            
        Returns:
            Tuple[bool, str]: (sukces, podsumowanie/błąd)
        """
        if self.ai_manager is None:
            return False, "AI manager is not configured. Please configure AI settings first."
        
        prompt = self._build_prompt(
            email_content=email_content,
            base_prompt=self.default_prompts["summarize"],
            email_context=email_context
        )
        
        response = self.ai_manager.generate(prompt)
        return (response.error is None, response.text if response.error is None else response.error)
    
    def extract_action_items(self, email_content: str) -> Tuple[bool, List[str]]:
        """
        Ekstrahuje zadania z emaila
        
        Args:
            email_content: Treść emaila
            
        Returns:
            Tuple[bool, List[str]]: (sukces, lista zadań)
        """
        if self.ai_manager is None:
            return False, []
        
        prompt = self._build_prompt(
            email_content=email_content,
            base_prompt=self.default_prompts["extract_action_items"]
        )
        
        response = self.ai_manager.generate(prompt)
        if response.error is None:
            # Parsuj odpowiedź do listy
            items = [line.strip() for line in response.text.split('\n') if line.strip()]
            return True, items
        else:
            return False, []


# Singleton instance
_promail_ai_connector: Optional[ProMailAIConnector] = None

def get_promail_ai_connector() -> ProMailAIConnector:
    """Zwraca singleton instancję konektora AI dla ProMail"""
    global _promail_ai_connector
    if _promail_ai_connector is None:
        _promail_ai_connector = ProMailAIConnector()
    return _promail_ai_connector
