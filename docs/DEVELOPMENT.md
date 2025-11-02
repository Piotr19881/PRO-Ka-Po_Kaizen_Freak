# Development Guide - PRO-Ka-Po Kaizen Freak

## 🚀 Rozpoczęcie Pracy

### 1. Setup Środowiska

```powershell
# Klonowanie repozytorium
git clone <repository-url>
cd PRO-Ka-Po_Kaizen_Freak

# Utworzenie środowiska wirtualnego
python -m venv venv

# Aktywacja środowiska
.\venv\Scripts\Activate.ps1

# Instalacja zależności
pip install -r requirements.txt

# Konfiguracja środowiska
cp .env.example .env
# Edytuj .env zgodnie z potrzebami
```

### 2. Inicjalizacja Bazy Danych

```powershell
# TODO: Dodać skrypty migracji
# python scripts/init_db.py
```

### 3. Uruchomienie Aplikacji

```powershell
python main.py
```

## 🛠️ Narzędzia Deweloperskie

### Code Formatting

```powershell
# Black - formatowanie kodu
black src/ tests/

# autopep8 - alternatywa
autopep8 --in-place --recursive src/
```

### Linting

```powershell
# flake8 - sprawdzanie stylu kodu
flake8 src/ tests/

# mypy - sprawdzanie typów
mypy src/
```

### Testing

```powershell
# Uruchomienie wszystkich testów
pytest

# Z pokryciem kodu
pytest --cov=src tests/

# Wygenerowanie raportu HTML
pytest --cov=src --cov-report=html tests/

# Testy dla konkretnego modułu
pytest tests/test_auth.py

# Testy z verbose output
pytest -v

# Testy z pokazaniem print statements
pytest -s
```

### Pre-commit Hook

Utwórz plik `.git/hooks/pre-commit`:

```bash
#!/bin/sh

echo "Running pre-commit checks..."

# Format check
echo "Checking code formatting..."
black --check src/ tests/
if [ $? -ne 0 ]; then
    echo "Code formatting check failed. Run 'black src/ tests/' to fix."
    exit 1
fi

# Linting
echo "Running linter..."
flake8 src/ tests/
if [ $? -ne 0 ]; then
    echo "Linting failed. Fix the issues and try again."
    exit 1
fi

# Type checking
echo "Running type checker..."
mypy src/
if [ $? -ne 0 ]; then
    echo "Type checking failed. Fix the issues and try again."
    exit 1
fi

# Tests
echo "Running tests..."
pytest
if [ $? -ne 0 ]; then
    echo "Tests failed. Fix the failing tests and try again."
    exit 1
fi

echo "All checks passed!"
exit 0
```

## 📦 Struktura Pakietu

### Dodawanie Nowego Modułu UI

```python
# src/ui/my_new_widget.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

from ..utils.i18n_manager import t


class MyNewWidget(QWidget):
    """
    Widget description
    """
    
    # Signals
    data_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Setup user interface"""
        # TODO: Implement
        pass
    
    def _connect_signals(self) -> None:
        """Connect signals and slots"""
        # TODO: Implement
        pass
```

### Dodawanie Nowego Serwisu

```python
# src/core/my_service.py
from typing import List, Optional
from loguru import logger


class MyService:
    """
    Service description
    """
    
    def __init__(self):
        self._initialized = False
        logger.info("MyService initialized")
    
    def do_something(self, param: str) -> Optional[str]:
        """
        Method description
        
        Args:
            param: Parameter description
            
        Returns:
            Result description
        """
        try:
            # Implementation
            result = f"Processed: {param}"
            return result
        except Exception as e:
            logger.error(f"Error in do_something: {e}")
            return None
```

### Dodawanie Modelu Bazy Danych

```python
# src/database/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class MyModel(Base):
    """Model description"""
    
    __tablename__ = "my_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MyModel(id={self.id}, name='{self.name}')>"
```

## 🎨 Style Guide

### Python Code Style

- **PEP 8** compliance
- **Type hints** dla wszystkich funkcji publicznych
- **Docstrings** w formacie Google Style
- **Max line length**: 100 znaków (tolerance 120)
- **Import ordering**: stdlib → third-party → local

### Import Order Example

```python
# Standard library
import sys
from pathlib import Path
from typing import List, Optional

# Third-party
from PyQt6.QtWidgets import QWidget
from sqlalchemy import Column, Integer

# Local
from ..core.config import config
from ..utils.i18n_manager import t
```

### Docstring Format

```python
def function_name(param1: str, param2: int = 0) -> bool:
    """
    Short description of the function.
    
    Longer description if needed, explaining what the function does
    in more detail.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        RuntimeError: When something goes wrong
        
    Examples:
        >>> function_name("test", 42)
        True
    """
    pass
```

## 🐛 Debugging

### Logging

```python
from loguru import logger

# Different log levels
logger.debug("Detailed information for debugging")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical error")

# Exception logging
try:
    risky_operation()
except Exception as e:
    logger.exception("An error occurred")  # Includes traceback
```

### PyQt Debugging

```python
# Enable Qt warnings
import os
os.environ['QT_DEBUG_PLUGINS'] = '1'

# Print widget hierarchy
def print_widget_tree(widget, indent=0):
    print("  " * indent + str(widget))
    for child in widget.children():
        if isinstance(child, QWidget):
            print_widget_tree(child, indent + 1)
```

### Database Debugging

```python
# Enable SQLAlchemy logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## 🔧 Konfiguracja IDE

### VS Code

Zalecane rozszerzenia:
- Python (Microsoft)
- Pylance
- Black Formatter
- PyQt Integration

`.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [100, 120]
}
```

### PyCharm

- Enable PEP 8 checking
- Set line length to 100
- Enable type checking
- Configure pytest as test runner

## 📊 Performance Profiling

### Memory Profiling

```powershell
pip install memory_profiler

# Add @profile decorator to functions
python -m memory_profiler script.py
```

### Time Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10
```

## 🔄 Database Migrations

```powershell
# TODO: Alembic setup
# alembic init migrations
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head
```

## 📦 Building & Packaging

### PyInstaller

```powershell
# Build executable
pyinstaller --name="KaizenFreak" `
            --windowed `
            --onefile `
            --icon=resources/icons/app.ico `
            main.py

# Output in dist/KaizenFreak.exe
```

### Setup.py Installation

```powershell
# Development install (editable)
pip install -e .

# Production install
pip install .
```

## 🌐 Internationalization Development

### Adding New Translation

```powershell
# 1. Add keys to resources/i18n/en.json (base language)
# 2. Translate to resources/i18n/pl.json
# 3. Translate to resources/i18n/de.json
```

### Using Translations in Code

```python
from src.utils.i18n_manager import t

# Simple translation
text = t("app.title")

# In UI
label.setText(t("auth.username"))
button.setText(t("button.save"))
```

## 🎨 Theme Development

### Creating Custom Theme

```css
/* resources/themes/my_theme.qss */
QMainWindow {
    background-color: #your-color;
}

QPushButton {
    background-color: #button-color;
    color: #text-color;
    /* ... */
}
```

### Applying Theme

```python
from src.utils.theme_manager import ThemeManager

theme_manager = ThemeManager()
theme_manager.apply_theme("my_theme")
```

## 📝 Documentation

### Generating API Docs

```powershell
# Using Sphinx
cd docs
sphinx-apidoc -o source/ ../src/
make html
# Output in docs/_build/html/
```

## 🚀 Deployment Checklist

- [ ] All tests passing
- [ ] Code formatted (black)
- [ ] Linting clean (flake8)
- [ ] Type checking clean (mypy)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Git tag created
- [ ] Build tested
- [ ] Performance tested

## 💡 Tips & Tricks

1. **Use Qt Designer** for complex UI layouts
2. **Signals over direct calls** for loose coupling
3. **Repository pattern** for database access
4. **Config for hardcoded values** - use config.py
5. **Lazy loading** for large datasets
6. **Cache translations and themes**
7. **Use context managers** for database sessions

## 🐞 Common Issues

### Issue: PyQt not found
```powershell
pip install PyQt6 --upgrade
```

### Issue: Database locked
- Close all connections
- Check for hanging transactions

### Issue: Theme not applying
- Check file path
- Verify QSS syntax
- Clear cache

---

**Happy Coding! 🚀**
