-- =====================================================
-- SQL CLEANUP SCRIPT - Błędne note_links
-- =====================================================
-- Data: 2025-11-03
-- Problem: start_position == end_position (długość 0)
-- Constraint: links_position_valid wymaga start_position < end_position
-- =====================================================

-- KROK 1: Sprawdź błędne rekordy
SELECT 
    id,
    source_note_id,
    target_note_id,
    link_text,
    start_position,
    end_position,
    (end_position - start_position) as link_length,
    created_at
FROM s06_notes.note_links
WHERE start_position >= end_position  -- Złe dane
ORDER BY created_at DESC;

-- KROK 2: Usuń błędne rekordy
-- UWAGA: Wykonaj tylko jeśli KROK 1 pokazał błędne dane!

DELETE FROM s06_notes.note_links
WHERE start_position >= end_position;

-- KROK 3: Weryfikacja
SELECT COUNT(*) as total_links,
       MIN(end_position - start_position) as min_length,
       MAX(end_position - start_position) as max_length,
       AVG(end_position - start_position) as avg_length
FROM s06_notes.note_links;

-- Oczekiwany wynik: min_length > 0
