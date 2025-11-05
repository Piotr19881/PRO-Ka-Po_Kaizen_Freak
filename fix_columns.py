import sqlite3
import os

# Znajdź bazę danych użytkownika
db_path = os.path.join('src', 'database', 'tasks.db')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Sprawdź aktualne pozycje kolumn
    cursor.execute('SELECT column_id, position FROM task_columns_config WHERE column_id IN ("Subtaski", "Zadanie") ORDER BY position')
    print('Aktualne pozycje kolumn:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: position={row[1]}')
    
    # Usuń konfigurację tych kolumn aby wymusić użycie wartości domyślnych
    print('\nUsuwam konfigurację kolumn Subtaski i Zadanie...')
    cursor.execute('DELETE FROM task_columns_config WHERE column_id IN ("Subtaski", "Zadanie")')
    conn.commit()
    
    print(f'Usunięto {cursor.rowcount} wierszy')
    print('\nZrestartuj aplikację aby zobaczyć zmiany.')
    
    conn.close()
else:
    print(f'Nie znaleziono bazy: {db_path}')
