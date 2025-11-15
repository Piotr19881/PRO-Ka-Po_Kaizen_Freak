-- ============================================================================
-- ZAPYTANIA SQL DLA MODUŁU TEAMWORK
-- ============================================================================
-- Kolekcja najważniejszych operacji CRUD i zapytań dla aplikacji
-- ============================================================================

-- ============================================================================
-- 1. ZARZĄDZANIE UŻYTKOWNIKAMI I KONTAKTAMI
-- ============================================================================

-- Dodaj nowego użytkownika/kontakt
INSERT INTO users (email, first_name, last_name)
VALUES (?, ?, ?);

-- Pobierz wszystkich użytkowników
SELECT user_id, email, first_name, last_name, created_at, is_active
FROM users
WHERE is_active = 1
ORDER BY last_name, first_name;

-- Znajdź użytkownika po emailu
SELECT user_id, email, first_name, last_name
FROM users
WHERE email = ? AND is_active = 1;

-- Aktualizuj dane użytkownika
UPDATE users
SET first_name = ?, last_name = ?
WHERE user_id = ?;

-- Dezaktywuj użytkownika (soft delete)
UPDATE users
SET is_active = 0
WHERE user_id = ?;


-- ============================================================================
-- 2. ZARZĄDZANIE ZESPOŁAMI (TEAMS)
-- ============================================================================

-- Utwórz nowy zespół
INSERT INTO teams (team_name, description, created_by)
VALUES (?, ?, ?);

-- Pobierz wszystkie zespoły
SELECT t.team_id, t.team_name, t.description, t.created_at,
       u.first_name || ' ' || u.last_name AS created_by_name,
       COUNT(tm.user_id) AS members_count
FROM teams t
LEFT JOIN users u ON t.created_by = u.user_id
LEFT JOIN team_members tm ON t.team_id = tm.team_id
GROUP BY t.team_id
ORDER BY t.team_name;

-- Dodaj członka do zespołu
INSERT INTO team_members (team_id, user_id)
VALUES (?, ?);

-- Usuń członka z zespołu
DELETE FROM team_members
WHERE team_id = ? AND user_id = ?;

-- Pobierz członków zespołu
SELECT u.user_id, u.email, u.first_name, u.last_name, tm.added_at
FROM team_members tm
JOIN users u ON tm.user_id = u.user_id
WHERE tm.team_id = ?
ORDER BY u.last_name, u.first_name;

-- Pobierz zespoły użytkownika
SELECT t.team_id, t.team_name, t.description
FROM teams t
JOIN team_members tm ON t.team_id = tm.team_id
WHERE tm.user_id = ?
ORDER BY t.team_name;

-- Usuń zespół
DELETE FROM teams
WHERE team_id = ?;


-- ============================================================================
-- 3. ZARZĄDZANIE GRUPAMI ROBOCZYMI (WORK GROUPS)
-- ============================================================================

-- Utwórz nową grupę roboczą
INSERT INTO work_groups (group_name, description, team_id, created_by)
VALUES (?, ?, ?, ?);

-- Pobierz wszystkie grupy użytkownika
SELECT wg.group_id, wg.group_name, wg.description, wg.created_at,
       COUNT(gm.user_id) AS members_count,
       CASE 
           WHEN gm.user_id = ? THEN 'Członek'
           ELSE 'Brak dostępu'
       END AS user_status
FROM work_groups wg
LEFT JOIN group_members gm ON wg.group_id = gm.group_id
WHERE wg.is_active = 1 
  AND (wg.created_by = ? OR gm.user_id = ?)
GROUP BY wg.group_id
ORDER BY wg.group_name;

-- Pobierz szczegóły grupy
SELECT wg.group_id, wg.group_name, wg.description, wg.created_at,
       u.first_name || ' ' || u.last_name AS created_by_name,
       t.team_name
FROM work_groups wg
JOIN users u ON wg.created_by = u.user_id
LEFT JOIN teams t ON wg.team_id = t.team_id
WHERE wg.group_id = ? AND wg.is_active = 1;

-- Dodaj członka do grupy
INSERT INTO group_members (group_id, user_id, role)
VALUES (?, ?, ?);

-- Usuń członka z grupy (opuść grupę)
DELETE FROM group_members
WHERE group_id = ? AND user_id = ?;

-- Pobierz członków grupy
SELECT u.user_id, u.email, u.first_name, u.last_name, 
       gm.role, gm.joined_at
FROM group_members gm
JOIN users u ON gm.user_id = u.user_id
WHERE gm.group_id = ?
ORDER BY gm.role DESC, u.last_name, u.first_name;

-- Sprawdź czy użytkownik jest członkiem grupy
SELECT COUNT(*) AS is_member
FROM group_members
WHERE group_id = ? AND user_id = ?;


-- ============================================================================
-- 4. ZAPROSZENIA DO GRUP
-- ============================================================================

-- Wyślij zaproszenie do grupy
INSERT INTO group_invitations (group_id, invited_email, invited_by)
VALUES (?, ?, ?);

-- Pobierz zaproszenia dla użytkownika (po emailu)
SELECT gi.invitation_id, gi.invitation_status, gi.invited_at,
       wg.group_id, wg.group_name, wg.description,
       u.first_name || ' ' || u.last_name AS invited_by_name
FROM group_invitations gi
JOIN work_groups wg ON gi.group_id = wg.group_id
JOIN users u ON gi.invited_by = u.user_id
WHERE gi.invited_email = ? 
  AND gi.invitation_status = 'pending'
ORDER BY gi.invited_at DESC;

-- Akceptuj zaproszenie
UPDATE group_invitations
SET invitation_status = 'accepted', responded_at = CURRENT_TIMESTAMP
WHERE invitation_id = ?;

-- Następnie dodaj do grupy:
-- INSERT INTO group_members (group_id, user_id) VALUES (?, ?);

-- Odrzuć zaproszenie
UPDATE group_invitations
SET invitation_status = 'rejected', responded_at = CURRENT_TIMESTAMP
WHERE invitation_id = ?;

-- Pobierz oczekujące zaproszenia dla grupy
SELECT gi.invitation_id, gi.invited_email, gi.invited_at,
       u.first_name || ' ' || u.last_name AS invited_by_name
FROM group_invitations gi
JOIN users u ON gi.invited_by = u.user_id
WHERE gi.group_id = ? AND gi.invitation_status = 'pending'
ORDER BY gi.invited_at DESC;

-- Anuluj zaproszenie
UPDATE group_invitations
SET invitation_status = 'cancelled', responded_at = CURRENT_TIMESTAMP
WHERE invitation_id = ? AND invited_by = ?;


-- ============================================================================
-- 5. ZARZĄDZANIE WĄTKAMI (TOPICS)
-- ============================================================================

-- Utwórz nowy wątek
INSERT INTO topics (group_id, topic_name, created_by)
VALUES (?, ?, ?);

-- Pobierz wątki z grupy
SELECT t.topic_id, t.topic_name, t.created_at,
       u.first_name || ' ' || u.last_name AS created_by_name,
       COUNT(DISTINCT m.message_id) AS messages_count,
       MAX(m.created_at) AS last_activity
FROM topics t
JOIN users u ON t.created_by = u.user_id
LEFT JOIN messages m ON t.topic_id = m.topic_id
WHERE t.group_id = ? AND t.is_active = 1
GROUP BY t.topic_id
ORDER BY last_activity DESC NULLS LAST, t.created_at DESC;

-- Pobierz szczegóły wątku
SELECT t.topic_id, t.topic_name, t.created_at,
       u.first_name || ' ' || u.last_name AS created_by_name,
       wg.group_name
FROM topics t
JOIN users u ON t.created_by = u.user_id
JOIN work_groups wg ON t.group_id = wg.group_id
WHERE t.topic_id = ? AND t.is_active = 1;

-- Dezaktywuj wątek
UPDATE topics
SET is_active = 0
WHERE topic_id = ?;


-- ============================================================================
-- 6. WIADOMOŚCI W WĄTKACH
-- ============================================================================

-- Dodaj wiadomość do wątku
INSERT INTO messages (topic_id, user_id, content, background_color, is_important)
VALUES (?, ?, ?, ?, ?);

-- Pobierz wiadomości z wątku
SELECT m.message_id, m.content, m.background_color, m.is_important,
       m.created_at, m.edited_at,
       u.user_id, u.first_name || ' ' || u.last_name AS author_name
FROM messages m
JOIN users u ON m.user_id = u.user_id
WHERE m.topic_id = ?
ORDER BY m.created_at ASC;

-- Pobierz tylko ważne wiadomości z wątku
SELECT m.message_id, m.content, m.background_color, m.created_at,
       u.first_name || ' ' || u.last_name AS author_name
FROM messages m
JOIN users u ON m.user_id = u.user_id
WHERE m.topic_id = ? AND m.is_important = 1
ORDER BY m.created_at ASC;

-- Oznacz wiadomość jako ważną/nieważną
UPDATE messages
SET is_important = ?
WHERE message_id = ?;

-- Edytuj wiadomość
UPDATE messages
SET content = ?, edited_at = CURRENT_TIMESTAMP
WHERE message_id = ? AND user_id = ?;

-- Usuń wiadomość
DELETE FROM messages
WHERE message_id = ? AND user_id = ?;


-- ============================================================================
-- 7. PLIKI W WĄTKACH
-- ============================================================================

-- Dodaj plik do wątku
INSERT INTO topic_files (topic_id, file_name, file_path, file_size, uploaded_by, is_important)
VALUES (?, ?, ?, ?, ?, ?);

-- Pobierz pliki z wątku
SELECT f.file_id, f.file_name, f.file_path, f.file_size, f.uploaded_at, f.is_important,
       u.first_name || ' ' || u.last_name AS uploaded_by_name
FROM topic_files f
JOIN users u ON f.uploaded_by = u.user_id
WHERE f.topic_id = ?
ORDER BY f.uploaded_at DESC;

-- Pobierz tylko ważne pliki z wątku
SELECT f.file_id, f.file_name, f.file_path, f.uploaded_at,
       u.first_name || ' ' || u.last_name AS uploaded_by_name
FROM topic_files f
JOIN users u ON f.uploaded_by = u.user_id
WHERE f.topic_id = ? AND f.is_important = 1
ORDER BY f.uploaded_at DESC;

-- Oznacz plik jako ważny/nieważny
UPDATE topic_files
SET is_important = ?
WHERE file_id = ?;

-- Usuń plik
DELETE FROM topic_files
WHERE file_id = ? AND uploaded_by = ?;


-- ============================================================================
-- 8. LINKI W WĄTKACH
-- ============================================================================

-- Dodaj link do wątku
INSERT INTO topic_links (topic_id, url, title, description, added_by, is_important)
VALUES (?, ?, ?, ?, ?, ?);

-- Pobierz linki z wątku
SELECT l.link_id, l.url, l.title, l.description, l.added_at, l.is_important,
       u.first_name || ' ' || u.last_name AS added_by_name
FROM topic_links l
JOIN users u ON l.added_by = u.user_id
WHERE l.topic_id = ?
ORDER BY l.added_at DESC;

-- Pobierz tylko ważne linki z wątku
SELECT l.link_id, l.url, l.title, l.description, l.added_at,
       u.first_name || ' ' || u.last_name AS added_by_name
FROM topic_links l
JOIN users u ON l.added_by = u.user_id
WHERE l.topic_id = ? AND l.is_important = 1
ORDER BY l.added_at DESC;

-- Oznacz link jako ważny/nieważny
UPDATE topic_links
SET is_important = ?
WHERE link_id = ?;

-- Usuń link
DELETE FROM topic_links
WHERE link_id = ? AND added_by = ?;


-- ============================================================================
-- 9. ZADANIA
-- ============================================================================

-- Utwórz nowe zadanie
INSERT INTO tasks (topic_id, task_subject, task_description, assigned_to, created_by, due_date, is_important)
VALUES (?, ?, ?, ?, ?, ?, ?);

-- Pobierz zadania z wątku
SELECT t.task_id, t.task_subject, t.task_description, t.due_date, t.completed,
       t.created_at, t.completed_at, t.is_important,
       u_created.first_name || ' ' || u_created.last_name AS created_by_name,
       u_assigned.first_name || ' ' || u_assigned.last_name AS assigned_to_name,
       u_completed.first_name || ' ' || u_completed.last_name AS completed_by_name
FROM tasks t
JOIN users u_created ON t.created_by = u_created.user_id
LEFT JOIN users u_assigned ON t.assigned_to = u_assigned.user_id
LEFT JOIN users u_completed ON t.completed_by = u_completed.user_id
WHERE t.topic_id = ?
ORDER BY t.completed ASC, t.due_date ASC, t.created_at DESC;

-- Pobierz tylko ważne zadania z wątku
SELECT t.task_id, t.task_subject, t.due_date, t.completed,
       u_assigned.first_name || ' ' || u_assigned.last_name AS assigned_to_name
FROM tasks t
LEFT JOIN users u_assigned ON t.assigned_to = u_assigned.user_id
WHERE t.topic_id = ? AND t.is_important = 1
ORDER BY t.completed ASC, t.due_date ASC;

-- Oznacz zadanie jako ukończone
UPDATE tasks
SET completed = 1, completed_by = ?, completed_at = CURRENT_TIMESTAMP
WHERE task_id = ?;

-- Oznacz zadanie jako nieukończone
UPDATE tasks
SET completed = 0, completed_by = NULL, completed_at = NULL
WHERE task_id = ?;

-- Oznacz zadanie jako ważne/nieważne
UPDATE tasks
SET is_important = ?
WHERE task_id = ?;

-- Pobierz zadania przypisane do użytkownika
SELECT t.task_id, t.task_subject, t.task_description, t.due_date, t.completed,
       top.topic_name, wg.group_name,
       u_created.first_name || ' ' || u_created.last_name AS created_by_name
FROM tasks t
JOIN topics top ON t.topic_id = top.topic_id
JOIN work_groups wg ON top.group_id = wg.group_id
JOIN users u_created ON t.created_by = u_created.user_id
WHERE t.assigned_to = ? AND t.completed = 0
ORDER BY t.due_date ASC NULLS LAST, t.created_at DESC;

-- Aktualizuj zadanie
UPDATE tasks
SET task_subject = ?, task_description = ?, assigned_to = ?, due_date = ?
WHERE task_id = ? AND created_by = ?;

-- Usuń zadanie
DELETE FROM tasks
WHERE task_id = ? AND created_by = ?;


-- ============================================================================
-- 10. ZAPYTANIA ZŁOŻONE I STATYSTYKI
-- ============================================================================

-- Pobierz wszystkie ważne elementy z wątku (wiadomości + pliki + linki + zadania)
-- Wiadomości
SELECT 'message' AS type, m.message_id AS item_id, 
       SUBSTR(m.content, 1, 100) AS preview, m.created_at,
       u.first_name || ' ' || u.last_name AS author_name
FROM messages m
JOIN users u ON m.user_id = u.user_id
WHERE m.topic_id = ? AND m.is_important = 1

UNION ALL

-- Pliki
SELECT 'file' AS type, f.file_id AS item_id,
       f.file_name AS preview, f.uploaded_at AS created_at,
       u.first_name || ' ' || u.last_name AS author_name
FROM topic_files f
JOIN users u ON f.uploaded_by = u.user_id
WHERE f.topic_id = ? AND f.is_important = 1

UNION ALL

-- Linki
SELECT 'link' AS type, l.link_id AS item_id,
       COALESCE(l.title, l.url) AS preview, l.added_at AS created_at,
       u.first_name || ' ' || u.last_name AS author_name
FROM topic_links l
JOIN users u ON l.added_by = u.user_id
WHERE l.topic_id = ? AND l.is_important = 1

UNION ALL

-- Zadania
SELECT 'task' AS type, t.task_id AS item_id,
       t.task_subject AS preview, t.created_at,
       u.first_name || ' ' || u.last_name AS author_name
FROM tasks t
JOIN users u ON t.created_by = u.user_id
WHERE t.topic_id = ? AND t.is_important = 1

ORDER BY created_at ASC;

-- Statystyki grupy
SELECT 
    wg.group_name,
    COUNT(DISTINCT gm.user_id) AS members_count,
    COUNT(DISTINCT t.topic_id) AS topics_count,
    COUNT(DISTINCT m.message_id) AS messages_count,
    COUNT(DISTINCT tk.task_id) AS total_tasks,
    SUM(CASE WHEN tk.completed = 1 THEN 1 ELSE 0 END) AS completed_tasks
FROM work_groups wg
LEFT JOIN group_members gm ON wg.group_id = gm.group_id
LEFT JOIN topics t ON wg.group_id = t.group_id AND t.is_active = 1
LEFT JOIN messages m ON t.topic_id = m.topic_id
LEFT JOIN tasks tk ON t.topic_id = tk.topic_id
WHERE wg.group_id = ?
GROUP BY wg.group_id;

-- Aktywność w grupie (ostatnie akcje)
SELECT 'message' AS activity_type, m.created_at AS activity_time,
       u.first_name || ' ' || u.last_name AS user_name,
       top.topic_name,
       SUBSTR(m.content, 1, 100) AS details
FROM messages m
JOIN users u ON m.user_id = u.user_id
JOIN topics top ON m.topic_id = top.topic_id
WHERE top.group_id = ?

UNION ALL

SELECT 'file' AS activity_type, f.uploaded_at AS activity_time,
       u.first_name || ' ' || u.last_name AS user_name,
       top.topic_name,
       f.file_name AS details
FROM topic_files f
JOIN users u ON f.uploaded_by = u.user_id
JOIN topics top ON f.topic_id = top.topic_id
WHERE top.group_id = ?

UNION ALL

SELECT 'task' AS activity_type, t.created_at AS activity_time,
       u.first_name || ' ' || u.last_name AS user_name,
       top.topic_name,
       t.task_subject AS details
FROM tasks t
JOIN users u ON t.created_by = u.user_id
JOIN topics top ON t.topic_id = top.topic_id
WHERE top.group_id = ?

ORDER BY activity_time DESC
LIMIT 20;

-- Pobierz grupy z liczbą oczekujących zaproszeń dla użytkownika
SELECT wg.group_id, wg.group_name, wg.description,
       COUNT(gm.user_id) AS members_count,
       CASE 
           WHEN gi.invitation_id IS NOT NULL THEN 'Zaproszenie oczekujące'
           WHEN gm.user_id IS NOT NULL THEN 'Członek'
           ELSE 'Brak dostępu'
       END AS status
FROM work_groups wg
LEFT JOIN group_members gm ON wg.group_id = gm.group_id AND gm.user_id = ?
LEFT JOIN group_invitations gi ON wg.group_id = gi.group_id 
    AND gi.invited_email = (SELECT email FROM users WHERE user_id = ?)
    AND gi.invitation_status = 'pending'
WHERE wg.is_active = 1
GROUP BY wg.group_id
ORDER BY status DESC, wg.group_name;
