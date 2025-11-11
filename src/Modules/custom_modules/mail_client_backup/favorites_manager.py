"""
Zarządzanie ulubionymi plikami dla okna komponowania wiadomości

Funkcje:
- Wczytywanie ulubionych plików
- Zarządzanie grupami plików
- Normalizacja danych
- Populacja widgetów (drzewo, lista ostatnio używanych)
- Śledzenie użycia plików
"""

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_favorite_files_from_disk() -> List[Dict[str, Any]]:
    """Ładuje ulubione pliki z dysku."""
    favorites_file = Path("mail_client/favorite_files.json")
    if favorites_file.exists():
        try:
            with open(favorites_file, "r", encoding="utf-8") as handle:
                raw_data = json.load(handle)
            if not isinstance(raw_data, list):
                return []
            normalized: List[Dict[str, Any]] = []
            for entry in raw_data:
                if isinstance(entry, dict):
                    normalized_entry = normalize_favorite_entry(entry)
                    if normalized_entry is not None:
                        normalized.append(normalized_entry)
            return normalized
        except Exception:
            return []
    return []


def load_group_definitions_from_disk() -> Dict[str, Dict[str, str]]:
    """Ładuje definicje grup ulubionych plików."""
    groups_file = Path("mail_client/file_groups.json")
    if groups_file.exists():
        try:
            with open(groups_file, "r", encoding="utf-8") as handle:
                raw_data = json.load(handle)
            result: Dict[str, Dict[str, str]] = {}
            if isinstance(raw_data, list):
                for entry in raw_data:
                    name = entry.get("name")
                    if not name:
                        continue
                    result[name] = {
                        "icon": entry.get("icon", "📂"),
                        "color": entry.get("color", "#FFFFFF"),
                    }
            return result
        except Exception:
            return {}
    return {}


def normalize_favorite_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalizuje strukturę danych ulubionego pliku."""
    path_value = entry.get("path")
    if not path_value:
        return None

    path = str(Path(path_value))
    name = entry.get("name") or Path(path).name
    group = entry.get("group") or "Bez grupy"

    tags_raw = entry.get("tags")
    if isinstance(tags_raw, list):
        tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
    else:
        tags = []

    added_at = entry.get("added_at") if isinstance(entry.get("added_at"), str) else None
    if added_at:
        try:
            datetime.fromisoformat(added_at)
        except ValueError:
            added_at = None
    if not added_at:
        added_at = "1970-01-01T00:00:00"

    last_used_at = entry.get("last_used_at") if isinstance(entry.get("last_used_at"), str) else None
    if last_used_at:
        try:
            datetime.fromisoformat(last_used_at)
        except ValueError:
            last_used_at = None
    if not last_used_at:
        last_used_at = added_at

    return {
        "name": name,
        "path": path,
        "group": group,
        "tags": tags,
        "added_at": added_at,
        "last_used_at": last_used_at,
    }


def find_favorite_by_path(favorites: List[Dict[str, Any]], target_path: str) -> Optional[Dict[str, Any]]:
    """Znajduje ulubiony plik po ścieżce."""
    normalized_target = str(Path(target_path))
    for fav in favorites:
        if fav.get("path") == normalized_target:
            return fav
    return None


def record_favorite_usage(favorites: List[Dict[str, Any]], used_path: str) -> None:
    """Aktualizuje timestamp ostatniego użycia ulubionego pliku."""
    fav = find_favorite_by_path(favorites, used_path)
    if fav:
        fav["last_used_at"] = datetime.now().isoformat()
        save_favorites_to_disk(favorites)


def save_favorites_to_disk(favorites: List[Dict[str, Any]]) -> None:
    """Zapisuje ulubione pliki na dysk."""
    favorites_file = Path("mail_client/favorite_files.json")
    try:
        favorites_file.parent.mkdir(parents=True, exist_ok=True)
        with open(favorites_file, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Błąd zapisu ulubionych: {e}")
