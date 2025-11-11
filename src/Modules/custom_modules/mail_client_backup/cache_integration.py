"""
Integracja cache z mail_view - szybkie ładowanie danych przy starcie

Funkcje:
- Szybkie wczytywanie maili z cache przy starcie aplikacji
- Lazy loading - szczegóły maili ładowane na żądanie
- Automatyczna synchronizacja w tle
- Progresywne ładowanie danych
"""

from typing import Dict, List, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from .mail_cache import MailCache, BackgroundSyncManager


class CacheLoader(QThread):
    """Wątek ładujący dane z cache w tle"""
    
    mails_loaded = pyqtSignal(dict)  # folder -> mails
    contacts_loaded = pyqtSignal(dict)  # email -> contact_data
    progress = pyqtSignal(str)  # status message
    finished = pyqtSignal()
    
    def __init__(self, cache: MailCache):
        super().__init__()
        self.cache = cache
    
    def run(self):
        """Ładuje dane z cache"""
        try:
            self.progress.emit("Ładowanie maili z cache...")
            
            # Załaduj maile
            mails = self.cache.load_all_mails_from_cache()
            if mails:
                self.mails_loaded.emit(mails)
                self.progress.emit(f"Załadowano {sum(len(m) for m in mails.values())} maili")
            
            # Załaduj kontakty
            self.progress.emit("Ładowanie kontaktów z cache...")
            contacts = self.cache.load_all_contacts_from_cache()
            if contacts:
                self.contacts_loaded.emit(contacts)
                self.progress.emit(f"Załadowano {len(contacts)} kontaktów")
            
            self.progress.emit("Cache załadowany pomyślnie")
            
        except Exception as e:
            self.progress.emit(f"Błąd ładowania cache: {e}")
        
        finally:
            self.finished.emit()


class MailViewCacheIntegration:
    """Integracja cache z MailViewModule"""
    
    def __init__(self, mail_view):
        self.mail_view = mail_view
        self.cache = MailCache()
        self.sync_manager = BackgroundSyncManager(self.cache, mail_view)
        self.cache_loader = None
    
    def load_from_cache_at_startup(self):
        """Ładuje dane z cache przy starcie aplikacji (asynchronicznie)"""
        # Utwórz loader w tle
        self.cache_loader = CacheLoader(self.cache)
        
        # Połącz sygnały
        self.cache_loader.mails_loaded.connect(self._on_mails_loaded)
        self.cache_loader.contacts_loaded.connect(self._on_contacts_loaded)
        self.cache_loader.progress.connect(self._on_progress)
        self.cache_loader.finished.connect(self._on_loading_finished)
        
        # Rozpocznij ładowanie
        self.cache_loader.start()
    
    def _on_mails_loaded(self, mails: Dict[str, List[Dict[str, Any]]]):
        """Obsługa załadowanych maili z cache"""
        # Załaduj maile do mail_view
        if hasattr(self.mail_view, 'sample_mails'):
            # Merguj z istniejącymi mailami (cache + nowe)
            for folder, cached_mails in mails.items():
                if folder not in self.mail_view.sample_mails:
                    self.mail_view.sample_mails[folder] = []
                
                # Dodaj cached maile (jeśli nie istnieją już)
                existing_uids = {m.get("_uid") for m in self.mail_view.sample_mails[folder] if m.get("_uid")}
                
                for mail in cached_mails:
                    uid = mail.get("_uid")
                    if uid and uid not in existing_uids:
                        self.mail_view.sample_mails[folder].append(mail)
                        existing_uids.add(uid)
            
            # Odśwież widok jeśli jest aktywny folder
            if hasattr(self.mail_view, 'current_folder') and self.mail_view.current_folder:
                if hasattr(self.mail_view, 'populate_mail_table'):
                    folder_mails = self.mail_view.sample_mails.get(self.mail_view.current_folder, [])
                    self.mail_view.populate_mail_table(folder_mails)
            
            # Odśwież drzewo folderów (liczniki)
            if hasattr(self.mail_view, 'populate_folders_tree'):
                self.mail_view.populate_folders_tree()
    
    def _on_contacts_loaded(self, contacts: Dict[str, Dict[str, Any]]):
        """Obsługa załadowanych kontaktów z cache"""
        if hasattr(self.mail_view, 'contact_colors'):
            from PyQt6.QtGui import QColor
            
            for email, contact_data in contacts.items():
                # Załaduj kolory
                if contact_data.get("color"):
                    try:
                        self.mail_view.contact_colors[email] = QColor(contact_data["color"])
                    except:
                        pass
                
                # Załaduj tagi
                if contact_data.get("tags"):
                    if hasattr(self.mail_view, 'contact_tags'):
                        self.mail_view.contact_tags[email] = contact_data["tags"]
    
    def _on_progress(self, message: str):
        """Obsługa komunikatów o postępie"""
        if hasattr(self.mail_view, 'statusBar'):
            self.mail_view.statusBar().showMessage(message, 3000)
        print(f"[Cache] {message}")
    
    def _on_loading_finished(self):
        """Obsługa zakończenia ładowania"""
        print("[Cache] Ładowanie z cache zakończone")
        
        # Rozpocznij synchronizację w tle
        self.sync_manager.start_background_sync(interval_minutes=5)
    
    def save_current_state_to_cache(self):
        """Zapisuje aktualny stan do cache"""
        # Zapisz maile
        if hasattr(self.mail_view, 'sample_mails'):
            for folder, mails in self.mail_view.sample_mails.items():
                self.cache.save_mails_to_cache(folder, mails)
        
        # Zapisz kontakty
        if hasattr(self.mail_view, 'contact_colors'):
            for email, color in self.mail_view.contact_colors.items():
                tags = []
                if hasattr(self.mail_view, 'contact_tags'):
                    tags = self.mail_view.contact_tags.get(email, [])
                
                color_str = color.name() if hasattr(color, 'name') else str(color)
                self.cache.save_contact_to_cache(email, "", tags, color_str)
    
    def update_mail_cache(self, uid: str, updates: Dict[str, Any]):
        """Aktualizuje mail w cache"""
        self.cache.update_mail_in_cache(uid, updates)
    
    def cleanup_old_cache(self):
        """Czyści stary cache"""
        deleted = self.cache.clear_old_cache(days=30)
        print(f"[Cache] Usunięto {deleted} starych wpisów")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki cache"""
        return self.cache.get_cache_stats()
    
    def shutdown(self):
        """Zamyka cache i zapisuje dane"""
        # Zatrzymaj synchronizację w tle
        self.sync_manager.stop_background_sync()
        
        # Zapisz aktualny stan
        self.save_current_state_to_cache()
        
        # Wyczyść stary cache
        self.cleanup_old_cache()


def integrate_cache_with_mail_view(mail_view) -> MailViewCacheIntegration:
    """
    Integruje cache z mail_view i zwraca obiekt integracji
    
    Użycie:
        cache_integration = integrate_cache_with_mail_view(mail_view)
        cache_integration.load_from_cache_at_startup()
    """
    return MailViewCacheIntegration(mail_view)
