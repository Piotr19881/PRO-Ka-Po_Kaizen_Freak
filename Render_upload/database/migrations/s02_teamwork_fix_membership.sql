-- ============================================================================
-- FIX TEAMWORK MEMBERSHIP
-- ============================================================================
-- Naprawia członkostwo użytkownika w grupach TeamWork
-- ============================================================================

SET search_path TO s02_teamwork;

-- Wyczyść istniejące członkostwa dla tego użytkownika
DELETE FROM s02_teamwork.group_members WHERE user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6';
DELETE FROM s02_teamwork.topic_members WHERE user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6';

-- Dodaj ponownie członkostwa w grupach
INSERT INTO s02_teamwork.group_members (group_id, user_id, role)
VALUES 
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner');

-- Dodaj ponownie członkostwa w tematach
INSERT INTO s02_teamwork.topic_members (topic_id, user_id, role)
VALUES 
    (1, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (2, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (3, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (4, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner'),
    (5, '207222a2-3845-40c2-9bea-cd5bbd6e15f6', 'owner');

-- Weryfikacja
SELECT 'Group memberships:' as info, COUNT(*) as count 
FROM s02_teamwork.group_members 
WHERE user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6';

SELECT 'Topic memberships:' as info, COUNT(*) as count 
FROM s02_teamwork.topic_members 
WHERE user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6';

-- Pokaż grupy użytkownika
SELECT g.group_id, g.group_name, gm.role
FROM s02_teamwork.work_groups g
JOIN s02_teamwork.group_members gm ON g.group_id = gm.group_id
WHERE gm.user_id = '207222a2-3845-40c2-9bea-cd5bbd6e15f6';
