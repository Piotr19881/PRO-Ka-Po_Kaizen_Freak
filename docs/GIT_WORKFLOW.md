# Git Workflow - PRO-Ka-Po Kaizen Freak Project

## 📋 Konwencje Git dla Projektu

### Branch Strategy

Projekt wykorzystuje **Git Flow** z następującymi gałęziami:

#### Główne Gałęzie
- `main` - produkcyjna wersja aplikacji (stabilna)
- `develop` - główna gałąź rozwojowa

#### Gałęzie Wspomagające
- `feature/*` - nowe funkcjonalności
- `bugfix/*` - poprawki błędów
- `hotfix/*` - pilne poprawki w produkcji
- `release/*` - przygotowanie do wydania

### Nazewnictwo Branch'y

```
feature/nazwa-funkcjonalnosci
bugfix/opis-bledu
hotfix/opis-poprawki
release/v1.0.0
```

**Przykłady:**
```
feature/login-system
feature/task-management
bugfix/password-validation
hotfix/database-connection
release/v0.1.0
```

## 🔄 Workflow

### 1. Rozpoczęcie Pracy nad Nową Funkcjonalnością

```bash
# Upewnij się, że masz najnowszą wersję develop
git checkout develop
git pull origin develop

# Utwórz nową gałąź feature
git checkout -b feature/nazwa-funkcjonalnosci

# Pracuj nad funkcjonalnością...
# Dodaj zmiany
git add .
git commit -m "feat: opis zmian"

# Push do repozytorium
git push -u origin feature/nazwa-funkcjonalnosci
```

### 2. Praca nad Poprawką Błędu

```bash
git checkout develop
git pull origin develop

git checkout -b bugfix/opis-bledu

# Napraw błąd...
git add .
git commit -m "fix: opis poprawki"

git push -u origin bugfix/opis-bledu
```

### 3. Merge do Develop

```bash
# Po zakończeniu pracy i zatwierdzeniu PR
git checkout develop
git pull origin develop
git merge --no-ff feature/nazwa-funkcjonalnosci
git push origin develop

# Usuń gałąź feature (lokalnie i zdalnie)
git branch -d feature/nazwa-funkcjonalnosci
git push origin --delete feature/nazwa-funkcjonalnosci
```

### 4. Przygotowanie Release

```bash
git checkout develop
git pull origin develop

git checkout -b release/v0.1.0

# Aktualizuj wersję w plikach
# - setup.py
# - src/__init__.py
# - README.md

git add .
git commit -m "chore: bump version to 0.1.0"

# Merge do main i develop
git checkout main
git merge --no-ff release/v0.1.0
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin main --tags

git checkout develop
git merge --no-ff release/v0.1.0
git push origin develop

git branch -d release/v0.1.0
```

## 📝 Konwencje Commit Messages

Projekt używa **Conventional Commits**:

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Typy Commitów

- `feat`: nowa funkcjonalność
- `fix`: poprawka błędu
- `docs`: zmiany w dokumentacji
- `style`: formatowanie kodu (bez zmian logicznych)
- `refactor`: refaktoryzacja kodu
- `perf`: poprawa wydajności
- `test`: dodanie lub modyfikacja testów
- `chore`: zmiany w konfiguracji, build, itp.
- `build`: zmiany w systemie budowania
- `ci`: zmiany w CI/CD

### Scope (Opcjonalny)

- `ui`: zmiany w interfejsie użytkownika
- `auth`: system autentykacji
- `db`: baza danych
- `api`: API aplikacji
- `config`: konfiguracja
- `i18n`: internacjonalizacja
- `theme`: motywy

### Przykłady

```bash
# Nowa funkcjonalność
git commit -m "feat(auth): add user registration form"

# Poprawka błędu
git commit -m "fix(ui): resolve table scrolling issue"

# Dokumentacja
git commit -m "docs: update README with installation steps"

# Refaktoryzacja
git commit -m "refactor(db): optimize database queries"

# Style
git commit -m "style: format code with black"

# Testy
git commit -m "test(auth): add unit tests for login"

# Konfiguracja
git commit -m "chore: update dependencies"
```

### Dłuższe Commity

```bash
git commit -m "feat(ui): add quick input section

- Added two-row quick input form at bottom
- Implemented auto-save functionality
- Added keyboard shortcuts (Ctrl+Enter to save)

Closes #123"
```

## 🔍 Code Review Process

### Pull Request Checklist

Przed utworzeniem PR upewnij się, że:

- [ ] Kod jest zgodny z PEP 8
- [ ] Wszystkie testy przechodzą
- [ ] Dodano testy dla nowych funkcjonalności
- [ ] Zaktualizowano dokumentację
- [ ] Nie ma konfliktów z develop
- [ ] Commit messages są zgodne z konwencją
- [ ] Code coverage nie spadł

### Tworzenie Pull Request

```bash
# Na GitHub/GitLab utwórz PR z:
# - Opisem zmian
# - Referencją do issue (#123)
# - Screenshots (jeśli UI)
# - Lista zmian
```

**Szablon PR:**
```markdown
## Opis
Krótki opis zmian

## Typ zmiany
- [ ] Nowa funkcjonalność
- [ ] Poprawka błędu
- [ ] Dokumentacja
- [ ] Refaktoryzacja

## Testy
- [ ] Testy jednostkowe dodane/zaktualizowane
- [ ] Testy manualne przeprowadzone

## Screenshots
(jeśli dotyczy UI)

## Checklist
- [ ] Kod zgodny z PEP 8
- [ ] Dokumentacja zaktualizowana
- [ ] Testy przechodzą
- [ ] Nie ma konfliktów

## Related Issues
Closes #123
```

## 🏷️ Tagging

### Semantic Versioning

Projekt używa **Semantic Versioning** (MAJOR.MINOR.PATCH):

- `MAJOR`: niekompatybilne zmiany API
- `MINOR`: nowe funkcjonalności (kompatybilne wstecz)
- `PATCH`: poprawki błędów

**Przykłady:**
- `v0.1.0` - pierwsza wersja alpha
- `v0.2.0` - dodano nowe funkcje
- `v0.2.1` - poprawki błędów
- `v1.0.0` - pierwsza stabilna wersja

### Tworzenie Tagów

```bash
# Annotated tag (zalecany)
git tag -a v0.1.0 -m "Release version 0.1.0 - MVP"

# Push tagów
git push origin --tags

# Lista tagów
git tag -l

# Usunięcie taga
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0
```

## 🚫 .gitignore - Co Ignorujemy

- Pliki Python (`__pycache__`, `*.pyc`)
- Środowiska wirtualne (`venv/`, `.env`)
- IDE (`.vscode/`, `.idea/`)
- Bazy danych (`*.db`, `*.sqlite`)
- Logi (`logs/`, `*.log`)
- Dane użytkownika (`user_data/`, `backups/`)
- Sekretne dane (`.env.local`, `secrets.json`)
- Pliki tymczasowe (`*.tmp`, `temp/`)

## 🔒 Bezpieczeństwo

### Nigdy nie commituj:
- Haseł i kluczy API
- Tokenów dostępu
- Danych użytkowników
- Certyfikatów i kluczy prywatnych
- Plików konfiguracyjnych z sekretami

### Używaj:
- `.env` dla zmiennych środowiskowych
- `secrets.json` dla kluczy (dodaj do .gitignore)
- Zmiennych środowiskowych w CI/CD

## 📊 Git Best Practices

1. **Commituj często** - małe, atomowe zmiany
2. **Pull przed push** - zawsze synchronizuj przed wysłaniem
3. **Używaj PR** - nawet dla małych zmian
4. **Code review** - zawsze poproś o review
5. **Testuj lokalnie** - przed commitem
6. **Nie commituj do main** - zawsze przez PR
7. **Używaj .gitignore** - nie commituj śmieci
8. **Opisuj zmiany** - jasne commit messages
9. **Rebase vs Merge** - używaj merge dla przejrzystości
10. **Backup** - regularnie push do remote

## 🛠️ Przydatne Komendy

```bash
# Status i różnice
git status
git diff
git diff --staged

# Historia
git log --oneline --graph --all
git log --author="Jan Kowalski"

# Cofnięcie zmian
git checkout -- file.py          # cofnij zmiany w pliku
git reset HEAD file.py           # usuń z staging
git reset --soft HEAD~1          # cofnij ostatni commit (zmiany zostają)
git reset --hard HEAD~1          # cofnij ostatni commit (usuń zmiany)

# Stash (schowek)
git stash                        # schowaj zmiany
git stash pop                    # przywróć zmiany
git stash list                   # lista schowanych zmian

# Branch management
git branch -a                    # wszystkie gałęzie
git branch -d feature/name       # usuń lokalną gałąź
git push origin --delete feature/name  # usuń zdalną gałąź

# Aktualizacja
git fetch --all --prune          # pobierz wszystkie zmiany
git pull --rebase                # pull z rebase
```

## 📞 Pomoc

W razie problemów:
1. Sprawdź dokumentację Git
2. Zapytaj na zespołowym czacie
3. Używaj `git help <command>`

---

**Utworzono:** Listopad 2025
**Wersja:** 1.0
