import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

print('Struktura tabeli task_columns_config:')
rows = cursor.execute('PRAGMA table_info(task_columns_config)').fetchall()
for r in rows:
    print(f'  {r}')

print('\nWszystkie kolumny:')
rows = cursor.execute('SELECT * FROM task_columns_config LIMIT 5').fetchall()
for r in rows:
    print(f'  {r}')

conn.close()
