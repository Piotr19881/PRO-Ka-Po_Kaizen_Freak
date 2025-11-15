-- ============================================================================
-- DIAGNOSTYKA TEAMWORK - ANALIZA PROBLEMU
-- ============================================================================
-- Ten skrypt nie modyfikuje danych - tylko analizuje stan bazy
-- ============================================================================

SET search_path TO s02_teamwork;

-- ============================================================================
-- KROK 1: Sprawdź czy user istnieje w s01_user_accounts
-- ============================================================================
SELECT 
    '=== UŻYTKOWNIK ===' as section,
    id, 
    email, 
    name,
    created_at
FROM s01_user_accounts.users 
WHERE email = 'piotr.prokop@promirbud.eu';

-- ============================================================================
-- KROK 2: Sprawdź grupy w bazie
-- ============================================================================
SELECT 
    '=== WSZYSTKIE GRUPY ===' as section,
    group_id, 
    group_name, 
    created_by,
    is_active,
    created_at
FROM s02_teamwork.work_groups
ORDER BY group_id;

-- ============================================================================
-- KROK 3: Sprawdź członkostwa w grupach
-- ============================================================================
SELECT 
    '=== CZŁONKOSTWA W GRUPACH ===' as section,
    gm.group_member_id,
    gm.group_id,
    g.group_name,
    gm.user_id,
    u.email as user_email,
    gm.role,
    gm.joined_at
FROM s02_teamwork.group_members gm
LEFT JOIN s02_teamwork.work_groups g ON gm.group_id = g.group_id
LEFT JOIN s01_user_accounts.users u ON gm.user_id = u.id
ORDER BY gm.group_id, gm.user_id;

-- ============================================================================
-- KROK 4: Sprawdź członkostwa dla konkretnego user_id
-- ============================================================================
SELECT 
    '=== CZŁONKOSTWA DLA 207222a2-3845-40c2-9bea-cd5bbd6e15f6 ===' as section,
    gm.group_id,
    g.group_name,
    gm.role,
    gm.joined_at
FROM s02_teamwork.group_members gm
JOIN s02_teamwork.work_groups g ON gm.group_id = g.group_id
WHERE gm.user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6'
ORDER BY gm.group_id;

-- ============================================================================
-- KROK 5: Sprawdź tematy w bazie
-- ============================================================================
SELECT 
    '=== WSZYSTKIE TEMATY ===' as section,
    t.topic_id,
    t.topic_name,
    t.group_id,
    g.group_name,
    t.created_by,
    t.is_active,
    t.created_at
FROM s02_teamwork.topics t
LEFT JOIN s02_teamwork.work_groups g ON t.group_id = g.group_id
ORDER BY t.topic_id;

-- ============================================================================
-- KROK 6: Sprawdź członkostwa w tematach
-- ============================================================================
SELECT 
    '=== CZŁONKOSTWA W TEMATACH ===' as section,
    tm.topic_member_id,
    tm.topic_id,
    t.topic_name,
    tm.user_id,
    u.email as user_email,
    tm.role,
    tm.joined_at
FROM s02_teamwork.topic_members tm
LEFT JOIN s02_teamwork.topics t ON tm.topic_id = t.topic_id
LEFT JOIN s01_user_accounts.users u ON tm.user_id = u.id
ORDER BY tm.topic_id, tm.user_id;

-- ============================================================================
-- KROK 7: Sprawdź zadania
-- ============================================================================
SELECT 
    '=== ZADANIA ===' as section,
    task_id,
    topic_id,
    task_subject,
    assigned_to,
    created_by,
    completed,
    is_important,
    due_date,
    created_at
FROM s02_teamwork.tasks
ORDER BY topic_id, task_id;

-- ============================================================================
-- KROK 8: Sprawdź wiadomości
-- ============================================================================
SELECT 
    '=== WIADOMOŚCI ===' as section,
    message_id,
    topic_id,
    user_id,
    LEFT(content, 50) as content_preview,
    is_important,
    created_at
FROM s02_teamwork.messages
ORDER BY topic_id, created_at;

-- ============================================================================
-- KROK 9: Statystyki - czy dane zostały dodane?
-- ============================================================================
SELECT 
    '=== STATYSTYKI OGÓLNE ===' as section,
    (SELECT COUNT(*) FROM s02_teamwork.work_groups) as total_groups,
    (SELECT COUNT(*) FROM s02_teamwork.group_members) as total_group_members,
    (SELECT COUNT(*) FROM s02_teamwork.topics) as total_topics,
    (SELECT COUNT(*) FROM s02_teamwork.topic_members) as total_topic_members,
    (SELECT COUNT(*) FROM s02_teamwork.messages) as total_messages,
    (SELECT COUNT(*) FROM s02_teamwork.tasks) as total_tasks;

-- ============================================================================
-- KROK 10: Test zapytania używanego przez API endpoint
-- ============================================================================
-- To jest dokładnie to zapytanie które wykonuje endpoint /groups
SELECT 
    '=== TEST ZAPYTANIA API (dla user_id = 207222a2-3845-40c2-9bea-cd5bbd6e15f6) ===' as section,
    g.group_id,
    g.group_name,
    g.description,
    g.created_by,
    g.is_active,
    g.created_at,
    COUNT(t.topic_id) as topics_count
FROM s02_teamwork.work_groups g
JOIN s02_teamwork.group_members gm ON g.group_id = gm.group_id
LEFT JOIN s02_teamwork.topics t ON g.group_id = t.group_id AND t.is_active = true
WHERE gm.user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6'
GROUP BY g.group_id, g.group_name, g.description, g.created_by, g.is_active, g.created_at
ORDER BY g.group_id;

-- ============================================================================
-- KROK 11: Sprawdź typy danych kolumn
-- ============================================================================
SELECT 
    '=== TYPY DANYCH ===' as section,
    table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 's02_teamwork' 
AND table_name IN ('work_groups', 'group_members', 'topics', 'topic_members')
AND column_name IN ('user_id', 'created_by', 'assigned_to', 'group_id', 'topic_id')
ORDER BY table_name, column_name;

-- ============================================================================
-- KROK 12: Sprawdź czy są konflikty klucz-wartość (duplikaty)
-- ============================================================================
SELECT 
    '=== DUPLIKATY W GROUP_MEMBERS ===' as section,
    group_id,
    user_id,
    COUNT(*) as count
FROM s02_teamwork.group_members
GROUP BY group_id, user_id
HAVING COUNT(*) > 1;

SELECT 
    '=== DUPLIKATY W TOPIC_MEMBERS ===' as section,
    topic_id,
    user_id,
    COUNT(*) as count
FROM s02_teamwork.topic_members
GROUP BY topic_id, user_id
HAVING COUNT(*) > 1;
