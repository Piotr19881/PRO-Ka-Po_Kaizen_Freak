"""Quick script to check PostgreSQL database contents"""
import psycopg2

conn = psycopg2.connect(
    'postgresql://pro_ka_po_kaizen_freak_user:BjjezyKd1oiAW2KQd20ze63RcIH6Hhxt@dpg-ct91r8aj1k6c73a7pbu0-a.frankfurt-postgres.render.com/pro_ka_po_kaizen_freak'
)
cur = conn.cursor()

user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6'

# Count total items
cur.execute('SELECT COUNT(*) FROM s04_alarms_timers.alarms_timers WHERE user_id = %s', (user_id,))
count = cur.fetchone()[0]
print(f'Total items in DB: {count}')

# Get item details
cur.execute('''
    SELECT id, type, label, deleted_at, enabled, created_at 
    FROM s04_alarms_timers.alarms_timers 
    WHERE user_id = %s 
    ORDER BY created_at DESC
    LIMIT 10
''', (user_id,))

rows = cur.fetchall()
print(f'\nItems:')
for row in rows:
    item_id, item_type, label, deleted_at, enabled, created_at = row
    status = "DELETED" if deleted_at else ("ENABLED" if enabled else "DISABLED")
    print(f'- {item_id[:8]}... {item_type:5} "{label}" [{status}] created={created_at}')

cur.close()
conn.close()
