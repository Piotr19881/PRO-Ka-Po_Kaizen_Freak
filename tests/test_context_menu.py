#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test menu kontekstowego - sprawdzenie czy wszystkie komponenty są na miejscu
"""
import sys
from pathlib import Path

# Dodaj główny katalog do PYTHONPATH
project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
sys.path.insert(0, str(project_root))

print("=== Test importów menu kontekstowego ===\n")

try:
    from src.Modules.task_module.task_context_menu import TaskContextMenu
    print("✅ TaskContextMenu zaimportowany poprawnie")
except Exception as e:
    print(f"❌ Błąd importu TaskContextMenu: {e}")

try:
    from src.ui.ui_task_simple_dialogs import TaskEditDialog
    print("✅ TaskEditDialog zaimportowany poprawnie")
except Exception as e:
    print(f"❌ Błąd importu TaskEditDialog: {e}")

try:
    from src.Modules.AI_module.ai_logic import get_ai_manager
    print("✅ AI Module zaimportowany poprawnie")
except Exception as e:
    print(f"❌ Błąd importu AI Module: {e}")

try:
    from src.utils.i18n_manager import t
    # Test kluczy tłumaczeń
    keys_to_test = [
        "tasks.context_menu.ai_plan",
        "tasks.context_menu.colorize",
        "tasks.context_menu.edit",
        "tasks.context_menu.mark_done",
        "tasks.context_menu.archive",
        "tasks.context_menu.delete",
        "tasks.context_menu.note",
        "tasks.context_menu.kanban",
        "tasks.context_menu.copy",
        "tasks.edit_dialog.title",
        "tasks.edit_dialog.label"
    ]
    
    print("\n=== Test kluczy i18n ===")
    for key in keys_to_test:
        value = t(key, f"MISSING: {key}")
        if "MISSING" not in value:
            print(f"✅ {key}: {value}")
        else:
            print(f"❌ Brakujący klucz: {key}")
            
except Exception as e:
    print(f"❌ Błąd testowania i18n: {e}")

print("\n=== Test bazy danych ===")
import sqlite3

try:
    conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
    cursor = conn.cursor()
    
    # Sprawdź czy kolumna row_color istnieje
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'row_color' in columns:
        print("✅ Kolumna 'row_color' istnieje w tabeli tasks")
    else:
        print("❌ Kolumna 'row_color' NIE istnieje w tabeli tasks")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Błąd sprawdzania bazy danych: {e}")

print("\n=== Test zakończony ===")
