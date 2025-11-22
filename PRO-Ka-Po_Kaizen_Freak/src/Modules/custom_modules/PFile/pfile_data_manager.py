"""
PFile Data Manager Module
Manages data operations for folders, files, tags, and history
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from loguru import logger

from .pfile_config import (
    FOLDERS_DATA_FILE,
    TAGS_DATA_FILE,
    HISTORY_DATA_FILE,
    SETTINGS_FILE,
    ITEM_TYPE_FOLDER,
    ITEM_TYPE_FILE
)


class PFileDataManager:
    """Manages P-File data operations (CRUD for folders, files, tags)"""
    
    def __init__(self):
        self.folders_data = self._load_json(FOLDERS_DATA_FILE)
        self.tags_data = self._load_json(TAGS_DATA_FILE)
        self.history_data = self._load_json(HISTORY_DATA_FILE)
        self.settings = self._load_json(SETTINGS_FILE)
    
    # =========================================================================
    # FILE I/O OPERATIONS
    # =========================================================================
    
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data from file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return {}
    
    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Save JSON data to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")
            return False
    
    def save_all(self) -> bool:
        """Save all data files"""
        try:
            self._save_json(FOLDERS_DATA_FILE, self.folders_data)
            self._save_json(TAGS_DATA_FILE, self.tags_data)
            self._save_json(HISTORY_DATA_FILE, self.history_data)
            self._save_json(SETTINGS_FILE, self.settings)
            return True
        except Exception as e:
            logger.error(f"Failed to save all data: {e}")
            return False
    
    # =========================================================================
    # FOLDER OPERATIONS
    # =========================================================================
    
    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Get all folders"""
        return self.folders_data.get('folders', [])
    
    def get_folder_by_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get folder by ID"""
        folders = self.get_all_folders()
        for folder in folders:
            if folder.get('id') == folder_id:
                return folder
        return None
    
    def add_folder(self, name: str, path: str, parent_id: Optional[str] = None, 
                   tags: Optional[List[str]] = None, comment: str = "") -> Dict[str, Any]:
        """
        Add new folder
        
        Returns:
            Created folder dict
        """
        import uuid
        
        folder = {
            'id': str(uuid.uuid4()),
            'type': ITEM_TYPE_FOLDER,
            'name': name,
            'path': path,
            'parent_id': parent_id,
            'tags': tags or [],
            'comment': comment,
            'created_at': datetime.now().isoformat(),
            'modified_at': datetime.now().isoformat(),
            'children': []
        }
        
        folders = self.get_all_folders()
        folders.append(folder)
        self.folders_data['folders'] = folders
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        self._add_to_history('add_folder', folder['name'])
        
        return folder
    
    def update_folder(self, folder_id: str, **kwargs) -> bool:
        """Update folder properties"""
        folder = self.get_folder_by_id(folder_id)
        if not folder:
            return False
        
        for key, value in kwargs.items():
            if key in folder:
                folder[key] = value
        
        folder['modified_at'] = datetime.now().isoformat()
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        self._add_to_history('update_folder', folder['name'])
        
        return True
    
    def delete_folder(self, folder_id: str) -> bool:
        """Delete folder and its children"""
        folders = self.get_all_folders()
        folder = self.get_folder_by_id(folder_id)
        
        if not folder:
            return False
        
        # Remove folder
        self.folders_data['folders'] = [f for f in folders if f['id'] != folder_id]
        
        # Remove associated files
        files = self.get_all_files()
        self.folders_data['files'] = [f for f in files if f.get('parent_id') != folder_id]
        
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        self._add_to_history('delete_folder', folder['name'])
        
        return True
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all files"""
        return self.folders_data.get('files', [])
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file by ID"""
        files = self.get_all_files()
        for file in files:
            if file.get('id') == file_id:
                return file
        return None
    
    def get_files_by_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get all files in a folder"""
        files = self.get_all_files()
        return [f for f in files if f.get('parent_id') == folder_id]
    
    def add_file(self, name: str, path: str, parent_id: str, 
                 size: int = 0, tags: Optional[List[str]] = None, 
                 comment: str = "") -> Dict[str, Any]:
        """
        Add new file
        
        Returns:
            Created file dict
        """
        import uuid
        
        file_item = {
            'id': str(uuid.uuid4()),
            'type': ITEM_TYPE_FILE,
            'name': name,
            'path': path,
            'parent_id': parent_id,
            'size': size,
            'tags': tags or [],
            'comment': comment,
            'created_at': datetime.now().isoformat(),
            'modified_at': datetime.now().isoformat(),
            'shared': False,
            'share_url': None,
            'share_expires_at': None
        }
        
        files = self.get_all_files()
        files.append(file_item)
        self.folders_data['files'] = files
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        self._add_to_history('add_file', file_item['name'])
        
        return file_item
    
    def update_file(self, file_id: str, **kwargs) -> bool:
        """Update file properties"""
        file_item = self.get_file_by_id(file_id)
        if not file_item:
            return False
        
        for key, value in kwargs.items():
            if key in file_item:
                file_item[key] = value
        
        file_item['modified_at'] = datetime.now().isoformat()
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        self._add_to_history('update_file', file_item['name'])
        
        return True
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file"""
        files = self.get_all_files()
        file_item = self.get_file_by_id(file_id)
        
        if not file_item:
            return False
        
        self.folders_data['files'] = [f for f in files if f['id'] != file_id]
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        self._add_to_history('delete_file', file_item['name'])
        
        return True
    
    # =========================================================================
    # TAG OPERATIONS
    # =========================================================================
    
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all tags"""
        return self.tags_data.get('tags', [])
    
    def get_tag_by_name(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get tag by name"""
        tags = self.get_all_tags()
        for tag in tags:
            if tag.get('name') == tag_name:
                return tag
        return None
    
    def add_tag(self, name: str, color: str) -> Dict[str, Any]:
        """Add new tag"""
        tag = {
            'name': name,
            'color': color,
            'created_at': datetime.now().isoformat()
        }
        
        tags = self.get_all_tags()
        tags.append(tag)
        self.tags_data['tags'] = tags
        self._save_json(TAGS_DATA_FILE, self.tags_data)
        
        return tag
    
    def delete_tag(self, tag_name: str) -> bool:
        """Delete tag and remove from all items"""
        tags = self.get_all_tags()
        self.tags_data['tags'] = [t for t in tags if t['name'] != tag_name]
        
        # Remove tag from folders
        for folder in self.get_all_folders():
            if tag_name in folder.get('tags', []):
                folder['tags'].remove(tag_name)
        
        # Remove tag from files
        for file in self.get_all_files():
            if tag_name in file.get('tags', []):
                file['tags'].remove(tag_name)
        
        self._save_json(TAGS_DATA_FILE, self.tags_data)
        self._save_json(FOLDERS_DATA_FILE, self.folders_data)
        
        return True
    
    def get_items_by_tag(self, tag_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all items (folders + files) with specific tag"""
        folders = [f for f in self.get_all_folders() if tag_name in f.get('tags', [])]
        files = [f for f in self.get_all_files() if tag_name in f.get('tags', [])]
        
        return {
            'folders': folders,
            'files': files
        }
    
    # =========================================================================
    # HISTORY OPERATIONS
    # =========================================================================
    
    def _add_to_history(self, action: str, item_name: str):
        """Add entry to history"""
        history = self.history_data.get('history', [])
        max_entries = self.history_data.get('max_entries', 100)
        
        entry = {
            'action': action,
            'item_name': item_name,
            'timestamp': datetime.now().isoformat()
        }
        
        history.insert(0, entry)
        
        # Limit history size
        if len(history) > max_entries:
            history = history[:max_entries]
        
        self.history_data['history'] = history
        self._save_json(HISTORY_DATA_FILE, self.history_data)
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent history"""
        history = self.history_data.get('history', [])
        return history[:limit]
    
    def clear_history(self) -> bool:
        """Clear all history"""
        self.history_data['history'] = []
        return self._save_json(HISTORY_DATA_FILE, self.history_data)
    
    # =========================================================================
    # SETTINGS OPERATIONS
    # =========================================================================
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set setting value"""
        self.settings[key] = value
        return self._save_json(SETTINGS_FILE, self.settings)
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    def search_items(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search folders and files by name or comment"""
        query_lower = query.lower()
        
        folders = [
            f for f in self.get_all_folders()
            if query_lower in f.get('name', '').lower() or 
               query_lower in f.get('comment', '').lower()
        ]
        
        files = [
            f for f in self.get_all_files()
            if query_lower in f.get('name', '').lower() or 
               query_lower in f.get('comment', '').lower()
        ]
        
        return {
            'folders': folders,
            'files': files
        }
