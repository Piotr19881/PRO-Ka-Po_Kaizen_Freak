# CallCryptor Sync - Checklist Testów Manualnych

**Data utworzenia:** 2025-01-XX  
**Wersja:** 1.0  
**Status:** Gotowy do testów  

---

## 📋 Spis treści
1. [Środowisko testowe](#środowisko-testowe)
2. [Testy UI](#testy-ui)
3. [Testy integracyjne](#testy-integracyjne)
4. [Testy błędów](#testy-błędów)
5. [Testy prywatności](#testy-prywatności)
6. [Checklist końcowy](#checklist-końcowy)

---

## 🔧 Środowisko testowe

### Opcja A: Backend lokalny (FastAPI)
```bash
# Wymagania:
# - PostgreSQL 14+ zainstalowany i działający
# - Python 3.11+ z requirements.txt z Render_upload/

# 1. Uruchom migrację schematu
cd Render_upload/database
psql -U postgres -d kaizen_freak_dev < s07_callcryptor_schema.sql

# 2. Uruchom FastAPI backend
cd Render_upload
uvicorn app.main:app --reload --port 8000

# 3. Sprawdź dostępność
curl http://localhost:8000/docs
# Powinno pokazać Swagger UI

# 4. W user_settings.json ustaw:
# "api_base_url": "http://localhost:8000"
```

### Opcja B: Backend produkcyjny (Render.com)
```json
// W user_settings.json:
{
  "api_base_url": "https://twoja-aplikacja.onrender.com"
}
```

### Opcja C: Mock API (dla offline testing)
```python
# TODO: Przygotować mock server dla testów offline
# Użyj pytest-httpserver lub responses library
```

### ✅ Pre-flight checklist
- [ ] PostgreSQL działa i ma zaaplikowany schema s07_callcryptor
- [ ] FastAPI backend odpowiada na http://localhost:8000/docs (lub Render URL)
- [ ] Masz aktywne konto użytkownika (zalogowany)
- [ ] Token dostępowy jest ważny (sprawdź `data/tokens.json`)
- [ ] CallCryptor module ma przynajmniej 5 przykładowych nagrań w bazie SQLite

---

## 🎨 Testy UI

### TEST 1: Przycisk Sync - Stan początkowy
**Warunki początkowe:** Sync NIGDY nie był włączany  
**Kroki:**
1. Otwórz moduł CallCryptor
2. Zlokalizuj przycisk 📨 w toolbarze

**Oczekiwany rezultat:**
- ✅ Przycisk widoczny
- ✅ Kolor: 🟠 **pomarańczowy** (disabled state)
- ✅ Tooltip: "Synchronizacja wyłączona - kliknij aby włączyć"
- ✅ Przycisk jest klikalny

---

### TEST 2: SyncConsentDialog - Pierwsze uruchomienie
**Warunki początkowe:** Sync NIGDY nie był włączany  
**Kroki:**
1. Kliknij przycisk 📨 sync
2. Powinien pojawić się `SyncConsentDialog`

**Oczekiwany rezultat:**
- ✅ Dialog się otwiera
- ✅ Nagłówek: "📨 Włącz synchronizację metadanych nagrań"
- ✅ Sekcja "⚠️ WAŻNE: Informacja o prywatności" widoczna
- ✅ Tekst ostrzeżenia: "Synchronizacja jest CAŁKOWICIE OPCJONALNA..."
- ✅ Sekcja "✅ Co BĘDZIE synchronizowane" zawiera 4 pozycje:
  - Metadane nagrań (data, czas, kontakt, długość)
  - Transkrypcje i podsumowania AI
  - Tagi i notatki
  - Powiązania z zadaniami/notatkami
- ✅ Sekcja "❌ Co NIE będzie synchronizowane" zawiera 2 pozycje (kolor czerwony):
  - Pliki audio (pozostają TYLKO lokalnie)
  - Hasła do zaszyfrowanych nagrań
- ✅ Checkbox: "Włącz automatyczną synchronizację co 5 minut"
- ✅ Checkbox: "Nie pokazuj więcej tego okna"
- ✅ 3 przyciski:
  - "Anuluj" (szary)
  - "Synchronizuj raz" (🟠 pomarańczowy)
  - "Włącz synchronizację" (🟢 zielony)

**Testy interakcji:**
- ✅ Kliknięcie "Anuluj" zamyka dialog bez zmian
- ✅ Przycisk sync pozostaje 🟠 pomarańczowy

---

### TEST 3: Sync Once - Jednorazowa synchronizacja
**Warunki początkowe:** `SyncConsentDialog` otwarty  
**Kroki:**
1. W `SyncConsentDialog` kliknij "Synchronizuj raz"

**Oczekiwany rezultat:**
- ✅ Dialog zamyka się
- ✅ Rozpoczyna się synchronizacja (sprawdź logi)
- ✅ Przycisk sync zmienia kolor na 🟢 **zielony** (tymczasowo)
- ✅ Po synchronizacji przycisk wraca do 🟠 **pomarańczowego** (sync disabled)
- ✅ Tooltip: "Synchronizacja wyłączona - kliknij aby włączyć"

**Sprawdź w logach:**
```
[CallCryptor Sync] Starting manual sync...
[CallCryptor Sync] Uploading X recordings...
[CallCryptor Sync] Sync completed successfully
```

---

### TEST 4: Enable Sync - Włączenie synchronizacji
**Warunki początkowe:** `SyncConsentDialog` otwarty  
**Kroki:**
1. Zaznacz checkbox "Włącz automatyczną synchronizację co 5 minut"
2. Zaznacz checkbox "Nie pokazuj więcej tego okna"
3. Kliknij "Włącz synchronizację"

**Oczekiwany rezultat:**
- ✅ Dialog zamyka się
- ✅ Rozpoczyna się synchronizacja
- ✅ Przycisk sync **NA STAŁE** zmienia kolor na 🟢 **zielony**
- ✅ Tooltip: "Synchronizacja włączona - kliknij aby zarządzać"
- ✅ Auto-sync worker uruchamia się w tle (sprawdź logi co 5 minut)

**Sprawdź w user_settings.json:**
```json
{
  "callcryptor_sync": {
    "enabled": true,
    "auto_sync_enabled": true,
    "dont_show_consent": true,
    "last_sync_at": "2025-01-XX 12:34:56"
  }
}
```

---

### TEST 5: SyncStatusDialog - Zarządzanie sync
**Warunki początkowe:** Sync jest już włączony (przycisk 🟢 zielony)  
**Kroki:**
1. Kliknij przycisk 📨 sync (już 🟢 zielony)
2. Powinien pojawić się `SyncStatusDialog`

**Oczekiwany rezultat:**
- ✅ Dialog się otwiera (BEZ `SyncConsentDialog` jeśli zaznaczono "Nie pokazuj więcej")
- ✅ Nagłówek: "📨 Status synchronizacji"
- ✅ Sekcja "Status":
  - Stan: "✅ Włączona" (kolor zielony)
  - Ostatnia synchronizacja: "[data i godzina]" (lub "Nigdy")
- ✅ Sekcja "Statystyki":
  - Wszystkie nagrania: [liczba]
  - Zsynchronizowane: [liczba]
  - Oczekuje na synchronizację: [liczba]
- ✅ Checkbox: "Automatyczna synchronizacja co 5 minut" (zaznaczony jeśli włączony)
- ✅ Checkbox: "Wyłącz synchronizację" (tooltip: "Zatrzyma automatyczną synchronizację...")
- ✅ 2 przyciski:
  - "Zamknij" (szary)
  - "Synchronizuj teraz" (🟢 zielony)

---

### TEST 6: Manual Sync z SyncStatusDialog
**Warunki początkowe:** `SyncStatusDialog` otwarty, sync włączony  
**Kroki:**
1. Kliknij "Synchronizuj teraz"

**Oczekiwany rezultat:**
- ✅ Dialog zamyka się
- ✅ Rozpoczyna się synchronizacja (sprawdź logi)
- ✅ Przycisk sync pozostaje 🟢 zielony
- ✅ Statystyki w `SyncStatusDialog` aktualizują się po ponownym otwarciu

---

### TEST 7: Wyłączenie sync z SyncStatusDialog
**Warunki początkowe:** `SyncStatusDialog` otwarty, sync włączony  
**Kroki:**
1. Zaznacz checkbox "Wyłącz synchronizację"
2. Kliknij "Synchronizuj teraz" (lub "Zamknij")

**Oczekiwany rezultat:**
- ✅ Dialog zamyka się
- ✅ Przycisk sync zmienia kolor na 🟠 **pomarańczowy**
- ✅ Tooltip: "Synchronizacja wyłączona - kliknij aby włączyć"
- ✅ Auto-sync worker zatrzymuje się (sprawdź logi - brak wpisów co 5 min)

**Sprawdź w user_settings.json:**
```json
{
  "callcryptor_sync": {
    "enabled": false,
    "auto_sync_enabled": false
  }
}
```

---

### TEST 8: Auto-sync w tle
**Warunki początkowe:** Sync włączony z auto-sync (co 5 minut)  
**Kroki:**
1. Włącz sync z auto-sync
2. Pozostaw aplikację otwartą na 5+ minut
3. Obserwuj logi

**Oczekiwany rezultat:**
- ✅ Co ~5 minut w logach pojawia się:
  ```
  [CallCryptor Sync] Auto-sync triggered
  [CallCryptor Sync] Starting background sync...
  [CallCryptor Sync] Sync completed successfully
  ```
- ✅ Przycisk sync pozostaje 🟢 zielony przez cały czas
- ✅ UI NIE blokuje się podczas auto-sync (działa w osobnym wątku)

---

## 🔗 Testy integracyjne

### TEST 9: Synchronizacja nagrań - Upload do backend
**Warunki początkowe:** CallCryptor ma 5 nagrań w lokalnej bazie SQLite  
**Kroki:**
1. Włącz sync i kliknij "Synchronizuj raz"
2. Sprawdź logi
3. Sprawdź bazę PostgreSQL

**Oczekiwany rezultat:**
- ✅ Logi pokazują:
  ```
  [CallCryptor Sync] Uploading 5 recordings...
  [CallCryptor Sync] POST /api/recordings/bulk-sync (Status: 200)
  [CallCryptor Sync] Server created: 5, updated: 0
  ```
- ✅ W PostgreSQL (tabela `s07_callcryptor.recordings`):
  ```sql
  SELECT COUNT(*) FROM s07_callcryptor.recordings WHERE user_id = 'twoj_user_id';
  -- Powinno zwrócić: 5
  ```
- ✅ Kolumny wypełnione:
  - `uuid` (z lokalnej bazy)
  - `source_uuid`, `contact_name`, `call_date`, `duration_seconds`
  - `transcription`, `ai_summary` (jeśli były w lokalnej bazie)
  - `created_at`, `updated_at`
  - `version = 1`

---

### TEST 10: Synchronizacja tagów
**Warunki początkowe:** Masz nagrania z tagami w lokalnej bazie  
**Kroki:**
1. Dodaj tag "Klient A" do nagrania #1
2. Uruchom sync

**Oczekiwany rezultat:**
- ✅ W PostgreSQL (tabela `s07_callcryptor.recording_tags`):
  ```sql
  SELECT tag_name FROM s07_callcryptor.recording_tags 
  WHERE recording_uuid = '[uuid nagrania #1]';
  -- Powinno zwrócić: "Klient A"
  ```

---

### TEST 11: Konflikt - Last-Write-Wins
**Warunki początkowe:** To samo nagranie zmienione lokalnie i na serwerze  
**Kroki:**
1. Sync nagranie #1 (lokalnie: `updated_at = 2025-01-10 10:00`)
2. Zmień ręcznie w PostgreSQL: `updated_at = 2025-01-10 11:00`, `version = 2`
3. Lokalnie zmień nagranie #1 (dodaj tag)
4. Uruchom sync

**Oczekiwany rezultat:**
- ✅ Jeśli lokalna zmiana jest **nowsza** (`updated_at > server`):
  - Server aktualizuje nagranie (wersja serwera = 3)
- ✅ Jeśli lokalna zmiana jest **starsza** (`updated_at < server`):
  - Lokalna zmiana jest **ignorowana** (Last-Write-Wins)
  - Logi pokazują: `[CallCryptor Sync] Conflict detected for recording [uuid], server version kept`

---

## ❌ Testy błędów

### TEST 12: Backend niedostępny
**Warunki początkowe:** Backend wyłączony lub błędny URL  
**Kroki:**
1. Zatrzymaj backend FastAPI
2. Kliknij "Synchronizuj teraz"

**Oczekiwany rezultat:**
- ✅ Logi pokazują:
  ```
  [CallCryptor Sync] Network error: Connection refused
  [CallCryptor Sync] Retrying (1/3)...
  [CallCryptor Sync] Retrying (2/3)...
  [CallCryptor Sync] Retrying (3/3)...
  [CallCryptor Sync] Sync failed after 3 retries
  ```
- ✅ UI pokazuje komunikat błędu (QMessageBox):
  - Tytuł: "Błąd synchronizacji"
  - Treść: "Nie można połączyć się z serwerem. Sprawdź połączenie internetowe."
- ✅ Przycisk sync pozostaje 🟢 zielony (sync nadal włączony)
- ✅ **WAŻNE:** Aplikacja NIE crashuje, UI pozostaje responsywne

---

### TEST 13: Token wygasły (401 Unauthorized)
**Warunki początkowe:** Token w `data/tokens.json` wygasł  
**Kroki:**
1. Ręcznie zmień token na nieprawidłowy
2. Kliknij "Synchronizuj teraz"

**Oczekiwany rezultat:**
- ✅ Logi pokazują:
  ```
  [CallCryptor Sync] Token expired (401), refreshing...
  [CallCryptor Sync] Token refreshed successfully
  [CallCryptor Sync] Retrying sync with new token...
  [CallCryptor Sync] Sync completed successfully
  ```
- ✅ Plik `data/tokens.json` zawiera nowy token
- ✅ Synchronizacja kończy się powodzeniem (po refresh)

**Jeśli refresh też się nie powiedzie:**
- ✅ Logi pokazują:
  ```
  [CallCryptor Sync] Token refresh failed (401)
  [CallCryptor Sync] User needs to re-login
  ```
- ✅ UI pokazuje komunikat: "Sesja wygasła. Zaloguj się ponownie."
- ✅ Aplikacja przekierowuje do ekranu logowania

---

### TEST 14: Server Error (500)
**Warunki początkowe:** Backend zwraca błąd 500  
**Kroki:**
1. Symuluj błąd serwera (np. zatrzymaj PostgreSQL)
2. Kliknij "Synchronizuj teraz"

**Oczekiwany rezultat:**
- ✅ Logi pokazują:
  ```
  [CallCryptor Sync] Server error (500): Internal Server Error
  [CallCryptor Sync] Retrying (1/3)...
  [CallCryptor Sync] Sync failed after 3 retries
  ```
- ✅ UI pokazuje komunikat: "Błąd serwera. Spróbuj ponownie później."
- ✅ Aplikacja NIE crashuje

---

### TEST 15: Bulk sync limit (max 100 nagrań)
**Warunki początkowe:** Lokalnie masz 150 nagrań do synchronizacji  
**Kroki:**
1. Uruchom sync pierwszy raz (150 nowych nagrań)

**Oczekiwany rezultat:**
- ✅ Logi pokazują:
  ```
  [CallCryptor Sync] 150 recordings to sync, splitting into batches...
  [CallCryptor Sync] Batch 1/2: Uploading 100 recordings...
  [CallCryptor Sync] POST /api/recordings/bulk-sync (Status: 200)
  [CallCryptor Sync] Batch 2/2: Uploading 50 recordings...
  [CallCryptor Sync] POST /api/recordings/bulk-sync (Status: 200)
  [CallCryptor Sync] Total synced: 150
  ```
- ✅ Wszystkie 150 nagrań w PostgreSQL

---

## 🔒 Testy prywatności

### TEST 16: Pliki audio NIE są wysyłane
**Warunki początkowe:** Nagranie ma plik audio `file_path = "C:\Recordings\call.amr"`  
**Kroki:**
1. Uruchom sync
2. Sprawdź logi sieciowe (opcjonalnie: Wireshark, Fiddler)
3. Sprawdź PostgreSQL

**Oczekiwany rezultat:**
- ✅ W logach **BRAK** uploadu plików `.amr`, `.mp3` itp.
- ✅ W PostgreSQL kolumna `file_path` jest **NULL** lub **pusta**
- ✅ W requestach HTTP **BRAK** binarne dane audio (payload < 100 KB dla 100 nagrań)

---

### TEST 17: Hasła do zaszyfrowanych nagrań NIE są wysyłane
**Warunki początkowe:** Nagranie ma hasło w lokalnej bazie  
**Kroki:**
1. Sprawdź lokalną bazę SQLite:
   ```sql
   SELECT encryption_key FROM recordings WHERE uuid = 'xyz';
   -- Zwraca: "tajne_haslo"
   ```
2. Uruchom sync
3. Sprawdź PostgreSQL:
   ```sql
   SELECT encryption_key FROM s07_callcryptor.recordings WHERE uuid = 'xyz';
   ```

**Oczekiwany rezultat:**
- ✅ Kolumna `encryption_key` w PostgreSQL jest **NULL**
- ✅ **NIGDY** nie pojawia się w payloadzie HTTP

---

### TEST 18: User może wyłączyć sync w każdej chwili
**Warunki początkowe:** Sync włączony, auto-sync działa  
**Kroki:**
1. Kliknij przycisk sync (🟢)
2. W `SyncStatusDialog` zaznacz "Wyłącz synchronizację"
3. Kliknij "Zamknij"

**Oczekiwany rezultat:**
- ✅ Sync wyłączony (przycisk 🟠)
- ✅ **DANE NA SERWERZE POZOSTAJĄ** (sprawdź PostgreSQL - nagrania nadal tam są)
- ✅ Auto-sync zatrzymany
- ✅ User może ponownie włączyć sync w dowolnym momencie

---

## ✅ Checklist końcowy

### UI Tests
- [ ] TEST 1: Przycisk sync - stan początkowy (🟠 pomarańczowy)
- [ ] TEST 2: SyncConsentDialog wyświetla się poprawnie
- [ ] TEST 3: "Synchronizuj raz" działa bez włączania auto-sync
- [ ] TEST 4: "Włącz synchronizację" aktywuje sync (🟢 zielony)
- [ ] TEST 5: SyncStatusDialog pokazuje statystyki
- [ ] TEST 6: Manual sync z SyncStatusDialog
- [ ] TEST 7: Wyłączenie sync zmienia przycisk na 🟠
- [ ] TEST 8: Auto-sync działa w tle (co 5 min)

### Integration Tests
- [ ] TEST 9: Nagrania są uploadowane do PostgreSQL
- [ ] TEST 10: Tagi są synchronizowane
- [ ] TEST 11: Konflikt - Last-Write-Wins działa

### Error Tests
- [ ] TEST 12: Backend niedostępny - retry 3x, graceful failure
- [ ] TEST 13: Token wygasły - auto-refresh działa
- [ ] TEST 14: Server Error (500) - graceful failure
- [ ] TEST 15: Bulk sync limit (max 100) - batching działa

### Privacy Tests
- [ ] TEST 16: Pliki audio NIE są wysyłane
- [ ] TEST 17: Hasła NIE są wysyłane
- [ ] TEST 18: User może wyłączyć sync w każdej chwili

---

## 📝 Znane ograniczenia

1. **Brak synchronizacji plików audio** (by design - privacy-first)
2. **Last-Write-Wins** - starsze lokalne zmiany mogą być nadpisane przez nowsze z serwera
3. **Bulk sync max 100 nagrań** - duże kolekcje wymagają wielu requestów
4. **Brak offline queue** - zmiany podczas offline nie są automatycznie wysyłane po powrocie online (trzeba ręcznie kliknąć sync)

---

## 🐛 Raportowanie błędów

Jeśli jakikolwiek test **NIE PRZECHODZI**:

1. **Zrób screenshot** (UI error)
2. **Skopiuj logi** z konsoli (ostatnie 50 linii)
3. **Sprawdź user_settings.json** - jaki jest stan `callcryptor_sync`?
4. **Sprawdź network** - czy request dotarł do serwera? (check backend logs)
5. **Utwórz Issue** na GitHubie z:
   - Nazwa testu
   - Oczekiwany rezultat
   - Faktyczny rezultat
   - Logi + screenshot

---

## ✅ Po zakończeniu testów

Jeśli wszystkie testy **PRZECHODZĄ**:

```bash
# 1. Commit zmian (lokalnie - NIE PUSH)
git add .
git commit -m "feat(callcryptor): Add privacy-first opt-in sync for recordings metadata

- Backend: PostgreSQL schema s07_callcryptor (3 tables)
- Backend: FastAPI router with CRUD + bulk sync (max 100)
- Backend: Pydantic models (14 models) with validators
- Frontend: Sync button (orange/green states)
- Frontend: SyncConsentDialog (privacy warning on first enable)
- Frontend: SyncStatusDialog (stats + manual trigger)
- Frontend: RecordingsAPIClient (HTTP client with retry + token refresh)
- Frontend: RecordingsSyncManager (opt-in, auto-sync optional)
- Integration: Full sync infrastructure in CallCryptorView
- Privacy: NO audio files synced, only metadata
- Conflict resolution: Last-Write-Wins
- i18n: 33 Polish translation keys added

Tests: All 18 manual tests passed
Status: Ready for production (no push until explicitly requested)
"

# 2. Merge do main (lokalnie)
git checkout main
git merge feature/callcryptor-sync

# 3. NIE PUSH (zgodnie z wymaganiem użytkownika)
# git push origin main  <-- SKIP THIS

# 4. Powiadom użytkownika
echo "✅ Implementacja CallCryptor Sync zakończona!"
echo "✅ Wszystkie testy przeszły pomyślnie"
echo "✅ Kod zamergowany do main (lokalnie)"
echo "⚠️ NIE PUSH na GitHub (czekamy na Twoją zgodę)"
```

---

**Koniec checklisty testów**  
**Good luck with testing! 🚀**
