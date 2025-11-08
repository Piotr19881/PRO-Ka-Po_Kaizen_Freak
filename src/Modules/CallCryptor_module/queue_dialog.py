"""
Processing Queue Dialog for CallCryptor

Displays a list of tasks being processed with individual and overall progress.
Supports graceful cancellation during processing.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QProgressBar, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor
import logging

logger = logging.getLogger(__name__)


class ProcessingWorker(QThread):
    """Worker thread for processing transcriptions and summaries"""
    
    progress_updated = pyqtSignal(int, str)  # row, status
    task_completed = pyqtSignal(int, bool, str)  # row, success, message
    all_completed = pyqtSignal()
    
    def __init__(self, tasks, db_path, user_id):
        """
        Args:
            tasks: List of dicts with keys: 'row', 'action', 'recording_id', 'file_path'
            db_path: Path to CallCryptor database
            user_id: User ID for database queries
        """
        super().__init__()
        self.tasks = tasks
        self.db_path = db_path
        self.user_id = user_id
        self.should_stop = False
        self.db_manager = None  # Will be created in run() method (same thread)
        
    def run(self):
        """Process all tasks sequentially"""
        # Create database connection in worker thread (thread-safe)
        from .callcryptor_database import CallCryptorDatabase
        self.db_manager = CallCryptorDatabase(self.db_path)
        logger.info(f"[QueueWorker] Database connection created in thread")
        
        for task in self.tasks:
            if self.should_stop:
                break
                
            row = task['row']
            action = task['action']
            recording_id = task['recording_id']
            
            try:
                self.progress_updated.emit(row, 'processing')
                
                if action == 'transcribe':
                    success = self._do_transcription(recording_id)
                elif action == 'summarize':
                    success = self._do_summary(recording_id)
                else:
                    success = False
                    
                if success:
                    self.task_completed.emit(row, True, 'completed')
                else:
                    self.task_completed.emit(row, False, 'failed')
                    
            except Exception as e:
                logger.error(f"Error processing task {row}: {e}")
                self.task_completed.emit(row, False, str(e))
                
        self.all_completed.emit()
        
    def _do_transcription(self, recording_id):
        """
        Perform transcription
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"[QueueWorker] Starting transcription for {recording_id}")
            
            # Get recording data from worker's own db connection
            recording = self._get_recording(recording_id)
            if not recording:
                logger.error(f"[QueueWorker] Recording {recording_id} not found")
                return False
            
            logger.info(f"[QueueWorker] Found recording: {recording.get('file_name')}")
            
            # Call parent view's transcription method
            # Since _transcribe_recording shows dialog, we need to handle it differently
            # For queue processing, we need direct transcription without UI
            
            from pathlib import Path
            file_path = recording.get('file_path')
            if not file_path or not Path(file_path).exists():
                logger.error(f"[QueueWorker] File not found: {file_path}")
                return False
            
            logger.info(f"[QueueWorker] File exists: {file_path}")
            
            # Get AI manager and perform transcription
            from ...Modules.AI_module.ai_logic import get_ai_manager, load_ai_settings, AIProvider
            ai_manager = get_ai_manager()
            settings = load_ai_settings()
            api_keys = settings.get('api_keys', {})
            
            # Check available providers supporting transcription
            if api_keys.get('gemini'):
                provider_key, provider_enum = 'gemini', AIProvider.GEMINI
            elif api_keys.get('openai'):
                provider_key, provider_enum = 'openai', AIProvider.OPENAI
            else:
                logger.error("[QueueWorker] No API keys configured for transcription")
                return False
            
            logger.info(f"[QueueWorker] Using provider: {provider_key}")
            
            # Configure provider with user's selected model
            selected_model = settings.get('models', {}).get(provider_key)
            
            ai_manager.set_provider(
                provider=provider_enum,
                api_key=api_keys.get(provider_key),
                model=selected_model
            )
            
            # Perform transcription
            logger.info(f"[QueueWorker] Starting AI transcription with model: {selected_model}...")
            
            try:
                transcription_text = ai_manager.transcribe_audio(file_path, language="pl")
            except ValueError as e:
                # Model doesn't support audio transcription
                logger.error(f"[QueueWorker] Model error: {e}")
                error_msg = str(e)
                if "does not support" in error_msg.lower() or "not support" in error_msg.lower():
                    logger.error(f"[QueueWorker] Model {selected_model} does not support audio transcription")
                return False
            except Exception as e:
                logger.error(f"[QueueWorker] Transcription failed with error: {e}")
                return False
            
            if not transcription_text:
                logger.error("[QueueWorker] Transcription returned empty text")
                return False
            
            logger.info(f"[QueueWorker] Transcription successful, length: {len(transcription_text)}")
            
            # Update database
            if self.db_manager:
                self.db_manager.update_recording(
                    recording_id=recording_id,
                    updates={
                        'transcription_text': transcription_text,
                        'transcription_status': 'completed'
                    }
                )
                logger.info(f"[QueueWorker] Database updated for {recording_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"[QueueWorker] Error transcribing {recording_id}: {e}", exc_info=True)
            return False
    
    def _get_recording(self, recording_id):
        """Get recording from database (thread-safe)"""
        if not self.db_manager:
            return None
        
        try:
            # Get all recordings and find the one we need
            all_recordings = self.db_manager.get_all_recordings(self.user_id)
            for rec in all_recordings:
                if str(rec.get('id')) == str(recording_id):
                    return rec
        except Exception as e:
            logger.error(f"[QueueWorker] Error getting recording {recording_id}: {e}")
        
        return None
        
    def _do_summary(self, recording_id):
        """
        Perform AI summary
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"[QueueWorker] Starting summary for {recording_id}")
            
            # Get recording data from worker's own db connection
            recording = self._get_recording(recording_id)
            if not recording:
                logger.error(f"[QueueWorker] Recording {recording_id} not found")
                return False
            
            logger.info(f"[QueueWorker] Found recording: {recording.get('file_name')}")
            
            # Check if transcription exists
            transcription_text = recording.get('transcription_text', '')
            if not transcription_text:
                logger.error(f"[QueueWorker] No transcription available for {recording_id}")
                return False
            
            logger.info(f"[QueueWorker] Transcription exists, length: {len(transcription_text)}")
            
            # Get AI manager and configure with user's active provider
            from ...Modules.AI_module.ai_logic import get_ai_manager, load_ai_settings, AIProvider
            ai_manager = get_ai_manager()
            settings = load_ai_settings()
            
            # Get active provider from settings (same as normal summary)
            active_provider = settings.get('provider')
            api_keys = settings.get('api_keys', {})
            
            if not active_provider:
                logger.error("[QueueWorker] No active provider configured")
                return False
            
            # Check if API key exists for active provider
            api_key = api_keys.get(active_provider, '')
            if not api_key:
                logger.error(f"[QueueWorker] No API key for provider: {active_provider}")
                return False
            
            # Map provider key to enum
            provider_map = {
                'openai': AIProvider.OPENAI,
                'gemini': AIProvider.GEMINI,
                'claude': AIProvider.CLAUDE,
                'grok': AIProvider.GROK,
                'deepseek': AIProvider.DEEPSEEK
            }
            
            provider_enum = provider_map.get(active_provider)
            if not provider_enum:
                logger.error(f"[QueueWorker] Unknown provider: {active_provider}")
                return False
            
            logger.info(f"[QueueWorker] Using active provider: {active_provider}")
            
            # Get model from settings
            selected_model = settings.get('models', {}).get(active_provider, '')
            
            # Configure provider with user's selected model
            ai_manager.set_provider(
                provider=provider_enum,
                api_key=api_key,
                model=selected_model
            )
            
            # Create summary prompt
            prompt = f"""Przeanalizuj poniższą transkrypcję rozmowy telefonicznej i utwórz jej podsumowanie.

Transkrypcja:
{transcription_text}

Proszę o:
1. Krótkie streszczenie (2-3 zdania)
2. Listę kluczowych punktów
3. Wyodrębnione zadania do wykonania (jeśli są)
4. Ewentualne terminy lub ważne daty

Format odpowiedzi:
**Podsumowanie:**
[streszczenie]

**Kluczowe punkty:**
- [punkt 1]
- [punkt 2]

**Zadania do wykonania:**
- [zadanie 1]
- [zadanie 2]

**Terminy:**
- [termin 1]
"""
            
            # Get summary
            logger.info(f"[QueueWorker] Requesting AI summary...")
            summary_response = ai_manager.generate_response(prompt)
            
            if not summary_response or not summary_response.text:
                logger.error("[QueueWorker] Summary returned empty result")
                return False
            
            summary_result = summary_response.text
            logger.info(f"[QueueWorker] Summary generated, length: {len(summary_result)}")
            
            # Extract tasks from summary (simple parsing)
            tasks = []
            if "**Zadania do wykonania:**" in summary_result:
                tasks_section = summary_result.split("**Zadania do wykonania:**")[1]
                if "**" in tasks_section:
                    tasks_section = tasks_section.split("**")[0]
                task_lines = [line.strip("- ").strip() for line in tasks_section.split("\n") if line.strip().startswith("-")]
                tasks = task_lines
            
            logger.info(f"[QueueWorker] Extracted {len(tasks)} tasks from summary")
            
            # Update database with summary
            if self.db_manager:
                import json
                self.db_manager.update_recording(
                    recording_id=recording_id,
                    updates={
                        'ai_summary_text': summary_result,
                        'ai_summary_tasks': json.dumps(tasks, ensure_ascii=False),
                        'ai_summary_status': 'completed'
                    }
                )
                logger.info(f"[QueueWorker] Summary saved to database for {recording_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"[QueueWorker] Error summarizing {recording_id}: {e}", exc_info=True)
            return False
        
    def stop(self):
        """Request worker to stop processing"""
        self.should_stop = True


class ProcessingQueueDialog(QDialog):
    """Dialog showing processing queue with progress"""
    
    def __init__(self, tasks, parent_view, theme_manager, t):
        """
        Args:
            tasks: List of dicts with keys: 'action', 'recording_id', 'file_path'
            parent_view: CallCryptorView instance
            theme_manager: ThemeManager instance
            t: Translation function
        """
        super().__init__(parent_view)
        self.tasks = tasks
        self.parent_view = parent_view
        self.theme_manager = theme_manager
        self.t = t
        self.worker = None
        
        # Get database path and user_id from parent view
        self.db_path = str(parent_view.db_manager.db_path) if parent_view.db_manager else None
        self.user_id = parent_view.user_id
        
        self._setup_ui()
        self._apply_theme()
        self._start_processing()
        
    def _setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle(self.t('callcryptor.queue.dialog_title'))
        self.setMinimumSize(700, 500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Overall progress
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel(self.t('callcryptor.queue.progress_total').format(current=0, total=len(self.tasks)))
        progress_layout.addWidget(self.progress_label)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximum(len(self.tasks))
        self.overall_progress.setValue(0)
        progress_layout.addWidget(self.overall_progress, stretch=1)
        
        layout.addLayout(progress_layout)
        
        # Task table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            self.t('callcryptor.table.file_name'),
            self.t('callcryptor.queue.action_transcribe') + '/' + self.t('callcryptor.queue.action_summarize'),
            'Status',
            'Progress'
        ])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 150)
        
        self.table.setRowCount(len(self.tasks))
        
        # Populate table
        for row, task in enumerate(self.tasks):
            # File name
            name_item = QTableWidgetItem(task.get('file_path', '').split('/')[-1])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # Action
            action_text = self.t(f'callcryptor.queue.action_{task["action"]}')
            action_item = QTableWidgetItem(action_text)
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, action_item)
            
            # Status
            status_item = QTableWidgetItem(self.t('callcryptor.queue.status_waiting'))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, status_item)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setMaximum(100)
            progress_bar.setValue(0)
            self.table.setCellWidget(row, 3, progress_bar)
            
            # Store original task data with row index
            task['row'] = row
            
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.stop_button = QPushButton(self.t('callcryptor.queue.button_stop'))
        self.stop_button.clicked.connect(self._on_stop_clicked)
        button_layout.addWidget(self.stop_button)
        
        self.close_button = QPushButton(self.t('callcryptor.queue.button_close'))
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def _apply_theme(self):
        """Apply theme colors"""
        colors = self.theme_manager.get_current_colors()
        
        # Map theme colors to expected names
        bg_main = colors.get('bg_main', '#1E1E1E')
        bg_secondary = colors.get('bg_secondary', '#2D2D2D')
        text_primary = colors.get('text_primary', '#FFFFFF')
        text_secondary = colors.get('text_secondary', '#B0B0B0')
        accent_primary = colors.get('accent_primary', '#64B5F6')
        accent_hover = colors.get('accent_hover', '#42A5F5')
        border_light = colors.get('border_light', '#404040')
        
        # Dialog background
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: {text_primary};
            }}
            QTableWidget {{
                background-color: {bg_secondary};
                color: {text_primary};
                gridline-color: {border_light};
                border: 1px solid {border_light};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {bg_secondary};
                color: {text_primary};
                padding: 5px;
                border: 1px solid {border_light};
            }}
            QProgressBar {{
                border: 1px solid {border_light};
                border-radius: 3px;
                text-align: center;
                background-color: {bg_secondary};
            }}
            QProgressBar::chunk {{
                background-color: {accent_primary};
            }}
            QPushButton {{
                background-color: {accent_primary};
                color: {bg_main};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {bg_secondary};
                color: {text_secondary};
            }}
        """)
        
    def _start_processing(self):
        """Start worker thread to process tasks"""
        if not self.db_path or not self.user_id:
            logger.error("[QueueDialog] Cannot start worker - no db_path or user_id")
            return
        
        self.worker = ProcessingWorker(self.tasks, self.db_path, self.user_id)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.task_completed.connect(self._on_task_completed)
        self.worker.all_completed.connect(self._on_all_completed)
        self.worker.start()
        
    def _on_progress_updated(self, row, status):
        """Update task status in table"""
        status_text = self.t(f'callcryptor.queue.status_{status}')
        status_item = self.table.item(row, 2)
        if status_item:
            status_item.setText(status_text)
            
        # Update progress bar to indeterminate during processing
        progress_bar = self.table.cellWidget(row, 3)
        if progress_bar and status == 'processing':
            progress_bar.setMaximum(0)  # Indeterminate
            
    def _on_task_completed(self, row, success, message):
        """Handle task completion"""
        # Update status
        if success:
            status_text = self.t('callcryptor.queue.status_completed')
            color = QColor(0, 200, 0)  # Green
        else:
            if message == 'cancelled':
                status_text = self.t('callcryptor.queue.status_cancelled')
                color = QColor(150, 150, 150)  # Gray
            else:
                status_text = self.t('callcryptor.queue.status_failed')
                color = QColor(255, 0, 0)  # Red
                
        status_item = self.table.item(row, 2)
        if status_item:
            status_item.setText(status_text)
            status_item.setForeground(color)
            
        # Update progress bar
        progress_bar = self.table.cellWidget(row, 3)
        if progress_bar:
            progress_bar.setMaximum(100)
            progress_bar.setValue(100 if success else 0)
            
        # Update overall progress
        completed = sum(1 for i in range(self.table.rowCount()) 
                       if self.table.item(i, 2) and 
                       self.table.item(i, 2).text() in [
                           self.t('callcryptor.queue.status_completed'),
                           self.t('callcryptor.queue.status_failed'),
                           self.t('callcryptor.queue.status_cancelled')
                       ])
        self.overall_progress.setValue(completed)
        self.progress_label.setText(
            self.t('callcryptor.queue.progress_total').format(
                current=completed,
                total=len(self.tasks)
            )
        )
        
    def _on_all_completed(self):
        """Handle all tasks completed"""
        self.stop_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Check if stopped by user
        if self.worker and self.worker.should_stop:
            self.progress_label.setText(self.t('callcryptor.queue.stopped_by_user'))
        else:
            self.progress_label.setText(self.t('callcryptor.queue.completed_all'))
            
    def _on_stop_clicked(self):
        """Handle stop button click"""
        if self.worker:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)  # Wait max 3 seconds
        event.accept()
