# System Cache dla Maili i Kontaktów

## Implementacja

System cache został zaimplementowany w 3 plikach:

1. **mail_cache.py** - Podstawowy system cache (SQLite + pamięć)
2. **cache_integration.py** - Integracja z mail_view
3. **mail_view.py** - Zmodyfikowany o obsługę cache

## Funkcjonalność

### Automatyczne działanie

System cache działa automatycznie:
- **Przy starcie aplikacji**: Ładuje maile i kontakty z cache w tle
- **Podczas pracy**: Zapisuje zmiany do cache (gwiazdki, kolory, tagi)
- **Co 5 minut**: Synchronizuje dane w tle
- **Przy zamykaniu**: Zapisuje wszystkie dane i czyści stary cache (>30 dni)

### Wydajność

- **Pierwsze uruchomienie**: Normalna prędkość (tworzy cache)
- **Kolejne uruchomienia**: 10-50x szybsze ładowanie
- **Cache w pamięci**: Dostęp w ~0.01 sekundy
- **Cache na dysku (SQLite)**: Dostęp w ~0.5 sekundy

## Struktura Danych

### Baza danych (mail_cache.db)

**Tabela mails:**
- uid (unikalne ID)
- folder (nazwa folderu)
- from, to, subject, date, body
- starred, read (flagi)
- size, attachments
- json_data (pełny obiekt maila)

**Tabela contacts:**
- email (unikalne)
- name, tags, color
- last_contact, mail_count

**Tabela sync_metadata:**
- key, value (metadane synchronizacji)

## Test

Uruchom test:
```bash
python mail_client/test_cache.py
```

Powinien pokazać:
- ✓ Zapisywanie maili
- ✓ Ładowanie z cache
- ✓ Aktualizacja danych
- ✓ Kontakty z tagami i kolorami
- ✓ Statystyki cache

## Zarządzanie Cache

### Automatyczne czyszczenie
- Usuwa maile starsze niż 30 dni (bez gwiazdki)
- Wykonuje się przy zamykaniu aplikacji

### Manualne operacje
```python
# Statystyki
stats = cache.get_cache_stats()
print(f"Maili: {stats['mails']}")

# Czyszczenie
cache.clear_old_cache(days=30)
```

## Synchronizacja w tle

System uruchamia wątek w tle który:
1. Co 5 minut zapisuje aktualny stan
2. Nie blokuje interfejsu użytkownika
3. Automatycznie zatrzymuje się przy zamknięciu

## Rozwiązywanie problemów

**Cache nie ładuje się:**
- Sprawdź czy plik `mail_cache.db` istnieje
- Uruchom test: `python mail_client/test_cache.py`

**Wolne działanie:**
- Sprawdź rozmiar cache: może być zbyt duży
- Wyczyść stary cache: `cache.clear_old_cache(days=7)`

**Błędy synchronizacji:**
- Sprawdź logi w konsoli (szukaj "[Cache]")
- Sprawdź czy SQLite działa: `import sqlite3`

## Pliki Cache

- `mail_client/mail_cache.db` - Baza danych SQLite
- Lokalizacja można zmienić w `MailCache(db_path="...")`

## Integracja z aplikacją

Wszystko odbywa się automatycznie:
1. Przy starcie: `cache_integration.load_from_cache_at_startup()`
2. Podczas pracy: Automatyczne aktualizacje
3. Przy zamykaniu: `cache_integration.shutdown()`

Nie wymaga dodatkowej konfiguracji!
