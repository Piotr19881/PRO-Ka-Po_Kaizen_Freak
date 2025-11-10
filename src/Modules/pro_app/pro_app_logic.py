"""
Pro-App Logic - Logika biznesowa modułu kompilacji i wykonywania skryptów Python

Ten moduł zawiera całą logikę związaną z:
- Testowaniem składni kodu Python
- Wykrywaniem importowanych modułów
- Sprawdzaniem dostępności bibliotek
- Uruchamianiem kodu Python
- Instalacją brakujących pakietów
- Generowaniem plików .bat i .py
"""

import sys
import os
import ast
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from loguru import logger


class ProAppLogic:
    """Logika biznesowa modułu Pro-App"""
    
    # Lista standardowych modułów Pythona (nie wymagających instalacji)
    STANDARD_MODULES = {
        'sys', 'os', 're', 'json', 'datetime', 'time', 
        'math', 'random', 'collections', 'itertools',
        'functools', 'pathlib', 'subprocess', 'threading',
        'multiprocessing', 'logging', 'argparse', 'unittest',
        'ast', 'copy', 'pickle', 'shelve', 'sqlite3',
        'csv', 'xml', 'html', 'http', 'urllib', 'email',
        'hashlib', 'hmac', 'secrets', 'typing', 'dataclasses',
        'enum', 'decimal', 'fractions', 'statistics', 'queue',
        'socket', 'ssl', 'select', 'asyncio', 'concurrent',
        'contextlib', 'weakref', 'gc', 'inspect', 'dis',
        'tempfile', 'shutil', 'glob', 'fnmatch', 'linecache',
        'traceback', 'warnings', 'importlib', 'pkgutil'
    }
    
    def __init__(self):
        """Inicjalizacja logiki Pro-App"""
        self.syntax_ok = False
        self.last_code = ""
        self.missing_modules: List[str] = []
        logger.info("[ProApp] Logic initialized")
    
    def test_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Testuje składnię kodu Python
        
        Args:
            code: Kod Python do przetestowania
            
        Returns:
            Tuple[bool, Optional[str]]: (czy_poprawna, komunikat_bledu)
        """
        if not code.strip():
            return False, "Edytor jest pusty! Wklej kod do testowania."
        
        self.last_code = code
        
        try:
            ast.parse(code)
            self.syntax_ok = True
            logger.info("[ProApp] Syntax check passed")
            return True, None
            
        except SyntaxError as e:
            self.syntax_ok = False
            error_msg = f"Błąd składni w linii {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n{e.text.strip()}"
            logger.error(f"[ProApp] Syntax error: {error_msg}")
            return False, error_msg
            
        except Exception as e:
            self.syntax_ok = False
            error_msg = f"Błąd: {str(e)}"
            logger.error(f"[ProApp] Unexpected error: {error_msg}")
            return False, error_msg
    
    def detect_imports(self, code: str) -> Dict[str, List[str]]:
        """
        Wykrywa importowane moduły w kodzie
        
        Args:
            code: Kod Python do analizy
            
        Returns:
            Dict zawierający:
                'all': wszystkie znalezione importy
                'available': dostępne moduły
                'missing': brakujące moduły
        """
        import_pattern = r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        imports = set()
        
        for line in code.split('\n'):
            match = re.match(import_pattern, line)
            if match:
                module_name = match.group(1)
                # Pomiń standardowe biblioteki Pythona
                if module_name not in self.STANDARD_MODULES:
                    imports.add(module_name)
        
        all_imports = list(sorted(imports))
        available = []
        missing = []
        
        for module_name in all_imports:
            if self.check_module_available(module_name):
                available.append(module_name)
            else:
                missing.append(module_name)
        
        self.missing_modules = missing
        
        logger.info(f"[ProApp] Detected {len(all_imports)} imports: {len(available)} available, {len(missing)} missing")
        
        return {
            'all': all_imports,
            'available': available,
            'missing': missing
        }
    
    def check_module_available(self, module_name: str) -> bool:
        """
        Sprawdza czy moduł jest dostępny w systemie
        
        Args:
            module_name: Nazwa modułu do sprawdzenia
            
        Returns:
            bool: True jeśli moduł jest dostępny
        """
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def run_code(self, code: str, timeout: int = 30) -> Dict[str, any]:
        """
        Uruchamia kod Python w subprocess
        
        Args:
            code: Kod Python do uruchomienia
            timeout: Maksymalny czas wykonania w sekundach
            
        Returns:
            Dict z kluczami:
                'success': bool - czy wykonanie się powiodło
                'stdout': str - wyjście standardowe
                'stderr': str - błędy
                'returncode': int - kod wyjścia
                'missing_modules': List[str] - wykryte brakujące moduły
        """
        if not self.syntax_ok:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Najpierw przetestuj składnię!',
                'returncode': -1,
                'missing_modules': []
            }
        
        temp_file = "temp_proapp_script.py"
        
        try:
            # Zapisz kod do tymczasowego pliku
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            python_path = sys.executable
            logger.info(f"[ProApp] Running code with Python: {python_path}")
            
            # Uruchom kod
            result = subprocess.run(
                [python_path, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Wykryj brakujące moduły w błędach
            detected_missing = self._extract_missing_modules(result.stderr)
            
            logger.info(f"[ProApp] Code execution completed with return code: {result.returncode}")
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'missing_modules': detected_missing
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"[ProApp] Code execution timeout ({timeout}s)")
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Przekroczono limit czasu ({timeout}s)!',
                'returncode': -1,
                'missing_modules': []
            }
            
        except Exception as e:
            logger.error(f"[ProApp] Code execution error: {str(e)}")
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Błąd podczas uruchamiania: {str(e)}',
                'returncode': -1,
                'missing_modules': []
            }
            
        finally:
            # Usuń plik tymczasowy
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
    
    def _extract_missing_modules(self, error_text: str) -> List[str]:
        """
        Wydobywa nazwy brakujących modułów z tekstu błędu
        
        Args:
            error_text: Tekst błędu z stderr
            
        Returns:
            Lista nazw brakujących modułów
        """
        patterns = [
            r"ModuleNotFoundError: No module named '([^']+)'",
            r"ImportError: No module named ([^\s]+)",
        ]
        
        missing = set()
        for pattern in patterns:
            matches = re.findall(pattern, error_text)
            missing.update(matches)
        
        return list(sorted(missing))
    
    def install_module(self, module_name: str, timeout: int = 120) -> Tuple[bool, str]:
        """
        Instaluje moduł przez pip
        
        Args:
            module_name: Nazwa modułu do zainstalowania
            timeout: Maksymalny czas instalacji w sekundach
            
        Returns:
            Tuple[bool, str]: (sukces, komunikat)
        """
        python_path = sys.executable
        logger.info(f"[ProApp] Installing module: {module_name}")
        
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install", module_name],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"[ProApp] Module {module_name} installed successfully")
                return True, f"Biblioteka {module_name} zainstalowana pomyślnie!"
            else:
                logger.error(f"[ProApp] Module {module_name} installation failed: {result.stderr}")
                return False, f"Błąd instalacji:\n{result.stderr}"
                
        except subprocess.TimeoutExpired:
            logger.error(f"[ProApp] Module {module_name} installation timeout")
            return False, f"Przekroczono limit czasu instalacji ({timeout}s)!"
            
        except Exception as e:
            logger.error(f"[ProApp] Module {module_name} installation error: {str(e)}")
            return False, f"Błąd: {str(e)}"
    
    def get_package_version(self, package_name: str) -> str:
        """
        Pobiera wersję zainstalowanego pakietu
        
        Args:
            package_name: Nazwa pakietu
            
        Returns:
            str: Wersja pakietu lub "???" jeśli nie można określić
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        logger.debug(f"[ProApp] Package {package_name} version: {version}")
                        return version
            
            return "???"
            
        except Exception:
            return "???"
    
    def save_as_bat(self, code: str, file_path: str, with_console: bool = True) -> Tuple[bool, str]:
        """
        Zapisuje kod jako plik .bat wraz ze skryptem .py
        
        Args:
            code: Kod Python do zapisania
            file_path: Ścieżka do pliku .bat
            with_console: Czy bat ma otwierać konsolę
            
        Returns:
            Tuple[bool, str]: (sukces, komunikat)
        """
        try:
            if not file_path.endswith('.bat'):
                file_path += '.bat'
            
            # Zapisz kod Python w tym samym katalogu
            bat_dir = os.path.dirname(file_path) or '.'
            bat_name = os.path.splitext(os.path.basename(file_path))[0]
            py_file = os.path.join(bat_dir, f"{bat_name}.py")
            
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Utwórz plik .bat
            python_path = sys.executable
            
            if with_console:
                bat_content = f'@echo off\n"{python_path}" "%~dp0{bat_name}.py"\npause\n'
            else:
                bat_content = f'@echo off\nstart /B "" "{python_path}" "%~dp0{bat_name}.py"\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            logger.info(f"[ProApp] Saved BAT file: {file_path} and Python script: {py_file}")
            return True, f"Zapisano:\nBAT: {file_path}\nPython: {py_file}"
            
        except Exception as e:
            logger.error(f"[ProApp] Error saving BAT file: {str(e)}")
            return False, f"Błąd podczas zapisywania: {str(e)}"
    
    def save_as_python(self, code: str, file_path: str) -> Tuple[bool, str]:
        """
        Zapisuje kod jako plik .py
        
        Args:
            code: Kod Python do zapisania
            file_path: Ścieżka do pliku .py
            
        Returns:
            Tuple[bool, str]: (sukces, komunikat)
        """
        try:
            if not file_path.endswith('.py'):
                file_path += '.py'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            logger.info(f"[ProApp] Saved Python script: {file_path}")
            return True, f"Zapisano skrypt Python:\n{file_path}"
            
        except Exception as e:
            logger.error(f"[ProApp] Error saving Python file: {str(e)}")
            return False, f"Błąd podczas zapisywania: {str(e)}"
    
    def reset(self):
        """Resetuje stan logiki"""
        self.syntax_ok = False
        self.last_code = ""
        self.missing_modules = []
        logger.info("[ProApp] Logic reset")
