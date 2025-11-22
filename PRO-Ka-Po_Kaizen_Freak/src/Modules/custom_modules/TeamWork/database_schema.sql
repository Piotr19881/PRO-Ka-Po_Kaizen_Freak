-- ============================================================================
-- SCHEMAT BAZY DANYCH DLA MODUŁU TEAMWORK
-- ============================================================================
-- System zarządzania grupami roboczymi, wątkami, zadaniami i komunikacją
-- ============================================================================

-- Tabela użytkowników
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Tabela zespołów (teams) - zdefiniowane grupy kontaktów
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Członkowie zespołów
CREATE TABLE team_members (
    team_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(team_id, user_id)
);

-- Tabela grup roboczych (groups) - przestrzenie współpracy
CREATE TABLE work_groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name VARCHAR(200) NOT NULL,
    description TEXT,
    team_id INTEGER, -- opcjonalnie powiązany z zespołem
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Członkowie grup roboczych
CREATE TABLE group_members (
    group_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(50) DEFAULT 'member', -- member, admin, owner
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES work_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(group_id, user_id)
);

-- Zaproszenia do grup
CREATE TABLE group_invitations (
    invitation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    invited_email VARCHAR(255) NOT NULL,
    invited_by INTEGER NOT NULL,
    invitation_status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, rejected, cancelled
    invited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    responded_at DATETIME,
    FOREIGN KEY (group_id) REFERENCES work_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES users(user_id)
);

-- Tabela wątków (topics) - dyskusje w ramach grupy
CREATE TABLE topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    topic_name VARCHAR(300) NOT NULL,
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (group_id) REFERENCES work_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Wiadomości w wątkach
CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    background_color VARCHAR(7) DEFAULT '#FFFFFF', -- hex color code
    is_important BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    edited_at DATETIME,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Pliki w wątkach
CREATE TABLE topic_files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size INTEGER, -- w bajtach
    uploaded_by INTEGER NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_important BOOLEAN DEFAULT 0,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- Linki w wątkach
CREATE TABLE topic_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    url VARCHAR(2000) NOT NULL,
    title VARCHAR(500),
    description TEXT,
    added_by INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_important BOOLEAN DEFAULT 0,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(user_id)
);

-- Zadania w wątkach
CREATE TABLE tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    task_subject VARCHAR(500) NOT NULL,
    task_description TEXT,
    assigned_to INTEGER,
    created_by INTEGER NOT NULL,
    due_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT 0,
    completed_by INTEGER,
    completed_at DATETIME,
    is_important BOOLEAN DEFAULT 0,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users(user_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    FOREIGN KEY (completed_by) REFERENCES users(user_id)
);

-- Indeksy dla wydajności
CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);
CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user ON group_members(user_id);
CREATE INDEX idx_group_invitations_email ON group_invitations(invited_email);
CREATE INDEX idx_group_invitations_status ON group_invitations(invitation_status);
CREATE INDEX idx_topics_group ON topics(group_id);
CREATE INDEX idx_messages_topic ON messages(topic_id);
CREATE INDEX idx_messages_important ON messages(is_important);
CREATE INDEX idx_topic_files_topic ON topic_files(topic_id);
CREATE INDEX idx_topic_files_important ON topic_files(is_important);
CREATE INDEX idx_topic_links_topic ON topic_links(topic_id);
CREATE INDEX idx_topic_links_important ON topic_links(is_important);
CREATE INDEX idx_tasks_topic ON tasks(topic_id);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_tasks_important ON tasks(is_important);
CREATE INDEX idx_tasks_completed ON tasks(completed);
