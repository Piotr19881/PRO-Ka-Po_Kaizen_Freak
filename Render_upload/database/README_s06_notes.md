# Instrukcja wykonania schematu s06_notes

## Metoda 1: PostgreSQL Client (psql)

```bash
psql -h dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com \
     -U pro_ka_po_user \
     -d pro_ka_po \
     -f Render_upload/database/s06_notes_schema.sql
```

**Hasło:** `01pHONi8u23ZlHNffO64TcmWywetoiUD`

---

## Metoda 2: DBeaver / pgAdmin

1. Połącz się z bazą:
   - Host: `dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com`
   - Port: `5432`
   - Database: `pro_ka_po`
   - Username: `pro_ka_po_user`
   - Password: `01pHONi8u23ZlHNffO64TcmWywetoiUD`

2. Otwórz plik `s06_notes_schema.sql`
3. Wykonaj całe query (Execute SQL)

---

## Metoda 3: Python Script (automatyczna)

```python
import psycopg2

conn = psycopg2.connect(
    host="dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com",
    port=5432,
    database="pro_ka_po",
    user="pro_ka_po_user",
    password="01pHONi8u23ZlHNffO64TcmWywetoiUD"
)

cursor = conn.cursor()

with open('Render_upload/database/s06_notes_schema.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
    cursor.execute(sql)

conn.commit()
cursor.close()
conn.close()

print("✅ Schema s06_notes created successfully!")
```

---

## Weryfikacja po wykonaniu

Wykonaj query:

```sql
-- Sprawdź czy schemat istnieje
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name = 's06_notes';

-- Sprawdź tabele
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 's06_notes';

-- Sprawdź funkcje
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 's06_notes';
```

Oczekiwany wynik:
- ✅ Schema: `s06_notes`
- ✅ Tables: `notes`, `note_links`
- ✅ Views: `active_notes`, `root_notes`, `user_stats`
- ✅ Functions: `get_note_path`, `get_note_descendants`, `soft_delete_note_cascade`

---

## Co zostało utworzone?

### Tabele:
1. **s06_notes.notes** - główna tabela notatek
   - Hierarchia (parent_id)
   - Soft delete (deleted_at)
   - Versioning (version)
   - Sync metadata (synced_at)

2. **s06_notes.note_links** - hiperłącza między notatkami

### Indeksy (8 szt):
- Wydajne wyszukiwanie po user_id
- Szybkie pobieranie hierarchii
- Optymalizacja queries synchronizacji

### Triggery (3 szt):
- Auto-update `updated_at`
- Auto-increment `version` (conflict resolution)
- Zapobieganie cyklom w hierarchii

### Views (3 szt):
- `active_notes` - tylko aktywne
- `root_notes` - notatki główne
- `user_stats` - statystyki

### Functions (3 szt):
- `get_note_path()` - breadcrumb (ścieżka hierarchii)
- `get_note_descendants()` - wszystkie dzieci rekurencyjnie
- `soft_delete_note_cascade()` - soft delete z cascade

---

## Gotowe do następnego kroku!

Po pomyślnym wykonaniu schematu przechodzimy do:
**Krok 2: Backend Models (SQLAlchemy)** 🚀
