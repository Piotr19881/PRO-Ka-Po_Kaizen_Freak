#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test dynamicznego importu TaskContextMenu
"""
import importlib.util
from pathlib import Path

print("=== Test importu TaskContextMenu ===\n")

try:
    # Ścieżka do pliku
    module_path = Path("PRO-Ka-Po_Kaizen_Freak/src/Modules/task_module/task_context_menu.py")
    
    print(f"Ścieżka modułu: {module_path}")
    print(f"Plik istnieje: {module_path.exists()}\n")
    
    if module_path.exists():
        # Załaduj moduł
        spec = importlib.util.spec_from_file_location("task_context_menu", module_path)
        
        if spec and spec.loader:
            task_context_menu = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(task_context_menu)
            
            # Sprawdź klasę
            if hasattr(task_context_menu, 'TaskContextMenu'):
                print("✅ TaskContextMenu załadowany pomyślnie!")
                print(f"   Klasa: {task_context_menu.TaskContextMenu}")
                
                # Sprawdź metody
                methods = [m for m in dir(task_context_menu.TaskContextMenu) if not m.startswith('_')]
                print(f"   Publiczne metody: {methods}")
            else:
                print("❌ Klasa TaskContextMenu nie została znaleziona w module")
        else:
            print("❌ Nie udało się utworzyć specyfikacji modułu")
    else:
        print("❌ Plik modułu nie istnieje!")
        
except Exception as e:
    print(f"❌ Błąd podczas importu: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test zakończony ===")
