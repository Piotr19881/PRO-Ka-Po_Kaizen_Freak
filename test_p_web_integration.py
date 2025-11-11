"""
Test integracji modułu P-Web V2

Sprawdza:
- Import wszystkich modułów
- Tworzenie logiki
- Kompatybilność wsteczną
- Operacje na grupach, tagach, zakładkach
"""

import sys
from pathlib import Path

# Dodaj ścieżki
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir / "src"))

def test_imports():
    """Test importów"""
    print("\n=== TEST IMPORTÓW ===")
    
    try:
        from src.Modules.p_web.p_web_logic import PWebLogic
        print("✅ Import PWebLogic")
    except Exception as e:
        print(f"❌ Import PWebLogic: {e}")
        return False
    
    try:
        from src.Modules.p_web.p_web_tree_widget import PWebTreeWidget
        print("✅ Import PWebTreeWidget")
    except Exception as e:
        print(f"❌ Import PWebTreeWidget: {e}")
        return False
    
    try:
        from src.Modules.p_web.p_web_context_menu import PWebContextMenu, CustomWebEnginePage
        print("✅ Import PWebContextMenu")
    except Exception as e:
        print(f"❌ Import PWebContextMenu: {e}")
        # To może nie działać bez PyQt6-WebEngine, ale to OK
        print("   (może brakować PyQt6-WebEngine - to normalne)")
    
    try:
        from src.ui.simple_pweb_dialogs import (
            GroupManagerDialog, TagManagerDialog, QuickOpenDialog, AddBookmarkDialog
        )
        print("✅ Import simple_pweb_dialogs")
    except Exception as e:
        print(f"❌ Import simple_pweb_dialogs: {e}")
        return False
    
    return True


def test_logic():
    """Test logiki biznesowej"""
    print("\n=== TEST LOGIKI BIZNESOWEJ ===")
    
    from src.Modules.p_web.p_web_logic import PWebLogic
    import tempfile
    import os
    
    # Użyj tymczasowego pliku
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.close()
    
    try:
        logic = PWebLogic(temp_file.name)
        print("✅ Utworzono instancję PWebLogic")
        
        # Test grupy domyślnej
        groups = logic.get_groups()
        if len(groups) == 1 and groups[0]['name'] == 'Wszystkie':
            print("✅ Grupa domyślna istnieje")
        else:
            print("❌ Brak grupy domyślnej")
            return False
        
        # Test dodawania grupy
        success, group_id = logic.add_group("Testowa", "#FF0000")
        if success:
            print(f"✅ Dodano grupę: {group_id}")
        else:
            print("❌ Błąd dodawania grupy")
            return False
        
        # Test dodawania tagu
        success, msg = logic.add_tag("test-tag")
        if success:
            print("✅ Dodano tag: test-tag")
        else:
            print(f"❌ Błąd dodawania tagu: {msg}")
            return False
        
        # Test dodawania zakładki
        success, error = logic.add_bookmark(
            "Test Bookmark",
            "https://example.com",
            "#00FF00",
            group_id,
            ["test-tag"],
            True  # favorite
        )
        if success:
            print("✅ Dodano zakładkę z grupą, tagiem i favorite=True")
        else:
            print(f"❌ Błąd dodawania zakładki: {error}")
            return False
        
        # Test filtrowania - wszystkie
        all_bookmarks = logic.get_bookmarks()
        print(f"✅ Wszystkie zakładki: {len(all_bookmarks)}")
        
        # Test filtrowania - tylko ulubione
        favorites = logic.get_bookmarks(favorites_only=True)
        if len(favorites) == 1:
            print("✅ Filtr ulubionych działa")
        else:
            print("❌ Filtr ulubionych nie działa")
            return False
        
        # Test filtrowania - po tagu
        tagged = logic.get_bookmarks(tag="test-tag")
        if len(tagged) == 1:
            print("✅ Filtr tagów działa")
        else:
            print("❌ Filtr tagów nie działa")
            return False
        
        # Test filtrowania - fraza
        phrase_results = logic.get_bookmarks(phrase="example")
        if len(phrase_results) == 1:
            print("✅ Filtr frazy działa")
        else:
            print("❌ Filtr frazy nie działa")
            return False
        
        # Test toggle favorite
        bookmark = all_bookmarks[0]
        success, result = logic.toggle_favorite(bookmark)
        if success and result == 'False':
            print("✅ Toggle favorite działa (True → False)")
        else:
            print("❌ Toggle favorite nie działa")
            return False
        
        print("\n✅ Wszystkie testy logiki przeszły pomyślnie!")
        return True
        
    except Exception as e:
        print(f"❌ Błąd w testach logiki: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Usuń plik tymczasowy
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_backward_compatibility():
    """Test kompatybilności wstecznej"""
    print("\n=== TEST BACKWARD COMPATIBILITY ===")
    
    from src.Modules.p_web.p_web_logic import PWebLogic
    import tempfile
    import json
    import os
    
    # Stwórz plik w starym formacie
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    old_format = [
        {"name": "Google", "url": "https://google.com", "color": "#4285F4"},
        {"name": "GitHub", "url": "https://github.com", "color": "#333"}
    ]
    json.dump(old_format, temp_file)
    temp_file.close()
    
    try:
        logic = PWebLogic(temp_file.name)
        print("✅ Załadowano plik w starym formacie")
        
        # Sprawdź czy zakładki zostały zmigrowane
        bookmarks = logic.get_bookmarks()
        if len(bookmarks) == 2:
            print("✅ Zakładki zmigrowane (2 zakładki)")
        else:
            print(f"❌ Błąd migracji: {len(bookmarks)} zakładek zamiast 2")
            return False
        
        # Sprawdź czy mają grupę domyślną
        if all(b.get('group_id') == 'default' for b in bookmarks):
            print("✅ Wszystkie zakładki w grupie 'default'")
        else:
            print("❌ Zakładki nie mają grupy 'default'")
            return False
        
        # Sprawdź pola
        first = bookmarks[0]
        if 'tags' in first and 'favorite' in first:
            print("✅ Zakładki mają nowe pola (tags, favorite)")
        else:
            print("❌ Brak nowych pól w zakładkach")
            return False
        
        print("\n✅ Test kompatybilności wstecznej przeszedł!")
        return True
        
    except Exception as e:
        print(f"❌ Błąd w teście backward compatibility: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass


def main():
    print("=" * 60)
    print("TEST INTEGRACJI P-WEB V2")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Importy
    if not test_imports():
        all_passed = False
    
    # Test 2: Logika
    if not test_logic():
        all_passed = False
    
    # Test 3: Backward compatibility
    if not test_backward_compatibility():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ WSZYSTKIE TESTY PRZESZŁY POMYŚLNIE!")
    else:
        print("❌ NIEKTÓRE TESTY NIE PRZESZŁY")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
