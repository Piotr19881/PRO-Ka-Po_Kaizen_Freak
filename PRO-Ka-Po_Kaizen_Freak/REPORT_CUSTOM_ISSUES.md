# Raport: Krytyczne problemy i rekomendacje

Data: 2025-11-22

Krótki opis: Zidentyfikowano krytyczne i wysokiego priorytetu problemy w aplikacji. Poniżej zwięzłe podsumowanie problemów, ryzyk i rekomendowane działania (po polsku).

## 1) Synchronizacja modułu zadań (tasks)
- Symptom: `custom_list` (kolumny typu lista) nie synchronizują się poprawnie między urządzeniami; Kanban działa poprawnie.
- Ryzyko: rozbieżność konfiguracji UI między urządzeniami, utrata wygenerowanych list.
- Rekomendacja:
  - Dodać pełny przepływ end-to-end: zapisywać metadane serwera (`server_uuid`, `version`), uwzględniać `custom_lists` w bulk-sync, zapewnić initial_sync (fetch + upsert), oraz fallback per-item endpointy.
  - Dodać robust mapping odpowiedzi serwera -> lokalne ID (bulk response mapping).

## 2) Wyłączanie się podczas synchronizacji
- Symptom: aplikacja crashuje lub zamyka się przy sync (może być modyfikacja GUI z wątku roboczego lub wyjątki w workerach).
- Rekomendacja:
  - Nie modyfikować obiektów GUI z wątków innych niż główny (QApplication). Użyć Signals & Slots (emitowane przez worker -> obsługa w MainWindow).
  - Zadbaj o solidne logowanie błędów i niełapanie wyjątków `except: pass` w krytycznych miejscach.

## 3) Braki w tłumaczeniach
- Symptom: Niepełne i brakujące klucze językowe w `resources/i18n`.
- Rekomendacja: Uruchomić skrypt weryfikacyjny który porówna klucze w każdym pliku i zgłosi braki; wygenerować TODO listę tłumaczeń.

## 4) Integracja dźwięków z Pomodoro (koniec przerwy)
- Symptom: brak integracji dźwiękowej lub niewłaściwe wywołania w module pomodoro.
- Rekomendacja: Dodać center audio manager (jedno API), reużyć pliki z `resources/sounds`, oraz testy manualne dla platformy Windows (uwaga na rozszerzenia .m4r).

## 5) Wyłączanie się przy zapisie pobranych maili do transkrypcji
- Symptom: Crash przy zapisie/konwersji mail->transkrypcja.
- Rekomendacja: Sprawdź kod zapisujący pliki i wyjątki I/O; upewnij się, że operacje długotrwałe są w wątku roboczym i nie modyfikują GUI bez sygnałów.

## 6) `main.py` – Problemy z wątkami i GUI (krytyczne)
- Problem: Modyfikacja GUI z innego wątku (np. `save_tokens` iteruje `QApplication.topLevelWidgets()` i aktualizuje widoki z callbacków w tle).
- Rekomendacja:
  - Wprowadzić `SignalManager` lub dodać sygnały Qt w workerach. MainWindow powinien subskrybować sygnały i wykonać aktualizacje GUI w głównym wątku.
  - Usunąć tight-coupling (np. `alarms_view.alarms_logic.ws_client`) – wprowadzić interfejsy/registry.

## 7) `password_crypto.py` – bezpieczeństwo i przenośność (krytyczne)
- Problem: Klucz generowany z `platform.node()` + `platform.machine()` (nieprzenośne i niebezpieczne).
- Rekomendacja:
  - Użyć `keyring` (systemowy manager haseł) do przechowywania klucza.
  - Fallback: losowy klucz zapisany do pliku `mail_client/.key` (bez powiązania ze sprzętem).
  - Dodać skrypt migracyjny dla istniejących użytkowników: odszyfruj starymi danymi i zaszyfruj ponownie nowym kluczem.

## 8) `TeamWork/db_manager.py` – SQLite i wielowątkowość
- Problem: Współdzielenie jednego połączenia `sqlite3.Connection` między wątkami.
- Rekomendacja:
  - Każdy wątek powinien mieć własne połączenie (np. `threading.local()`), lub stosować pool połączeń; użyć `check_same_thread=False` tylko świadomie i z lockami.
  - Naprawić logikę `connect()` aby ponownie otwierać połączenie, gdy jest zamknięte.

## 9) `src/utils/audio_recorder.py` – Zarządzanie pamięcią
- Problem: Trzymanie całych nagrań w pamięci (`self.recorded_frames.append(block)`).
- Rekomendacja:
  - Streamuj zapisy do pliku tymczasowego (rotacja chunków) zamiast gromadzić w pamięci.
  - Zadbaj o atomowe flagi `is_recording` i synchronizację (Event/Lock).

## 10) `tasks_sync_manager.py` – sieć i DB
- Problem: Sprawdzanie połączenia przez `socket.create_connection(('8.8.8.8', 53), timeout=3)` jest zawodny w środowiskach gdzie blokowany jest port 53.
- Rekomendacja:
  - Wykonywać lekki żądanie HTTP (HEAD) do własnego API lub znanego HTTPS.
  - Otwierać jedno połączenie do sqlite w workerze i używać go podczas całego cyklu pracy, zamiast budować/zarzynać połączenie przy każdym zapytaniu.

## Krótkie kroki natychmiastowe (priorytetowe)
1. Naprawić `password_crypto.py` (zrobione w tej gałęzi) + dodać skrypt migracyjny.
2. Zrefaktoryzować krytyczne miejsca modyfikujące GUI z wątków (MainWindow + save_tokens).
3. Zmienić sprawdzanie sieci w `tasks_sync_manager.py` i zredukować liczbę otwarć pliku DB w pętli syncu.
4. Dodać testowy harness do synchronizacji custom_lists (mock API), by zweryfikować mapping i bulk-sync.

---
Powiadom mnie jeśli chcesz, żebym utworzył: migracyjny skrypt odszyfrowania/re-encrypt, klasę `SignalManager`, lub przykładowy test harness do syncu. Mogę też spróbować wypchnąć zmiany na `origin` (git push) — spróbuję automatycznie poniżej.
