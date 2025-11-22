"""
File Upload Dialog for TeamWork Module
Dialog do uploadu plików do wątków tematycznych z integracją Backblaze B2
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
import requests
from typing import Optional


class FileUploadWorker(QThread):
    """Worker thread dla uploadu pliku do API"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, api_url: str, topic_id: int, file_path: str, 
                 is_important: bool, auth_token: str):
        super().__init__()
        self.api_url = api_url
        self.topic_id = topic_id
        self.file_path = file_path
        self.is_important = is_important
        self.auth_token = auth_token
    
    def run(self):
        try:
            # Przygotuj plik
            file_name = Path(self.file_path).name
            
            with open(self.file_path, 'rb') as f:
                files = {'file': (file_name, f)}
                params = {'is_important': str(self.is_important).lower()}
                headers = {'Authorization': f'Bearer {self.auth_token}'}
                
                # Endpoint: POST /api/teamwork/topics/{topic_id}/files
                url = f"{self.api_url}/api/teamwork/topics/{self.topic_id}/files"
                
                # Wyślij request
                response = requests.post(
                    url,
                    files=files,
                    params=params,
                    headers=headers,
                    timeout=300  # 5 minut timeout dla dużych plików
                )
                
                if response.status_code == 201:
                    self.progress.emit(100)
                    self.finished.emit(response.json())
                else:
                    self.error.emit(f"Błąd API: {response.status_code} - {response.text}")
                    
        except Exception as e:
            self.error.emit(f"Błąd podczas uploadu: {str(e)}")


class FileUploadDialog(QDialog):
    """
    Dialog do wyboru i uploadu pliku do wątku tematycznego
    
    Features:
    - Wybór pliku z dysku
    - Opcja oznaczenia jako ważne
    - Progress bar podczas uploadu
    - Integracja z API (Backblaze B2 w tle)
    """
    
    file_uploaded = pyqtSignal(dict)  # Emituje dane uploadu pliku
    
    def __init__(self, topic_id: int, topic_name: str, api_url: str, 
                 auth_token: str, parent=None):
        super().__init__(parent)
        self.topic_id = topic_id
        self.topic_name = topic_name
        self.api_url = api_url
        self.auth_token = auth_token
        self.selected_file_path: Optional[str] = None
        self.upload_worker: Optional[FileUploadWorker] = None
        
        self._init_ui()
        self.setWindowTitle("Upload pliku")
        self.resize(500, 250)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(f"Upload pliku do wątku: {self.topic_name}")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Nie wybrano pliku")
        self.file_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_label, 1)
        
        browse_btn = QPushButton("Wybierz plik")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # Important checkbox
        self.important_checkbox = QCheckBox("Oznacz jako ważny plik")
        layout.addWidget(self.important_checkbox)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self._start_upload)
        button_layout.addWidget(self.upload_btn)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def _browse_file(self):
        """Otwórz dialog wyboru pliku"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik do uploadu",
            "",
            "Wszystkie pliki (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            file_name = Path(file_path).name
            file_size = Path(file_path).stat().st_size
            
            # Format rozmiaru
            size_str = self._format_file_size(file_size)
            
            self.file_label.setText(f"{file_name} ({size_str})")
            self.file_label.setStyleSheet("color: #000;")
            self.upload_btn.setEnabled(True)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Formatuj rozmiar pliku"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _start_upload(self):
        """Rozpocznij upload pliku"""
        if not self.selected_file_path:
            return
        
        # Disable buttons
        self.upload_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Uploading...")
        
        # Create worker thread
        self.upload_worker = FileUploadWorker(
            api_url=self.api_url,
            topic_id=self.topic_id,
            file_path=self.selected_file_path,
            is_important=self.important_checkbox.isChecked(),
            auth_token=self.auth_token
        )
        
        # Connect signals
        self.upload_worker.progress.connect(self.progress_bar.setValue)
        self.upload_worker.finished.connect(self._on_upload_success)
        self.upload_worker.error.connect(self._on_upload_error)
        
        # Start upload
        self.upload_worker.start()
    
    def _on_upload_success(self, file_data: dict):
        """Upload zakończony sukcesem"""
        self.status_label.setText("Upload zakończony!")
        self.status_label.setStyleSheet("color: green; font-size: 9pt;")
        
        # Emit signal
        self.file_uploaded.emit(file_data)
        
        # Show success message
        QMessageBox.information(
            self,
            "Sukces",
            f"Plik '{file_data.get('file_name', 'unnamed')}' został przesłany!"
        )
        
        self.accept()
    
    def _on_upload_error(self, error_msg: str):
        """Błąd podczas uploadu"""
        self.status_label.setText(f"Błąd: {error_msg}")
        self.status_label.setStyleSheet("color: red; font-size: 9pt;")
        self.upload_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(
            self,
            "Błąd uploadu",
            f"Nie udało się przesłać pliku:\n{error_msg}"
        )
