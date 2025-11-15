-- ============================================================================
-- DANE TESTOWE - MODUŁ TEAMWORK
-- ============================================================================
-- Data: 2024-11-14
-- Opis: Przykładowe dane dla testowania synchronizacji i współpracy
-- User: piotr.prokop@promirbud.eu
-- ============================================================================

SET search_path TO s02_teamwork;

-- ============================================================================
-- KROK 1: Znajdź user_id dla piotr.prokop@promirbud.eu
-- ============================================================================

DO $$
DECLARE
    v_user_id TEXT;
BEGIN
    -- Znajdź user_id
    SELECT id INTO v_user_id 
    FROM s01_user_accounts.users 
    WHERE email = 'piotr.prokop@promirbud.eu';
    
    IF v_user_id IS NULL THEN
        RAISE NOTICE 'User not found! Please check email address.';
        RAISE NOTICE 'Available users:';
        FOR v_user_id IN 
            SELECT email FROM s01_user_accounts.users LIMIT 5
        LOOP
            RAISE NOTICE '  - %', v_user_id;
        END LOOP;
    ELSE
        RAISE NOTICE 'Found user_id: %', v_user_id;
    END IF;
END $$;

-- ============================================================================
-- KROK 2: Wyświetl user_id (uruchom to osobno aby zobaczyć wynik)
-- ============================================================================

SELECT id as user_id, email, name 
FROM s01_user_accounts.users 
WHERE email LIKE '%piotr%' OR email LIKE '%prokop%' OR email LIKE '%promirbud%'
LIMIT 5;

-- Jeśli nie znalazło, pokaż wszystkich użytkowników:
SELECT id as user_id, email, name 
FROM s01_user_accounts.users 
ORDER BY created_at DESC
LIMIT 10;

-- ============================================================================
-- KROK 3: Wstaw dane testowe (ZAMIEŃ 'USER_ID_HERE' na prawdziwe ID!)
-- ============================================================================

-- UWAGA: Po znalezieniu user_id, zamień wszystkie wystąpienia 'USER_ID_HERE' poniżej!

-- Grupa 1: Projekty Pro-Ka-Po
INSERT INTO s02_teamwork.work_groups (group_id, group_name, description, created_by, is_active, sync_status, version)
VALUES 
    (1, 'Pro-Ka-Po - Projekty główne', 'Główne projekty aplikacji Pro-Ka-Po', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1)
ON CONFLICT (group_id) DO NOTHING;

-- Grupa 2: Team Development
INSERT INTO s02_teamwork.work_groups (group_id, group_name, description, created_by, is_active, sync_status, version)
VALUES 
    (2, 'Team Development', 'Rozwój zespołowy i współpraca', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1)
ON CONFLICT (group_id) DO NOTHING;

-- Dodaj siebie jako członka grup
INSERT INTO s02_teamwork.group_members (group_id, user_id, role)
VALUES 
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner')
ON CONFLICT (group_id, user_id) DO NOTHING;

-- Tematy w grupie 1
INSERT INTO s02_teamwork.topics (topic_id, group_id, topic_name, created_by, is_active, sync_status, version)
VALUES 
    (1, 1, 'Moduł TeamWork - Implementacja', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1),
    (2, 1, 'Synchronizacja offline', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1),
    (3, 1, 'Integracja Backblaze B2', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1)
ON CONFLICT (topic_id) DO NOTHING;

-- Tematy w grupie 2
INSERT INTO s02_teamwork.topics (topic_id, group_id, topic_name, created_by, is_active, sync_status, version)
VALUES 
    (4, 2, 'Sprint Planning - Listopad 2024', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1),
    (5, 2, 'Code Review Process', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', true, 'synced', 1)
ON CONFLICT (topic_id) DO NOTHING;

-- Dodaj siebie jako członka wątków
INSERT INTO s02_teamwork.topic_members (topic_id, user_id, role)
VALUES 
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (3, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (4, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (5, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner')
ON CONFLICT (topic_id, user_id) DO NOTHING;

-- Wiadomości w wątku 1 (TeamWork Implementation)
INSERT INTO s02_teamwork.messages (topic_id, user_id, content, background_color, is_important, sync_status, version)
VALUES 
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Rozpoczynam implementację modułu TeamWork. Plan zakłada 7 faz rozwoju.', '#E3F2FD', true, 'synced', 1),
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Phase 1-4 ukończone! Podstawowa funkcjonalność działa. ✅', '#C8E6C9', false, 'synced', 1),
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Phase 5: Synchronizacja offline - w trakcie implementacji. Dodaję kolumny sync do wszystkich tabel.', '#FFF9C4', false, 'synced', 1),
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Phase 6: Współpraca zespołowa - dodaję zaproszenia, linki udostępniania i zarządzanie uprawnieniami.', '#F3E5F5', false, 'synced', 1)
ON CONFLICT DO NOTHING;

-- Wiadomości w wątku 2 (Synchronizacja)
INSERT INTO s02_teamwork.messages (topic_id, user_id, content, background_color, is_important, sync_status, version)
VALUES 
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Architektura: SQLite (local) ↔️ SyncManager ↔️ PostgreSQL (Render)', '#E1F5FE', true, 'synced', 1),
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Wykrywanie konfliktów: wersjonowanie + timestamp. Trzy strategie rozwiązywania: keep_local, keep_remote, merge.', '#FFFFFF', false, 'synced', 1),
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Triggery automatycznie oznaczają rekordy jako modified_locally = true przy każdej zmianie.', '#E8F5E9', false, 'synced', 1)
ON CONFLICT DO NOTHING;

-- Wiadomości w wątku 4 (Sprint Planning)
INSERT INTO s02_teamwork.messages (topic_id, user_id, content, background_color, is_important, sync_status, version)
VALUES 
    (4, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '📋 Sprint Goals:\n1. Dokończyć TeamWork sync\n2. Przetestować B2 upload\n3. Zaimplementować permissions', '#FFF3E0', true, 'synced', 1),
    (4, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'Daily standup: Dzisiaj skupiam się na migracji PostgreSQL i danych testowych.', '#FFFFFF', false, 'synced', 1)
ON CONFLICT DO NOTHING;

-- Zadania w wątku 1
INSERT INTO s02_teamwork.tasks (topic_id, task_subject, task_description, assigned_to, created_by, due_date, completed, is_important, sync_status, version)
VALUES 
    (1, 'Zaimplementować SyncManager.push_all()', 'Funkcja wysyłająca lokalne zmiany na serwer z batch upload', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '7 days', true, true, 'synced', 1),
    (1, 'Zaimplementować SyncManager.pull_all()', 'Funkcja pobierająca zmiany z serwera (incremental sync)', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '7 days', true, true, 'synced', 1),
    (1, 'Dodać resolution UI dla konfliktów', 'Dialog pozwalający użytkownikowi wybrać strategię rozwiązania konfliktu', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '14 days', false, true, 'synced', 1),
    (1, 'Przetestować synchronizację end-to-end', 'Pełny test: create local → push → modify server → pull → resolve conflicts', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '10 days', false, false, 'synced', 1)
ON CONFLICT DO NOTHING;

-- Zadania w wątku 2
INSERT INTO s02_teamwork.tasks (topic_id, task_subject, task_description, assigned_to, created_by, due_date, completed, is_important, sync_status, version)
VALUES 
    (2, 'Utworzyć migrację PostgreSQL', 'Skrypt dodający kolumny sync do istniejących tabel', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE, true, true, 'synced', 1),
    (2, 'Utworzyć migrację SQLite', 'Lokalny skrypt dla bazy offline', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '1 day', false, true, 'synced', 1),
    (2, 'Dodać monitoring synchronizacji', 'Dashboard pokazujący status sync, błędy, nierozwiązane konflikty', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '21 days', false, false, 'synced', 1)
ON CONFLICT DO NOTHING;

-- Zadania w wątku 3 (B2 Integration)
INSERT INTO s02_teamwork.tasks (topic_id, task_subject, task_description, assigned_to, created_by, due_date, completed, is_important, sync_status, version)
VALUES 
    (3, 'Zaimplementować upload plików do B2', 'Funkcja wysyłająca pliki do Backblaze B2 bucket', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '5 days', true, true, 'synced', 1),
    (3, 'Zaimplementować download plików z B2', 'Funkcja pobierająca pliki poprzez public URL', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '5 days', true, false, 'synced', 1),
    (3, 'Dodać preview dla obrazów', 'Wyświetlanie miniaturek obrazów w liście plików', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '14 days', false, false, 'synced', 1),
    (3, 'Dodać usuwanie plików z B2', 'Kaskadowe usuwanie: baza + B2 storage', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', '207222a2-3845-40c2-9bea-cd5bbd6e15f6', CURRENT_DATE + INTERVAL '7 days', false, true, 'synced', 1)
ON CONFLICT DO NOTHING;

-- Resetuj sekwencje ID
SELECT setval('s02_teamwork.work_groups_group_id_seq', (SELECT MAX(group_id) FROM s02_teamwork.work_groups), true);
SELECT setval('s02_teamwork.topics_topic_id_seq', (SELECT MAX(topic_id) FROM s02_teamwork.topics), true);

-- ============================================================================
-- WERYFIKACJA DANYCH
-- ============================================================================

-- Pokaż wszystkie grupy
SELECT g.group_id, g.group_name, g.description, 
       u.name as created_by_name, u.email,
       (SELECT COUNT(*) FROM s02_teamwork.topics WHERE group_id = g.group_id) as topics_count
FROM s02_teamwork.work_groups g
JOIN s01_user_accounts.users u ON g.created_by = u.id
ORDER BY g.group_id;

-- Pokaż wszystkie tematy z liczbą wiadomości i zadań
SELECT t.topic_id, t.topic_name, g.group_name,
       (SELECT COUNT(*) FROM s02_teamwork.messages WHERE topic_id = t.topic_id) as messages_count,
       (SELECT COUNT(*) FROM s02_teamwork.tasks WHERE topic_id = t.topic_id) as tasks_count,
       (SELECT COUNT(*) FROM s02_teamwork.tasks WHERE topic_id = t.topic_id AND completed = true) as completed_tasks
FROM s02_teamwork.topics t
JOIN s02_teamwork.work_groups g ON t.group_id = g.group_id
ORDER BY t.topic_id;

-- Pokaż statystyki
SELECT 
    'Groups' as entity, COUNT(*) as count FROM s02_teamwork.work_groups
UNION ALL
SELECT 'Topics', COUNT(*) FROM s02_teamwork.topics
UNION ALL
SELECT 'Messages', COUNT(*) FROM s02_teamwork.messages
UNION ALL
SELECT 'Tasks', COUNT(*) FROM s02_teamwork.tasks
UNION ALL
SELECT 'Tasks Completed', COUNT(*) FROM s02_teamwork.tasks WHERE completed = true
UNION ALL
SELECT 'Tasks Pending', COUNT(*) FROM s02_teamwork.tasks WHERE completed = false;
