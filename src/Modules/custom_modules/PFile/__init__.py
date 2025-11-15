"""
PFile Module - File and Folder Management with Cloud Sharing
=============================================================

This module provides comprehensive file and folder management capabilities
with tag-based organization and Backblaze B2 cloud sharing integration.

Main Components:
- pfile_module.py: Main QWidget module
- pfile_config.py: Configuration, constants, and theme styles
- pfile_data_manager.py: Data operations (folders, files, tags)
- pfile_api_client.py: API client for Backblaze B2 file sharing
- widgets/: Dialog widgets (tag management, sharing, etc.)

Features:
- Folder and file management with hierarchical structure
- Tag-based organization system
- Dual view modes (folders/files or tags)
- Comments and notes for items
- Context menu operations
- Backblaze B2 cloud sharing with email notifications
- History tracking
- Filtering and search
- Quick access panel
- Full i18n support (pl/en/de)
- Theme integration

Author: PRO-Ka-Po Kaizen Freak Team
License: See LICENSE file
"""

from .pfile_module import PFileWidget

__all__ = ['PFileWidget']
__version__ = '1.0.0'
