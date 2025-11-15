"""
Skrypt do parsowania i przemianowania plików dźwiękowych
Przekształca nazwy z formatu _pl_sound_opis_.m4r na czytelne polskie nazwy
"""

import os
import re
import shutil
from pathlib import Path

# Mapowanie specjalnych przypadków (ręczne nazwy)
MANUAL_NAMES = {
    "dzwiek-syrena-przeciwlotnicza.m4r": "Syrena przeciwlotnicza.m4r",
    "_pl_sound__.m4r": "Dźwięk systemowy 1.m4r",
    "_pl_sound__ (1).m4r": "Dźwięk systemowy 2.m4r",
    "_pl_sound__ (2).m4r": "Dźwięk systemowy 3.m4r",
    "_pl_sound__ (3).m4r": "Dźwięk systemowy 4.m4r",
    "_pl_sound__ (4).m4r": "Dźwięk systemowy 5.m4r",
    "_pl_sound__ (5).m4r": "Dźwięk systemowy 6.m4r",
    "_pl_sound__ (6).m4r": "Dźwięk systemowy 7.m4r",
    "_pl_sound__ (7).m4r": "Dźwięk systemowy 8.m4r",
    "_pl_sound__ (8).m4r": "Dźwięk systemowy 9.m4r",
    "_pl_sound__ (9).m4r": "Dźwięk systemowy 10.m4r",
    "_pl_sound__ (10).m4r": "Dźwięk systemowy 11.m4r",
    "_pl_sound__ (11).m4r": "Dźwięk systemowy 12.m4r",
    "_pl_sound__ (12).m4r": "Dźwięk systemowy 13.m4r",
    "_pl_sound__ (13).m4r": "Dźwięk systemowy 14.m4r",
    "_pl_sound__ (14).m4r": "Dźwięk systemowy 15.m4r",
    "_pl_sound__ (15).m4r": "Dźwięk systemowy 16.m4r",
    "_pl_sound__ (16).m4r": "Dźwięk systemowy 17.m4r",
    "_pl_sound__ (17).m4r": "Dźwięk systemowy 18.m4r",
    "_pl_sound__ (18).m4r": "Dźwięk systemowy 19.m4r",
    "_pl_sound__ (19).m4r": "Dźwięk systemowy 20.m4r",
    "_pl_sound__ (20).m4r": "Dźwięk systemowy 21.m4r",
    "_pl_sound__ (21).m4r": "Dźwięk systemowy 22.m4r",
}


def parse_sound_name(filename: str) -> str:
    """
    Parsuje nazwę pliku dźwiękowego i zwraca czytelną polską nazwę
    
    Args:
        filename: Oryginalna nazwa pliku
        
    Returns:
        Przetworzona nazwa pliku
    """
    # Sprawdź czy jest w mapowaniu ręcznym
    if filename in MANUAL_NAMES:
        return MANUAL_NAMES[filename]
    
    # Usuń prefix _pl_sound_
    name = filename.replace("_pl_sound_", "")
    
    # Usuń numer na początku (np. "06dzwiek-")
    name = re.sub(r'^\d+', '', name)
    
    # Usuń końcowy podkreślnik i duplikaty
    name = name.replace("_", " ").strip()
    name = name.replace("  ", " ")
    
    # Zastąp myślniki spacjami
    name = name.replace("-", " ")
    
    # Usuń duplikaty słów (np. "dzwiek dzwiek" -> "dzwiek")
    words = name.split()
    unique_words = []
    for word in words:
        if word.lower() not in [w.lower() for w in unique_words]:
            unique_words.append(word)
    name = " ".join(unique_words)
    
    # Kapitalizuj pierwsze litery
    name = name.title()
    
    # Usuń końcowy .m4r tymczasowo dla dalszego przetwarzania
    name = name.replace(".M4R", "").replace(".m4r", "")
    
    # Skróć zbyt długie nazwy
    if len(name) > 50:
        name = name[:47] + "..."
    
    # Dodaj rozszerzenie .m4r z powrotem
    name = name + ".m4r"
    
    return name


def rename_sounds(source_dir: str, dry_run: bool = True):
    """
    Przemianowuje pliki dźwiękowe w katalogu
    
    Args:
        source_dir: Ścieżka do katalogu z dźwiękami
        dry_run: Jeśli True, tylko wyświetla zmiany bez wykonywania
    """
    sounds_path = Path(source_dir)
    
    if not sounds_path.exists():
        print(f"❌ Katalog nie istnieje: {source_dir}")
        return
    
    print(f"📂 Przetwarzanie plików w: {source_dir}")
    print(f"   Tryb: {'PODGLĄD' if dry_run else 'WYKONANIE'}\n")
    
    renamed_count = 0
    skipped_count = 0
    
    for file_path in sorted(sounds_path.glob("*.m4r")):
        old_name = file_path.name
        new_name = parse_sound_name(old_name)
        
        if old_name == new_name:
            print(f"⏭️  Pomiń: {old_name}")
            skipped_count += 1
            continue
        
        new_path = file_path.parent / new_name
        
        print(f"📝 {old_name}")
        print(f"   ➡️  {new_name}")
        
        if not dry_run:
            try:
                file_path.rename(new_path)
                print(f"   ✅ Przemianowano")
                renamed_count += 1
            except Exception as e:
                print(f"   ❌ Błąd: {e}")
        else:
            renamed_count += 1
        
        print()
    
    print(f"\n{'='*60}")
    print(f"📊 Podsumowanie:")
    print(f"   ✅ Do przemianowania: {renamed_count}")
    print(f"   ⏭️  Pominiętych: {skipped_count}")
    print(f"   📁 Razem plików: {renamed_count + skipped_count}")
    
    if dry_run:
        print(f"\n⚠️  To był PODGLĄD. Uruchom ponownie z dry_run=False aby wykonać zmiany.")


if __name__ == "__main__":
    import sys
    
    # Ścieżka do katalogu sounds
    script_dir = Path(__file__).parent
    sounds_dir = script_dir.parent / "resources" / "sounds"
    
    # Sprawdź argument wiersza poleceń
    do_rename = "--rename" in sys.argv
    
    print("🔊 Renaming dźwięków PRO-Ka-Po")
    print("="*60)
    
    rename_sounds(str(sounds_dir), dry_run=not do_rename)
    
    if not do_rename:
        print("\n💡 Aby wykonać zmiany, uruchom: python scripts/rename_sounds.py --rename")
