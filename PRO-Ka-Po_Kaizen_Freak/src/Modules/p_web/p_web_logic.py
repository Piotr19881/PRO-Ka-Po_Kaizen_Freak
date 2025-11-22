"""
P-Web Logic Module
Logika biznesowa modułu przeglądarki internetowej

Nowa struktura danych:
{
    "groups": [
        {"id": "group_1", "name": "Praca", "color": "#FF5722"},
        {"id": "group_2", "name": "Osobiste", "color": "#2196F3"}
    ],
    "tags": ["ważne", "projekt", "dokumenty"],
    "bookmarks": [
        {
            "name": "Gmail",
            "url": "https://gmail.com",
            "color": "#4CAF50",
            "group_id": "group_1",
            "tags": ["ważne"],
            "favorite": true
        }
    ]
}
"""

import json
import os
from typing import List, Dict, Optional, Set
from PyQt6.QtGui import QColor


class PWebLogic:
    """Logika biznesowa dla modułu P-Web z grupami, tagami i ulubionymi"""
    
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
        self.data: Dict = {
            'groups': [],
            'tags': [],
            'bookmarks': []
        }
        self.load_bookmarks()
    
    def load_bookmarks(self) -> tuple[bool, str]:
        """
        Wczytuje dane z pliku JSON (grupy, tagi, zakładki)
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                    # Stara struktura (backward compatibility)
                    if isinstance(loaded_data, list):
                        self.data = {
                            'groups': [{'id': 'default', 'name': 'Wszystkie', 'color': '#9E9E9E'}],
                            'tags': [],
                            'bookmarks': [
                                {
                                    **bookmark,
                                    'group_id': 'default',
                                    'tags': [],
                                    'favorite': False
                                }
                                for bookmark in loaded_data
                            ]
                        }
                    else:
                        # Nowa struktura
                        self.data = {
                            'groups': loaded_data.get('groups', []),
                            'tags': loaded_data.get('tags', []),
                            'bookmarks': loaded_data.get('bookmarks', [])
                        }
                        
                        # Upewnij się że każda zakładka ma wymagane pola
                        for bookmark in self.data['bookmarks']:
                            bookmark.setdefault('group_id', None)
                            bookmark.setdefault('tags', [])
                            bookmark.setdefault('favorite', False)
                
                return True, ""
            else:
                # Stwórz domyślną grupę
                self.data = {
                    'groups': [{'id': 'default', 'name': 'Wszystkie', 'color': '#9E9E9E'}],
                    'tags': [],
                    'bookmarks': []
                }
                return True, ""
        except json.JSONDecodeError as e:
            self.data = {
                'groups': [{'id': 'default', 'name': 'Wszystkie', 'color': '#9E9E9E'}],
                'tags': [],
                'bookmarks': []
            }
            return False, f"JSONDecodeError: {str(e)}"
        except Exception as e:
            self.data = {
                'groups': [{'id': 'default', 'name': 'Wszystkie', 'color': '#9E9E9E'}],
                'tags': [],
                'bookmarks': []
            }
            return False, f"Error: {str(e)}"
    
    def save_bookmarks(self) -> tuple[bool, str]:
        """
        Zapisuje dane do pliku JSON
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def add_bookmark(self, name: str, url: str, color: str, group_id: Optional[str] = None, 
                     tags: Optional[List[str]] = None, favorite: bool = False) -> tuple[bool, str]:
        """
        Dodaje nową zakładkę
        
        Args:
            name: Nazwa zakładki
            url: Adres URL
            color: Kolor w formacie hex (#RRGGBB)
            group_id: ID grupy (opcjonalne)
            tags: Lista tagów (opcjonalne)
            favorite: Czy ulubiona (domyślnie False)
        
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
            'color': color,
            'group_id': group_id or 'default',
            'tags': tags or [],
            'favorite': favorite
        }
        
        self.data['bookmarks'].append(bookmark)
        
        # Zapis do pliku
        success, error = self.save_bookmarks()
        if not success:
            # Cofnięcie zmian w przypadku błędu zapisu
            self.data['bookmarks'].pop()
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
        bookmarks = self.data['bookmarks']
        if index < 0 or index >= len(bookmarks):
            return False, "invalid_index"
        
        # Backup przed usunięciem
        deleted_bookmark = bookmarks[index]
        
        # Usunięcie zakładki
        del bookmarks[index]
        
        # Zapis do pliku
        success, error = self.save_bookmarks()
        if not success:
            # Przywrócenie zakładki w przypadku błędu zapisu
            bookmarks.insert(index, deleted_bookmark)
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
            index = self.data['bookmarks'].index(bookmark_data)
            return self.delete_bookmark(index)
        except ValueError:
            return False, "not_found"
    
    def get_bookmarks(self, group_id: Optional[str] = None, tag: Optional[str] = None,
                      favorites_only: bool = False, phrase: Optional[str] = None) -> List[Dict]:
        """
        Zwraca listę zakładek z opcjonalnym filtrowaniem
        
        Args:
            group_id: Filtruj po grupie (None = wszystkie)
            tag: Filtruj po tagu (None = wszystkie)
            favorites_only: Tylko ulubione
            phrase: Filtruj po frazie w nazwie/URL
        
        Returns:
            List[Dict]: Lista zakładek
        """
        bookmarks = self.data['bookmarks'].copy()
        
        # Filtruj po grupie
        if group_id:
            bookmarks = [b for b in bookmarks if b.get('group_id') == group_id]
        
        # Filtruj po tagu
        if tag:
            bookmarks = [b for b in bookmarks if tag in b.get('tags', [])]
        
        # Filtruj ulubione
        if favorites_only:
            bookmarks = [b for b in bookmarks if b.get('favorite', False)]
        
        # Filtruj po frazie
        if phrase and phrase.strip():
            phrase_lower = phrase.strip().lower()
            bookmarks = [
                b for b in bookmarks
                if phrase_lower in b['name'].lower() or phrase_lower in b['url'].lower()
            ]
        
        return bookmarks
    
    def get_bookmark(self, index: int) -> Optional[Dict]:
        """
        Zwraca zakładkę o podanym indeksie
        
        Args:
            index: Indeks zakładki
        
        Returns:
            Optional[Dict]: Dane zakładki lub None jeśli indeks nieprawidłowy
        """
        bookmarks = self.data['bookmarks']
        if 0 <= index < len(bookmarks):
            return bookmarks[index].copy()
        return None
    
    # ======================
    # Zarządzanie grupami
    # ======================
    
    def get_groups(self) -> List[Dict]:
        """Zwraca listę wszystkich grup"""
        return self.data['groups'].copy()
    
    def add_group(self, name: str, color: str) -> tuple[bool, str]:
        """
        Dodaje nową grupę
        
        Args:
            name: Nazwa grupy
            color: Kolor grupy (#RRGGBB)
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu lub ID grupy)
        """
        if not name or not name.strip():
            return False, "no_name"
        
        # Generuj unikalne ID
        import time
        group_id = f"group_{int(time.time() * 1000)}"
        
        group = {
            'id': group_id,
            'name': name.strip(),
            'color': color
        }
        
        self.data['groups'].append(group)
        
        success, error = self.save_bookmarks()
        if not success:
            self.data['groups'].pop()
            return False, f"save_error:{error}"
        
        return True, group_id
    
    def edit_group(self, group_id: str, name: str, color: str) -> tuple[bool, str]:
        """
        Edytuje grupę
        
        Args:
            group_id: ID grupy
            name: Nowa nazwa
            color: Nowy kolor
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        for group in self.data['groups']:
            if group['id'] == group_id:
                if not name or not name.strip():
                    return False, "no_name"
                
                group['name'] = name.strip()
                group['color'] = color
                
                success, error = self.save_bookmarks()
                if not success:
                    return False, f"save_error:{error}"
                
                return True, ""
        
        return False, "group_not_found"
    
    def delete_group(self, group_id: str) -> tuple[bool, str]:
        """
        Usuwa grupę (zakładki z tej grupy przenosi do 'default')
        
        Args:
            group_id: ID grupy do usunięcia
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        if group_id == 'default':
            return False, "cannot_delete_default"
        
        # Znajdź grupę
        group_to_delete = None
        for idx, group in enumerate(self.data['groups']):
            if group['id'] == group_id:
                group_to_delete = (idx, group)
                break
        
        if not group_to_delete:
            return False, "group_not_found"
        
        # Przenieś zakładki do default
        for bookmark in self.data['bookmarks']:
            if bookmark.get('group_id') == group_id:
                bookmark['group_id'] = 'default'
        
        # Usuń grupę
        del self.data['groups'][group_to_delete[0]]
        
        success, error = self.save_bookmarks()
        if not success:
            # Cofnij zmiany
            self.data['groups'].insert(group_to_delete[0], group_to_delete[1])
            for bookmark in self.data['bookmarks']:
                if bookmark.get('group_id') == 'default':
                    bookmark['group_id'] = group_id
            return False, f"save_error:{error}"
        
        return True, ""
    
    def get_group_by_id(self, group_id: str) -> Optional[Dict]:
        """Zwraca grupę o podanym ID"""
        for group in self.data['groups']:
            if group['id'] == group_id:
                return group.copy()
        return None
    
    # ======================
    # Zarządzanie tagami
    # ======================
    
    def get_tags(self) -> List[str]:
        """Zwraca listę wszystkich tagów"""
        return self.data['tags'].copy()
    
    def add_tag(self, tag: str) -> tuple[bool, str]:
        """
        Dodaje nowy tag
        
        Args:
            tag: Nazwa tagu
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        if not tag or not tag.strip():
            return False, "no_tag"
        
        tag = tag.strip()
        
        if tag in self.data['tags']:
            return False, "tag_exists"
        
        self.data['tags'].append(tag)
        
        success, error = self.save_bookmarks()
        if not success:
            self.data['tags'].pop()
            return False, f"save_error:{error}"
        
        return True, ""
    
    def delete_tag(self, tag: str) -> tuple[bool, str]:
        """
        Usuwa tag (usuwa go też ze wszystkich zakładek)
        
        Args:
            tag: Nazwa tagu do usunięcia
        
        Returns:
            tuple[bool, str]: (sukces, komunikat_błędu)
        """
        if tag not in self.data['tags']:
            return False, "tag_not_found"
        
        # Usuń z listy tagów
        self.data['tags'].remove(tag)
        
        # Usuń ze wszystkich zakładek
        for bookmark in self.data['bookmarks']:
            if tag in bookmark.get('tags', []):
                bookmark['tags'].remove(tag)
        
        success, error = self.save_bookmarks()
        if not success:
            # Cofnij zmiany
            self.data['tags'].append(tag)
            for bookmark in self.data['bookmarks']:
                if 'tags' in bookmark:
                    bookmark['tags'].append(tag)
            return False, f"save_error:{error}"
        
        return True, ""
    
    # ======================
    # Ulubione
    # ======================
    
    def get_favorites(self) -> List[Dict]:
        """
        Zwraca listę ulubionych zakładek
        
        Returns:
            List[Dict]: Lista zakładek oznaczonych jako ulubione
        """
        return [b for b in self.data['bookmarks'] if b.get('favorite', False)]
    
    def toggle_favorite(self, bookmark_data: Dict) -> tuple[bool, str]:
        """
        Przełącza status ulubionej dla zakładki
        
        Args:
            bookmark_data: Dane zakładki
        
        Returns:
            tuple[bool, str]: (sukces, nowy_status_jako_string)
        """
        try:
            # Znajdź zakładkę w liście
            for bookmark in self.data['bookmarks']:
                if bookmark['name'] == bookmark_data['name'] and bookmark['url'] == bookmark_data['url']:
                    bookmark['favorite'] = not bookmark.get('favorite', False)
                    
                    success, error = self.save_bookmarks()
                    if not success:
                        bookmark['favorite'] = not bookmark['favorite']  # Cofnij
                        return False, f"save_error:{error}"
                    
                    return True, str(bookmark['favorite'])
            
            return False, "bookmark_not_found"
        except Exception as e:
            return False, str(e)
    
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
