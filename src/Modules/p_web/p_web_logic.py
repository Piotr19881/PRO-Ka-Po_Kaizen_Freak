"""
P-Web Logic Module
Logika biznesowa modułu przeglądarki internetowej
"""

import json
import os
from typing import List, Dict, Optional
from PyQt6.QtGui import QColor


class PWebLogic:
    """Logika biznesowa dla modułu P-Web"""
    
    def __init__(self, data_file: Optional[str] = None):
        """
        Inicjalizacja logiki P-Web
        
        Args:
            data_file: Ścieżka do pliku JSON z zakładkami (domyślnie 'web_pages.json')
        """
        if data_file is None:
            # Domyślna ścieżka w katalogu z danymi aplikacji
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
            os.makedirs(data_dir, exist_ok=True)
            data_file = os.path.join(data_dir, 'web_pages.json')
        
        self.data_file = data_file
        self.bookmarks: List[Dict] = []
        self.load_bookmarks()
    
    def load_bookmarks(self) -> tuple[bool, str]:
        """
        Wczytuje zakładki z pliku JSON
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.bookmarks = json.load(f)
                return True, ""
            else:
                self.bookmarks = []
                return True, ""
        except json.JSONDecodeError as e:
            self.bookmarks = []
            return False, f"JSONDecodeError: {str(e)}"
        except Exception as e:
            self.bookmarks = []
            return False, f"Error: {str(e)}"
    
    def save_bookmarks(self) -> tuple[bool, str]:
        """
        Zapisuje zakładki do pliku JSON
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2, ensure_ascii=False)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def add_bookmark(self, name: str, url: str, color: str) -> tuple[bool, str]:
        """
        Dodaje nową zakładkę
        
        Args:
            name: Nazwa zakładki
            url: Adres URL
            color: Kolor w formacie hex (#RRGGBB)
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        # Walidacja
        if not name or not name.strip():
            return False, "no_name"
        
        if not url or not url.strip():
            return False, "no_url"
        
        # Normalizacja URL (dodanie https:// jeśli brak protokołu)
        normalized_url = self.normalize_url(url.strip())
        
        # Dodanie zakładki
        bookmark = {
            'name': name.strip(),
            'url': normalized_url,
            'color': color
        }
        
        self.bookmarks.append(bookmark)
        
        # Zapis do pliku
        success, error = self.save_bookmarks()
        if not success:
            # Cofnięcie zmian w przypadku błędu zapisu
            self.bookmarks.pop()
            return False, f"save_error:{error}"
        
        return True, ""
    
    def delete_bookmark(self, index: int) -> tuple[bool, str]:
        """
        Usuwa zakładkę o podanym indeksie
        
        Args:
            index: Indeks zakładki do usunięcia
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        if index < 0 or index >= len(self.bookmarks):
            return False, "invalid_index"
        
        # Backup przed usunięciem
        deleted_bookmark = self.bookmarks[index]
        
        # Usunięcie zakładki
        del self.bookmarks[index]
        
        # Zapis do pliku
        success, error = self.save_bookmarks()
        if not success:
            # Przywrócenie zakładki w przypadku błędu zapisu
            self.bookmarks.insert(index, deleted_bookmark)
            return False, f"save_error:{error}"
        
        return True, ""
    
    def delete_bookmark_by_data(self, bookmark_data: Dict) -> tuple[bool, str]:
        """
        Usuwa zakładkę na podstawie danych (użyteczne przy usuwaniu z dialogu)
        
        Args:
            bookmark_data: Słownik z danymi zakładki
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        try:
            index = self.bookmarks.index(bookmark_data)
            return self.delete_bookmark(index)
        except ValueError:
            return False, "not_found"
    
    def get_bookmarks(self) -> List[Dict]:
        """
        Zwraca listę wszystkich zakładek
        
        Returns:
            List[Dict]: Lista zakładek
        """
        return self.bookmarks.copy()
    
    def get_bookmark(self, index: int) -> Optional[Dict]:
        """
        Zwraca zakładkę o podanym indeksie
        
        Args:
            index: Indeks zakładki
        
        Returns:
            Optional[Dict]: Dane zakładki lub None jeśli indeks nieprawidłowy
        """
        if 0 <= index < len(self.bookmarks):
            return self.bookmarks[index].copy()
        return None
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalizuje URL (dodaje https:// jeśli brak protokołu)
        
        Args:
            url: Adres URL do normalizacji
        
        Returns:
            str: Znormalizowany URL
        """
        url = url.strip()
        if not url.startswith(('http://', 'https://', 'about:', 'file:')):
            url = 'https://' + url
        return url
    
    @staticmethod
    def validate_color(color: str) -> bool:
        """
        Waliduje kolor w formacie hex
        
        Args:
            color: Kolor w formacie hex (#RRGGBB)
        
        Returns:
            bool: True jeśli kolor jest prawidłowy
        """
        try:
            qcolor = QColor(color)
            return qcolor.isValid()
        except:
            return False
    
    @staticmethod
    def is_dark_color(color: str) -> bool:
        """
        Sprawdza czy kolor jest ciemny (do doboru koloru tekstu)
        
        Args:
            color: Kolor w formacie hex (#RRGGBB)
        
        Returns:
            bool: True jeśli kolor jest ciemny
        """
        qcolor = QColor(color)
        if not qcolor.isValid():
            return False
        
        # Wzór na jasność koloru (perceived brightness)
        brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
        return brightness < 128
