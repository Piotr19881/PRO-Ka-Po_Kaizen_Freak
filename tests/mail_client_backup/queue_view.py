"""
Widok kolejki wiadomości - pozwala na szybką obsługę nieopowiedzianej poczty
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QLabel, QComboBox, QCheckBox, QTextEdit, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPalette
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import json


class MailQueueCard(QFrame):
    """Karta pojedynczego wątku wiadomości w kolejce"""
    
    reply_clicked = pyqtSignal(dict)  # mail
    no_reply_needed_clicked = pyqtSignal(dict)  # mail
    spam_clicked = pyqtSignal(dict)  # mail
    replied_changed = pyqtSignal(dict, bool)  # mail, is_replied
    note_changed = pyqtSignal(dict, str)  # mail, note_text
    
    def __init__(self, thread_mails: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.thread_mails = sorted(thread_mails, key=lambda m: m.get("date", ""), reverse=True)
        self.newest_mail = self.thread_mails[0]
        self.expanded = False
        self.reply_widget = None
        
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        
        # Ustaw kolor tła w zależności od wieku wiadomości
        self.update_background_color()
        
        self.init_ui()
    
    def update_background_color(self):
        """Aktualizuje kolor tła w zależności od wieku wiadomości"""
        date_str = self.newest_mail.get("date", "")
        try:
            if date_str:
                mail_date = datetime.strptime(date_str[:16], "%Y-%m-%d %H:%M")
                age_days = (datetime.now() - mail_date).days
                
                if age_days > 7:
                    bg_color = "#FFEBEE"  # Stare - czerwonawy
                elif age_days > 3:
                    bg_color = "#FFF3E0"  # Średnie - pomarańczowy
                elif age_days > 1:
                    bg_color = "#FFF9C4"  # Niedawne - żółty
                else:
                    bg_color = "#E8F5E9"  # Nowe - zielony
                
                self.setStyleSheet(f"MailQueueCard {{ background-color: {bg_color}; border-radius: 8px; }}")
        except:
            self.setStyleSheet("MailQueueCard { background-color: #FFFFFF; border-radius: 8px; }")
    
    def init_ui(self):
        """Inicjalizuje interfejs karty"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        
        # === NAGŁÓWEK ===
        header_layout = QHBoxLayout()
        
        # Data
        date_label = QLabel(self.newest_mail.get("date", ""))
        date_label.setStyleSheet("font-weight: bold; color: #0D47A1; font-size: 11pt;")
        header_layout.addWidget(date_label)
        
        # Adres
        from_address = self.extract_email_address(self.newest_mail.get("from", ""))
        address_label = QLabel(from_address)
        address_label.setStyleSheet("color: #212121; font-size: 10pt;")
        header_layout.addWidget(address_label)
        
        # Autor (nazwa)
        author_name = self.extract_display_name(self.newest_mail.get("from", "")) or from_address
        author_label = QLabel(author_name)
        author_label.setStyleSheet("font-weight: bold; color: #1A237E; font-size: 10pt;")
        header_layout.addWidget(author_label)
        
        # Tag autora (placeholder - będzie podpięty do systemu tagów)
        self.tag_label = QLabel("")
        self.tag_label.setStyleSheet("color: #424242; font-style: italic; font-size: 9pt;")
        header_layout.addWidget(self.tag_label)
        
        header_layout.addStretch()
        
        # Checkbox "Odpowiedziano"
        self.replied_checkbox = QCheckBox("✓ Odpowiedziano")
        self.replied_checkbox.setStyleSheet("color: #1B5E20; font-weight: bold;")
        self.replied_checkbox.setChecked(self.newest_mail.get("_replied", False))
        self.replied_checkbox.stateChanged.connect(self.on_replied_changed)
        header_layout.addWidget(self.replied_checkbox)
        
        # Checkbox "Bez odpowiedzi"
        self.no_reply_checkbox = QCheckBox("⊘ Bez odpowiedzi")
        self.no_reply_checkbox.setStyleSheet("color: #E65100; font-weight: bold;")
        self.no_reply_checkbox.setChecked(self.newest_mail.get("_no_reply_needed", False))
        self.no_reply_checkbox.stateChanged.connect(self.on_no_reply_changed)
        header_layout.addWidget(self.no_reply_checkbox)
        
        # Checkbox "Spam"
        self.spam_checkbox = QCheckBox("🚫 Spam")
        self.spam_checkbox.setStyleSheet("color: #B71C1C; font-weight: bold;")
        self.spam_checkbox.setChecked(False)
        self.spam_checkbox.stateChanged.connect(self.on_spam_changed)
        header_layout.addWidget(self.spam_checkbox)
        
        main_layout.addLayout(header_layout)
        
        # === NOTATKA ===
        note_layout = QHBoxLayout()
        note_label = QLabel("📝 Notatka:")
        note_label.setStyleSheet("color: #37474F; font-weight: bold;")
        note_layout.addWidget(note_label)
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Dodaj notatkę do tego wątku...")
        self.note_edit.setText(self.newest_mail.get("note", ""))
        self.note_edit.setStyleSheet("background-color: white; color: #212121; border: 1px solid #BDBDBD; padding: 4px;")
        self.note_edit.textChanged.connect(self.on_note_changed)
        note_layout.addWidget(self.note_edit)
        main_layout.addLayout(note_layout)
        
        # === TYTUŁ I PRZYCISK ROZWINIĘCIA ===
        subject_layout = QHBoxLayout()
        subject_text = self.newest_mail.get("subject", "(brak tematu)")
        if len(self.thread_mails) > 1:
            subject_text += f" ({len(self.thread_mails)} wiadomości)"
        
        self.subject_label = QLabel(f"<b style='color: #263238; font-size: 11pt;'>{subject_text}</b>")
        self.subject_label.setWordWrap(True)
        subject_layout.addWidget(self.subject_label, 1)
        
        self.expand_btn = QPushButton("▼ Rozwiń")
        self.expand_btn.setStyleSheet("background-color: #546E7A; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.expand_btn.clicked.connect(self.toggle_expansion)
        subject_layout.addWidget(self.expand_btn)
        main_layout.addLayout(subject_layout)
        
        # === TREŚĆ (początkowo ukryta) ===
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        # Treść najnowszej wiadomości
        self.body_edit = QTextEdit()
        self.body_edit.setReadOnly(True)
        self.body_edit.setMaximumHeight(200)
        self.body_edit.setPlainText(self.newest_mail.get("body", "(brak treści)"))
        self.body_edit.setStyleSheet("background-color: #FAFAFA; color: #212121; border: 1px solid #E0E0E0; padding: 8px;")
        self.content_layout.addWidget(self.body_edit)
        
        # Przyciski akcji
        action_layout = QHBoxLayout()
        
        reply_btn = QPushButton("↩️ Odpowiedz")
        reply_btn.clicked.connect(self.on_reply_clicked)
        reply_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 10px 16px; font-size: 10pt; border-radius: 4px;")
        action_layout.addWidget(reply_btn)
        
        no_reply_btn = QPushButton("⊘ Pozostaw bez odpowiedzi")
        no_reply_btn.clicked.connect(self.on_no_reply_btn_clicked)
        no_reply_btn.setStyleSheet("background-color: #EF6C00; color: white; font-weight: bold; padding: 10px 16px; font-size: 10pt; border-radius: 4px;")
        action_layout.addWidget(no_reply_btn)
        
        self.content_layout.addLayout(action_layout)
        
        # Kontener na okno odpowiedzi (początkowo pusty)
        self.reply_container = QWidget()
        self.reply_container_layout = QVBoxLayout(self.reply_container)
        self.reply_container.hide()
        self.content_layout.addWidget(self.reply_container)
        
        self.content_widget.hide()
        main_layout.addWidget(self.content_widget)
    
    def extract_email_address(self, from_field: str) -> str:
        """Wyodrębnia adres email z pola 'from'"""
        import re
        if not from_field:
            return ""
        match = re.match(r'^(.+?)\s*<(.+)>$', from_field.strip())
        if match:
            return match.group(2).strip()
        return from_field.strip()
    
    def extract_display_name(self, from_field: str) -> str:
        """Wyodrębnia nazwę z pola 'from'"""
        import re
        if not from_field:
            return ""
        match = re.match(r'^(.+?)\s*<(.+)>$', from_field.strip())
        if match:
            return match.group(1).strip().strip('"\'')
        return ""
    
    def toggle_expansion(self):
        """Rozwiń/zwiń treść wiadomości"""
        self.expanded = not self.expanded
        
        if self.expanded:
            self.content_widget.show()
            self.expand_btn.setText("▲ Zwiń")
        else:
            self.content_widget.hide()
            self.expand_btn.setText("▼ Rozwiń")
            # Ukryj okno odpowiedzi przy zwijaniu
            if self.reply_container:
                self.reply_container.hide()
    
    def on_reply_clicked(self):
        """Obsługa kliknięcia przycisku Odpowiedz"""
        # Sprawdź czy okno odpowiedzi już istnieje
        if self.reply_container.isVisible():
            return
        
        # Import new_mail_window
        try:
            import sys
            from pathlib import Path
            # Dodaj katalog mail_client do sys.path jeśli nie ma
            mail_client_dir = Path(__file__).parent
            if str(mail_client_dir) not in sys.path:
                sys.path.insert(0, str(mail_client_dir))
            
            from new_mail_window import NewMailWindow
            
            # Usuń poprzednie widgety z kontenera
            while self.reply_container_layout.count():
                item = self.reply_container_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Utwórz okno odpowiedzi jako widget (nie jako okno)
            reply_window = NewMailWindow(is_reply=True, original_mail=self.newest_mail)
            reply_window.setWindowFlags(Qt.WindowType.Widget)  # Usuń flagi okna
            
            # Połącz sygnał wysłania z zamknięciem
            reply_window.mail_sent.connect(self.on_reply_sent)
            
            self.reply_container_layout.addWidget(reply_window)
            self.reply_container.show()
            
        except Exception as e:
            print(f"Błąd podczas tworzenia okna odpowiedzi: {e}")
            import traceback
            traceback.print_exc()
    
    def on_reply_sent(self):
        """Obsługa po wysłaniu odpowiedzi"""
        # Ukryj kontener odpowiedzi
        self.reply_container.hide()
        
        # Zaznacz jako odpowiedziano
        self.replied_checkbox.setChecked(True)
        
        # Zwiń kartę
        self.expanded = False
        self.content_widget.hide()
        self.expand_btn.setText("▼ Rozwiń")
        
        # Emit sygnał
        self.reply_clicked.emit(self.newest_mail)
    
    def on_no_reply_btn_clicked(self):
        """Obsługa przycisku 'Pozostaw bez odpowiedzi'"""
        self.no_reply_checkbox.setChecked(True)
        self.no_reply_needed_clicked.emit(self.newest_mail)
    
    def on_replied_changed(self, state):
        """Obsługa zmiany checkboxa 'Odpowiedziano'"""
        is_checked = state == Qt.CheckState.Checked.value
        self.newest_mail["_replied"] = is_checked
        self.replied_changed.emit(self.newest_mail, is_checked)
    
    def on_no_reply_changed(self, state):
        """Obsługa zmiany checkboxa 'Bez odpowiedzi'"""
        is_checked = state == Qt.CheckState.Checked.value
        self.newest_mail["_no_reply_needed"] = is_checked
        
        if is_checked:
            self.no_reply_needed_clicked.emit(self.newest_mail)
    
    def on_spam_changed(self, state):
        """Obsługa zmiany checkboxa 'Spam'"""
        if state == Qt.CheckState.Checked.value:
            self.spam_clicked.emit(self.newest_mail)
    
    def on_note_changed(self, text):
        """Obsługa zmiany notatki"""
        self.newest_mail["note"] = text
        self.note_changed.emit(self.newest_mail, text)
    
    def set_tag_text(self, tag_text: str, color: str = "#424242"):
        """Ustawia tekst tagu autora"""
        self.tag_label.setText(tag_text)
        # Upewnij się że kolor jest ciemny i czytelny
        self.tag_label.setStyleSheet(f"color: {color}; font-style: italic; font-size: 9pt; font-weight: bold;")


class QueueView(QWidget):
    """Główny widok kolejki wiadomości"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.cards: List[MailQueueCard] = []
        
        self.init_ui()
        self.load_queue()
    
    def init_ui(self):
        """Inicjalizuje interfejs"""
        layout = QVBoxLayout(self)
        
        # === GÓRNY PANEL Z FILTREM ===
        top_panel = QHBoxLayout()
        
        filter_label = QLabel("<b>📅 Filtr zakresu czasu:</b>")
        filter_label.setStyleSheet("color: #1A237E; font-size: 11pt;")
        top_panel.addWidget(filter_label)
        
        self.time_filter = QComboBox()
        self.time_filter.setStyleSheet("background-color: white; color: #212121; padding: 6px; font-size: 10pt; border: 1px solid #BDBDBD;")
        self.time_filter.addItems([
            "Wszystkie",
            "Dzisiaj",
            "Ostatnie 3 dni",
            "Ostatni tydzień",
            "Ostatnie 2 tygodnie",
            "Ostatni miesiąc",
            "Starsze niż miesiąc"
        ])
        self.time_filter.currentTextChanged.connect(self.on_filter_changed)
        top_panel.addWidget(self.time_filter)
        
        top_panel.addStretch()
        
        # Licznik wiadomości
        self.count_label = QLabel("Wiadomości: 0")
        self.count_label.setStyleSheet("font-weight: bold; color: #0D47A1; font-size: 12pt; background-color: #E3F2FD; padding: 6px 12px; border-radius: 4px;")
        top_panel.addWidget(self.count_label)
        
        layout.addLayout(top_panel)
        
        # === OBSZAR PRZEWIJANIA Z KARTAMI ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)
    
    def load_queue(self):
        """Ładuje wiadomości do kolejki"""
        # Pobierz wszystkie wątki z nieopowiedzianymi wiadomościami
        threads = self.get_unanswered_threads()
        
        # Wyczyść obecne karty
        self.clear_cards()
        
        # Utwórz karty dla każdego wątku
        for thread_mails in threads:
            card = MailQueueCard(thread_mails)
            
            # Połącz sygnały
            card.reply_clicked.connect(self.on_card_reply)
            card.no_reply_needed_clicked.connect(self.on_card_no_reply)
            card.spam_clicked.connect(self.on_card_spam)
            card.replied_changed.connect(self.on_card_replied_changed)
            card.note_changed.connect(self.on_card_note_changed)
            
            # Ustaw tagi autora
            from_email = card.extract_email_address(card.newest_mail.get("from", ""))
            if hasattr(self.parent_view, 'contact_tags') and from_email in self.parent_view.contact_tags:
                tags = self.parent_view.contact_tags[from_email]
                if tags:
                    card.set_tag_text(", ".join(tags))
            
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self.cards.append(card)
        
        # Aktualizuj licznik
        self.count_label.setText(f"Wiadomości: {len(threads)}")
    
    def clear_cards(self):
        """Usuwa wszystkie karty"""
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
    
    def get_unanswered_threads(self) -> List[List[Dict[str, Any]]]:
        """Pobiera wątki z nieopowiedzianymi wiadomościami"""
        # Grupuj maile w wątki
        threads_dict = {}
        
        for folder_name, mails in self.parent_view.sample_mails.items():
            if folder_name in {"Kosz", "Spam", "Wysłane", "Szkice"}:
                continue
            
            for mail in mails:
                # Pomiń jeśli oznaczone jako odpowiedziano lub bez odpowiedzi
                if mail.get("_replied", False) or mail.get("_no_reply_needed", False):
                    continue
                
                # Grupuj po temacie (normalizowanym)
                subject = self.normalize_subject(mail.get("subject", ""))
                if subject not in threads_dict:
                    threads_dict[subject] = []
                threads_dict[subject].append(mail)
        
        # Konwertuj na listę i sortuj każdy wątek po dacie
        threads = []
        for subject, mails in threads_dict.items():
            sorted_mails = sorted(mails, key=lambda m: m.get("date", ""), reverse=True)
            threads.append(sorted_mails)
        
        # Sortuj wątki według najstarszej wiadomości (od najstarszych)
        threads.sort(key=lambda thread: self.get_oldest_date(thread))
        
        # Filtruj według wybranego zakresu czasu
        filtered_threads = self.filter_by_time_range(threads)
        
        return filtered_threads
    
    def normalize_subject(self, subject: str) -> str:
        """Normalizuje temat usuwając Re:, Fwd: itp."""
        import re
        if not subject:
            return ""
        normalized = re.sub(r'^(Re:|RE:|Fwd:|FW:|Odp:)\s*', '', subject, flags=re.IGNORECASE)
        return normalized.strip()
    
    def get_oldest_date(self, thread: List[Dict[str, Any]]) -> str:
        """Zwraca datę najstarszej wiadomości w wątku"""
        dates = [m.get("date", "") for m in thread if m.get("date")]
        return min(dates) if dates else ""
    
    def filter_by_time_range(self, threads: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """Filtruje wątki według wybranego zakresu czasu"""
        filter_text = self.time_filter.currentText()
        
        if filter_text == "Wszystkie":
            return threads
        
        now = datetime.now()
        cutoff_date = None
        
        if filter_text == "Dzisiaj":
            cutoff_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_text == "Ostatnie 3 dni":
            cutoff_date = now - timedelta(days=3)
        elif filter_text == "Ostatni tydzień":
            cutoff_date = now - timedelta(days=7)
        elif filter_text == "Ostatnie 2 tygodnie":
            cutoff_date = now - timedelta(days=14)
        elif filter_text == "Ostatni miesiąc":
            cutoff_date = now - timedelta(days=30)
        elif filter_text == "Starsze niż miesiąc":
            cutoff_date = now - timedelta(days=30)
            # Odwrotna logika
            return [
                thread for thread in threads
                if self.is_thread_older_than(thread, cutoff_date)
            ]
        
        if cutoff_date:
            return [
                thread for thread in threads
                if self.is_thread_newer_than(thread, cutoff_date)
            ]
        
        return threads
    
    def is_thread_newer_than(self, thread: List[Dict[str, Any]], cutoff: datetime) -> bool:
        """Sprawdza czy wątek ma przynajmniej jedną wiadomość nowszą niż cutoff"""
        for mail in thread:
            date_str = mail.get("date", "")
            try:
                if date_str:
                    mail_date = datetime.strptime(date_str[:16], "%Y-%m-%d %H:%M")
                    if mail_date >= cutoff:
                        return True
            except:
                pass
        return False
    
    def is_thread_older_than(self, thread: List[Dict[str, Any]], cutoff: datetime) -> bool:
        """Sprawdza czy wszystkie wiadomości w wątku są starsze niż cutoff"""
        for mail in thread:
            date_str = mail.get("date", "")
            try:
                if date_str:
                    mail_date = datetime.strptime(date_str[:16], "%Y-%m-%d %H:%M")
                    if mail_date >= cutoff:
                        return False
            except:
                pass
        return True
    
    def on_filter_changed(self):
        """Obsługa zmiany filtra czasu"""
        self.load_queue()
    
    def on_card_reply(self, mail):
        """Obsługa odpowiedzi na wiadomość"""
        # Odśwież kolejkę po pewnym czasie (aby mail zniknął)
        QTimer.singleShot(500, self.load_queue)
    
    def on_card_no_reply(self, mail):
        """Obsługa oznaczenia 'Bez odpowiedzi'"""
        # Odśwież kolejkę
        QTimer.singleShot(500, self.load_queue)
    
    def on_card_spam(self, mail):
        """Obsługa oznaczenia jako spam"""
        # Dodaj adres do listy spamu
        from_email = self.extract_email_address(mail.get("from", ""))
        if from_email:
            self.add_to_spam_list(from_email)
        
        # Usuń mail z kolejki
        self.load_queue()
    
    def on_card_replied_changed(self, mail, is_replied):
        """Obsługa zmiany statusu odpowiedzi"""
        # Jeśli zaznaczono jako odpowiedziano, odśwież kolejkę
        if is_replied:
            QTimer.singleShot(500, self.load_queue)
    
    def on_card_note_changed(self, mail, note_text):
        """Obsługa zmiany notatki"""
        # Zapisz notatkę w mail_view
        if hasattr(self.parent_view, 'save_mail_note'):
            self.parent_view.save_mail_note(mail, note_text)
    
    def extract_email_address(self, from_field: str) -> str:
        """Wyodrębnia adres email"""
        import re
        if not from_field:
            return ""
        match = re.match(r'^(.+?)\s*<(.+)>$', from_field.strip())
        if match:
            return match.group(2).strip()
        return from_field.strip()
    
    def add_to_spam_list(self, email: str):
        """Dodaje adres do listy spamu"""
        spam_file = Path("mail_client/spam_list.json")
        spam_list = []
        
        if spam_file.exists():
            try:
                with open(spam_file, 'r', encoding='utf-8') as f:
                    spam_list = json.load(f)
            except:
                pass
        
        if email not in spam_list:
            spam_list.append(email)
            
            try:
                spam_file.parent.mkdir(parents=True, exist_ok=True)
                with open(spam_file, 'w', encoding='utf-8') as f:
                    json.dump(spam_list, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Błąd zapisu listy spamu: {e}")
    
    def refresh(self):
        """Odświeża widok kolejki"""
        self.load_queue()
