# Instrukcja: Udostępnianie plików z modułu Folder

## 🚀 Przygotowanie

### 1. Zainstaluj wymagane biblioteki w module Folder

```bash
cd Folder
pip install requests
```

### 2. Uruchom API lokalnie (opcjonalnie)

Jeśli chcesz testować lokalnie przed wdrożeniem na Render:

```bash
cd ../render/Render_upload
pip install -r requirements.txt
python -m app.main
```

API będzie dostępne pod: `http://localhost:8000`

## 📤 Jak udostępnić plik

### Krok 1: Uruchom moduł Folder

```bash
cd Folder
python folder_module.py
```

### Krok 2: Wybierz plik

1. Przejdź do widoku ikon (przycisk "Wyświetl ikony")
2. Znajdź plik, który chcesz udostępnić
3. Kliknij na nim **prawym przyciskiem myszy**

### Krok 3: Wybierz "Udostępnij"

Z menu kontekstowego wybierz opcję **"Udostępnij"**

### Krok 4: Wypełnij formularz

Dialog poprosi o:

- **Email odbiorcy** - adres osoby, która ma otrzymać plik
  - Przykład: `jan.kowalski@example.com`

- **Twoje imię/nazwa** - będzie widoczne w emailu
  - Przykład: `Anna Nowak` lub `Firma XYZ`

- **Język emaila** - wybierz z listy:
  - Polski (pl)
  - English (en)
  - Deutsch (de)

- **URL API** - adres serwera API:
  - Lokalnie: `http://localhost:8000`
  - Produkcja: `https://your-app.onrender.com`

### Krok 5: Kliknij OK

Aplikacja:
1. Wyśle plik do chmury Backblaze B2
2. Wygeneruje publiczny link
3. Wyśle email do odbiorcy

## 📧 Co otrzyma odbiorca?

Odbiorca dostanie piękny email HTML zawierający:

- **Nagłówek** z logo PRO-Ka-Po
- **Informację** kto wysłał plik (Twoje imię)
- **Nazwę pliku** i rozmiar
- **Przycisk "Pobierz plik"** - bezpośredni link do pobrania
- **Informację o wygaśnięciu** - link ważny przez 7 dni

## ⚠️ Ważne informacje

### Limity:
- **Maksymalny rozmiar pliku:** 100 MB
- **Czas ważności linku:** 7 dni
- **Typy plików:** wszystkie (PDF, DOC, JPG, ZIP, itp.)

### Wymagania:
- ✅ Plik (nie folder)
- ✅ Plik istnieje na dysku
- ✅ Rozmiar < 100 MB
- ✅ Połączenie z internetem
- ✅ API uruchomione

### Możliwe błędy:

**"Nie można połączyć się z API"**
- Sprawdź czy URL API jest poprawny
- Upewnij się, że serwer API jest uruchomiony
- Sprawdź połączenie internetowe

**"Plik jest za duży"**
- Maksymalny rozmiar: 100 MB
- Rozważ kompresję (ZIP) lub podział pliku

**"Przekroczono czas"**
- Zbyt wolne połączenie internetowe
- Plik może być za duży
- Spróbuj ponownie

## 🧪 Testowanie

### Test lokalny:

1. Uruchom API lokalnie (`python -m app.main` w folderze Render_upload)
2. W module Folder ustaw URL API: `http://localhost:8000`
3. Wybierz mały plik testowy (np. < 1 MB)
4. Podaj swój własny email jako odbiorcę
5. Kliknij OK i sprawdź skrzynkę odbiorczą

### Test produkcyjny:

1. Wdróż API na Render.com (według instrukcji w Render_upload/README.md)
2. Skopiuj URL swojej aplikacji (np. `https://pro-ka-po.onrender.com`)
3. W module Folder ustaw ten URL jako URL API
4. Udostępnij plik

## 🔧 Konfiguracja API

Upewnij się, że plik `.env` w Render_upload zawiera:

```env
# Backblaze B2
B2_APPLICATION_KEY_ID=20eae90aecce
B2_APPLICATION_KEY=003210436a64eb7edbc1f8464efb84b3971879ef41
B2_BUCKET_NAME=Pro-Ka-Po
B2_BUCKET_ID=22903eaa0ed9404a9eac0c1e

# Email (Gmail)
SMTP_USERNAME=probud.construction@gmail.com
SMTP_PASSWORD=pvzc ryot gbpo lpbk
SMTP_FROM_EMAIL=probud.construction@gmail.com
```

## 📝 Przykładowy scenariusz

**Sytuacja:** Chcesz wysłać raport PDF do klienta

1. Dodaj plik do modułu Folder (jeśli jeszcze go nie ma)
2. Przejdź do widoku ikon
3. Kliknij prawym na pliku raportu
4. Wybierz "Udostępnij"
5. Wypełnij:
   - Email: `klient@firma.pl`
   - Imię: `Jan Kowalski - PRO-Ka-Po`
   - Język: Polski
   - URL API: `https://your-api.onrender.com`
6. Kliknij OK
7. Po chwili otrzymasz potwierdzenie
8. Klient otrzyma email z linkiem do pobrania

## 🎉 Gotowe!

Twój klient może teraz pobrać plik klikając przycisk w emailu. Link będzie aktywny przez 7 dni.
