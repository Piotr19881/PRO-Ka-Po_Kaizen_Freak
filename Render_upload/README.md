# PRO-Ka-Po API - Render Deployment

FastAPI application dla bezpiecznej komunikacji między aplikacją desktopową PRO-Ka-Po a bazą danych PostgreSQL.

## 📋 Struktura projektu

```
Render_upload/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application & endpoints
│   ├── config.py            # Configuration management
│   └── database.py          # Database models & connection
├── requirements.txt         # Python dependencies
├── runtime.txt             # Python version
├── render.yaml             # Render deployment config
├── .env                    # Environment variables (production)
├── .env.example            # Example environment file
└── README.md               # Ten plik
```

## 🚀 Deployment na Render

### Krok 1: Przygotowanie repozytorium
```bash
cd Render_upload
git init
git add .
git commit -m "Initial commit: PRO-Ka-Po API"
```

### Krok 2: Push do GitHub/GitLab
Utwórz nowe repozytorium i wypchnij kod:
```bash
git remote add origin <your-repo-url>
git push -u origin main
```

### Krok 3: Deploy na Render
1. Zaloguj się na https://render.com
2. Kliknij "New +" → "Web Service"
3. Połącz repozytorium
4. Render automatycznie wykryje `render.yaml`
5. Kliknij "Apply" aby wdrożyć

## 🔧 Konfiguracja lokalna (development)

### Instalacja zależności
```bash
pip install -r requirements.txt
```

### Konfiguracja zmiennych środowiskowych
Skopiuj `.env.example` do `.env` i dostosuj wartości:
```bash
cp .env.example .env
```

### Uruchomienie lokalnie
```bash
# Z katalogu Render_upload
python -m app.main

# Lub używając uvicorn bezpośrednio
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API będzie dostępne pod:
- http://localhost:8000
- Dokumentacja: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📡 Endpoints

### Status & Health
- `GET /` - Informacje o API
- `GET /health` - Health check (status + database)
- `GET /api/test` - Test połączenia z bazą

### API Info
- `GET /api/v1/info` - Informacje o dostępnych endpointach

### Planowane endpoints (TODO)
- `POST /api/v1/auth/register` - Rejestracja użytkownika
- `POST /api/v1/auth/login` - Logowanie
- `POST /api/v1/auth/refresh` - Odświeżenie tokena
- `GET /api/v1/users/me` - Pobierz dane zalogowanego użytkownika
- `GET /api/v1/tasks` - Lista zadań
- `POST /api/v1/tasks` - Utwórz zadanie
- `GET /api/v1/kanban/boards` - Lista tablic Kanban

## 🗄️ Baza danych

### Konfiguracja PostgreSQL
```
Host: dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com
Port: 5432
Database: pro_ka_po
User: pro_ka_po_user
Password: 01pHONi8u23ZlHNffO64TcmWywetoiUD
```

### Modele (SQLAlchemy)
- **User** - Użytkownicy systemu
- **Task** - Zadania
- **KanbanBoard** - Tablice Kanban
- **KanbanCard** - Karty na tablicach

## 🔐 Bezpieczeństwo

- Hasła hashowane używając **bcrypt**
- Autoryzacja przez **JWT tokens**
- CORS skonfigurowany dla bezpiecznej komunikacji
- Zmienne wrażliwe w zmiennych środowiskowych

### Ważne!
⚠️ **Nigdy nie commituj pliku `.env` do repozytorium!**

Dodaj do `.gitignore`:
```
.env
__pycache__/
*.pyc
.venv/
```

## 📦 Zależności

- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **SQLAlchemy** - ORM
- **Psycopg2** - PostgreSQL adapter
- **Python-JOSE** - JWT tokens
- **Passlib** - Password hashing
- **Pydantic** - Data validation

## 🧪 Testowanie

### Test lokalny
```bash
# Uruchom serwer
python -m app.main

# W innym terminalu
curl http://localhost:8000/health
```

### Test na Render
Po wdrożeniu:
```bash
curl https://your-app-name.onrender.com/health
```

## 📝 Następne kroki

1. ✅ Struktura aplikacji
2. ✅ Konfiguracja bazy danych
3. ✅ Podstawowe endpoints (health, test)
4. 🔄 Implementacja autoryzacji (register/login)
5. 🔄 Endpoints dla zadań
6. 🔄 Endpoints dla Kanban
7. 🔄 Integracja z aplikacją desktopową

## 🆘 Troubleshooting

### Błąd połączenia z bazą
- Sprawdź czy dane w `.env` są poprawne
- Upewnij się że baza danych jest online
- Sprawdź logi: `render logs` lub w Dashboard Render

### Port binding error
- Render automatycznie przypisuje port przez `$PORT`
- Lokalnie używaj portu 8000

## 📄 Licencja

Proprietary - PRO-Ka-Po Kaizen Freak Application
