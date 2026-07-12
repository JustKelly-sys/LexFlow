-- LexFlow Database Migration
-- Fixes audit items #4 (data isolation) and #9 (link code expiry)
-- Run in Supabase SQL Editor (Dashboard > SQL Editor > New Query)

-- #4: Add wa_phone column to billing_entries for data isolation
ALTER TABLE billing_entries ADD COLUMN IF NOT EXISTS wa_phone TEXT;

-- #9: Add link_code_expires_at column to whatsapp_users
ALTER TABLE whatsapp_users ADD COLUMN IF NOT EXISTS link_code_expires_at TIMESTAMPTZ;

-- #16: Add source column (may already exist)
ALTER TABLE billing_entries ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'web';
