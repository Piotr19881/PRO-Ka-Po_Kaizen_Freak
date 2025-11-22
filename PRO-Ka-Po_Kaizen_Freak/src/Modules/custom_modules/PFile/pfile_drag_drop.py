"""
PFile Drag and Drop Handler
Obsługa przeciągania plików do i z aplikacji PFile
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Callable
from PyQt6.QtCore import Qt, QUrl, QMimeData, pyqtSignal, QObject
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QDrag
from PyQt6.QtWidgets import QWidget, QMessageBox
from loguru import logger


class PFileDragDropHandler(QObject):
    """
    Handler obsługujący drag and drop dla modułu PFile.
    
    Funkcjonalności:
    - Przeciąganie plików z zewnątrz do aplikacji (import)
    - Przeciąganie plików z aplikacji na zewnątrz (export)
    - Obsługa wielu plików jednocześnie
    - Walidacja i feedback dla użytkownika
    """
    
    # Sygnały
    files_dropped = pyqtSignal(list)  # Emituje listę ścieżek plików do importu
    export_requested = pyqtSignal(list, str)  # Emituje listę plików i ścieżkę docelową
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Inicjalizacja handlera drag and drop.
        
        Args:
            parent: Widget rodzica
        """
        super().__init__(parent)
        self.parent_widget = parent
        self.allowed_extensions = None  # None = wszystkie, albo lista ['.pdf', '.jpg', ...]
        self.max_file_size_mb = 100  # Maksymalny rozmiar pliku w MB
        
        logger.info("PFileDragDropHandler initialized")
    
    def enable_drop(self, widget: QWidget):
        """
        Włącza obsługę drop (przyjmowanie plików) dla widgetu.
        
        Args:
            widget: Widget który ma przyjmować pliki
        """
        widget.setAcceptDrops(True)
        
        # Podpinamy metody obsługi eventów
        original_drag_enter = widget.dragEnterEvent
        original_drag_move = widget.dragMoveEvent
        original_drop = widget.dropEvent
        
        def drag_enter_event(event: QDragEnterEvent):
            if self._validate_drag_enter(event):
                event.acceptProposedAction()
            else:
                event.ignore()
        
        def drag_move_event(event: QDragMoveEvent):
            if self._validate_drag_move(event):
                event.acceptProposedAction()
            else:
                event.ignore()
        
        def drop_event(event: QDropEvent):
            self._handle_drop(event)
        
        # Nadpisz metody
        widget.dragEnterEvent = drag_enter_event
        widget.dragMoveEvent = drag_move_event
        widget.dropEvent = drop_event
        
        logger.debug(f"Drop enabled for widget: {widget.__class__.__name__}")
    
    def enable_drag(self, widget: QWidget, get_file_paths_callback: Callable[[], List[str]]):
        """
        Włącza obsługę drag (przeciąganie plików z aplikacji) dla widgetu.
        
        Args:
            widget: Widget który ma umożliwiać przeciąganie
            get_file_paths_callback: Funkcja zwracająca listę ścieżek plików do przeciągnięcia
        """
        widget.setDragEnabled(True)
        
        # Zapisz callback
        self.get_file_paths_callback = get_file_paths_callback
        
        # Podpinamy metodę obsługi start drag
        original_mouse_press = widget.mousePressEvent
        original_mouse_move = widget.mouseMoveEvent
        
        self.drag_start_position = None
        
        def mouse_press_event(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_position = event.pos()
            if original_mouse_press:
                original_mouse_press(event)
        
        def mouse_move_event(event):
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                return
            
            if not self.drag_start_position:
                return
            
            # Sprawdź czy przesunięcie jest wystarczające aby rozpocząć drag
            if (event.pos() - self.drag_start_position).manhattanLength() < 10:
                return
            
            # Rozpocznij operację drag
            self._start_drag(widget)
            
            if original_mouse_move:
                original_mouse_move(event)
        
        widget.mousePressEvent = mouse_press_event
        widget.mouseMoveEvent = mouse_move_event
        
        logger.debug(f"Drag enabled for widget: {widget.__class__.__name__}")
    
    def set_allowed_extensions(self, extensions: Optional[List[str]]):
        """
        Ustaw dozwolone rozszerzenia plików.
        
        Args:
            extensions: Lista rozszerzeń (np. ['.pdf', '.jpg']) lub None dla wszystkich
        """
        self.allowed_extensions = extensions
        logger.debug(f"Allowed extensions set to: {extensions}")
    
    def set_max_file_size_mb(self, size_mb: int):
        """
        Ustaw maksymalny rozmiar pliku w MB.
        
        Args:
            size_mb: Rozmiar w megabajtach
        """
        self.max_file_size_mb = size_mb
        logger.debug(f"Max file size set to: {size_mb} MB")
    
    def _validate_drag_enter(self, event: QDragEnterEvent) -> bool:
        """
        Waliduj czy drag enter jest akceptowalny.
        
        Args:
            event: Event drag enter
            
        Returns:
            True jeśli można zaakceptować
        """
        mime_data = event.mimeData()
        
        # Sprawdź czy zawiera pliki
        if not mime_data.hasUrls():
            logger.debug("Drag rejected: no URLs in mime data")
            return False
        
        # Sprawdź czy wszystkie URL to pliki
        urls = mime_data.urls()
        for url in urls:
            if not url.isLocalFile():
                logger.debug(f"Drag rejected: non-local file {url}")
                return False
            
            file_path = url.toLocalFile()
            
            # Sprawdź rozszerzenie
            if self.allowed_extensions:
                ext = Path(file_path).suffix.lower()
                if ext not in self.allowed_extensions:
                    logger.debug(f"Drag rejected: extension {ext} not allowed")
                    return False
            
            # Sprawdź rozmiar
            if os.path.isfile(file_path):
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb > self.max_file_size_mb:
                    logger.debug(f"Drag rejected: file too large ({size_mb:.2f} MB)")
                    return False
        
        return True
    
    def _validate_drag_move(self, event: QDragMoveEvent) -> bool:
        """
        Waliduj czy drag move jest akceptowalny.
        
        Args:
            event: Event drag move
            
        Returns:
            True jeśli można zaakceptować
        """
        # Podobna walidacja jak dla drag enter
        return event.mimeData().hasUrls()
    
    def _handle_drop(self, event: QDropEvent):
        """
        Obsłuż drop (upuszczenie plików).
        
        Args:
            event: Event drop
        """
        mime_data = event.mimeData()
        
        if not mime_data.hasUrls():
            event.ignore()
            return
        
        # Zbierz ścieżki plików
        file_paths = []
        invalid_files = []
        
        for url in mime_data.urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                
                # Walidacja rozszerzenia
                if self.allowed_extensions:
                    ext = Path(file_path).suffix.lower()
                    if ext not in self.allowed_extensions:
                        invalid_files.append((file_path, f"Nieprawidłowe rozszerzenie: {ext}"))
                        continue
                
                # Walidacja rozmiaru
                if os.path.isfile(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if size_mb > self.max_file_size_mb:
                        invalid_files.append((file_path, f"Plik za duży: {size_mb:.2f} MB"))
                        continue
                
                file_paths.append(file_path)
        
        # Pokaż ostrzeżenie dla nieprawidłowych plików
        if invalid_files and self.parent_widget:
            msg = "Następujące pliki zostały odrzucone:\n\n"
            for path, reason in invalid_files[:5]:  # Pokaż max 5
                msg += f"• {Path(path).name}: {reason}\n"
            if len(invalid_files) > 5:
                msg += f"\n... i {len(invalid_files) - 5} więcej"
            
            QMessageBox.warning(
                self.parent_widget,
                "Odrzucone pliki",
                msg
            )
        
        # Emit sygnał z prawidłowymi plikami
        if file_paths:
            logger.info(f"Files dropped: {len(file_paths)} files")
            self.files_dropped.emit(file_paths)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def _start_drag(self, widget: QWidget):
        """
        Rozpocznij operację drag (przeciąganie z aplikacji).
        
        Args:
            widget: Widget źródłowy
        """
        # Pobierz ścieżki plików do przeciągnięcia
        if not hasattr(self, 'get_file_paths_callback'):
            logger.warning("Drag aborted: no get_file_paths_callback set")
            return
        
        file_paths = self.get_file_paths_callback()
        
        if not file_paths:
            logger.debug("Drag aborted: no files selected")
            return
        
        # Utwórz mime data
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(path) for path in file_paths]
        mime_data.setUrls(urls)
        
        # Utwórz QDrag
        drag = QDrag(widget)
        drag.setMimeData(mime_data)
        
        # Wykonaj operację drag
        result = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        
        if result == Qt.DropAction.CopyAction:
            logger.info(f"Drag completed: {len(file_paths)} files copied")
        elif result == Qt.DropAction.MoveAction:
            logger.info(f"Drag completed: {len(file_paths)} files moved")
        else:
            logger.debug("Drag cancelled")


class PFileDropZone(QWidget):
    """
    Dedykowany widget strefy drop - wizualny feedback dla użytkownika.
    Może być używany jako overlay lub stały element UI.
    """
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()
        
        self.drag_handler = PFileDragDropHandler(self)
        self.drag_handler.files_dropped.connect(self.files_dropped.emit)
        self.drag_handler.enable_drop(self)
    
    def _setup_ui(self):
        """Setup UI strefy drop"""
        from PyQt6.QtWidgets import QVBoxLayout, QLabel
        from PyQt6.QtCore import Qt
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ikona
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 48pt;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Tekst
        text_label = QLabel("Przeciągnij pliki tutaj")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet("font-size: 14pt; color: #666;")
        layout.addWidget(text_label)
        
        # Styl tła
        self.setStyleSheet("""
            PFileDropZone {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
            PFileDropZone:hover {
                border-color: #999;
                background-color: #f0f0f0;
            }
        """)
        
        self.setMinimumSize(300, 200)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Wizualny feedback przy wejściu drag"""
        if event.mimeData().hasUrls():
            self.setStyleSheet("""
                PFileDropZone {
                    border: 3px solid #4CAF50;
                    border-radius: 10px;
                    background-color: #e8f5e9;
                }
            """)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Przywróć normalny styl po opuszczeniu"""
        self._setup_ui()
    
    def dropEvent(self, event: QDropEvent):
        """Przywróć normalny styl po drop"""
        self._setup_ui()
