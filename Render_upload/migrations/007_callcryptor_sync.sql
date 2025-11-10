-- ============================================================
-- Migration 007: CallCryptor Sync
-- Created: 2025-11-09
-- Description: Dodaje schema s07_callcryptor dla synchronizacji nagrań
--              Privacy-first: tylko metadane, pliki audio lokalne
-- ============================================================

\i database/s07_callcryptor_schema.sql;

-- ============================================================
-- Verification
-- ============================================================

-- Verify schema created
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 's07_callcryptor') THEN
        RAISE NOTICE '✅ Schema s07_callcryptor created successfully';
    ELSE
        RAISE EXCEPTION '❌ Schema s07_callcryptor not found';
    END IF;
END $$;

-- Verify tables created
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 's07_callcryptor' 
               AND table_name = 'recording_sources') THEN
        RAISE NOTICE '✅ Table recording_sources created';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 's07_callcryptor' 
               AND table_name = 'recordings') THEN
        RAISE NOTICE '✅ Table recordings created';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 's07_callcryptor' 
               AND table_name = 'recording_tags') THEN
        RAISE NOTICE '✅ Table recording_tags created';
    END IF;
END $$;

-- Verify RLS enabled
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables 
               WHERE schemaname = 's07_callcryptor' 
               AND tablename = 'recordings' 
               AND rowsecurity = true) THEN
        RAISE NOTICE '✅ RLS enabled on recordings';
    END IF;
END $$;
