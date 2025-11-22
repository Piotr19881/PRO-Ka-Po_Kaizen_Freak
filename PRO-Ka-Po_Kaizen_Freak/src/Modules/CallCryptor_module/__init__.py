"""
CallCryptor Module
==================

Moduł zarządzania nagraniami rozmów telefonicznych z możliwością:
- Skanowania folderów lokalnych i skrzynek e-mail
- Automatycznej transkrypcji nagrań
- Generowania podsumowań AI
- Tworzenia notatek i zadań z nagrań
- Organizacji przez tagi i archiwizację
- Synchronizacji metadanych z serwerem (privacy-first, opt-in)
"""

__version__ = "2.0.0"
__author__ = "PRO-Ka-Po Team"

# Sync infrastructure exports
from .recording_api_client import RecordingsAPIClient, APIResponse
from .recordings_sync_manager import RecordingsSyncManager

__all__ = [
    'RecordingsAPIClient',
    'APIResponse',
    'RecordingsSyncManager'
]
