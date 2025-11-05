# Moduł WebBrowser

Prosty moduł przeglądarki stron internetowych z możliwością zapisywania ulubionych stron z kolorowym oznaczeniem.

## Funkcje

### Pasek Operacyjny
- **Lista zapisanych stron** - rozwijana lista wszystkich dodanych stron z kolorowym oznaczeniem
- **Przycisk "Dodaj stronę"** - otwiera dialog do wprowadzenia:
  - Nazwy strony (wyświetlanej na liście)
  - Adresu URL strony
  - Koloru podświetlenia na liście
- **Przycisk "Usuń stronę"** - otwiera listę stron z możliwością usunięcia wybranej
- **Przycisk "Odśwież"** - przeładowuje aktualną stronę
- **Przycisk "Wstecz"** - powrót do poprzedniej strony w historii

### Główna Sekcja
- Wyświetlanie strony internetowej w wbudowanej przeglądarce (QtWebEngine)
- Pełna funkcjonalność przeglądania (klikanie linków, formularze, JavaScript)

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python web_browser_module.py
```

## Struktura Danych

Dane zapisywane są w pliku `web_pages.json`:

```json
[
  {
    "name": "Google",
    "url": "https://www.google.com",
    "color": "#4285f4"
  },
  {
    "name": "YouTube",
    "url": "https://www.youtube.com",
    "color": "#ff0000"
  }
]
```

## Wymagania Systemowe

- Python 3.8+
- PyQt6 6.4.0+
- PyQt6-WebEngine 6.4.0+

## Użytkowanie

1. **Dodawanie strony:**
   - Kliknij "Dodaj stronę"
   - Wprowadź nazwę (np. "Google")
   - Wprowadź adres URL (np. "https://www.google.com")
   - Wybierz kolor podświetlenia
   - Potwierdź przyciskiem OK

2. **Przeglądanie strony:**
   - Wybierz stronę z listy rozwijanej
   - Strona zostanie automatycznie załadowana

3. **Usuwanie strony:**
   - Kliknij "Usuń stronę"
   - Wybierz stronę z listy
   - Potwierdź przyciskiem OK

4. **Nawigacja:**
   - Przycisk "Wstecz" - powrót do poprzedniej strony
   - Przycisk "Odśwież" - przeładowanie aktualnej strony
   - Linki na stronie działają normalnie

## Uwagi

- Moduł automatycznie dodaje "https://" do adresów URL bez protokołu
- Kolory na liście dostosowują kolor tekstu (czarny/biały) do jasności tła dla lepszej czytelności
- Historia przeglądania działa w ramach bieżącej sesji
