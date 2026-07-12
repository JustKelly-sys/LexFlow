-- 002: Prevent duplicate WhatsApp user rows when two messages from the same
-- number arrive concurrently (the webhook get-or-create has a race window).
-- Run in the Supabase SQL Editor.

-- Remove any existing duplicates first (keep the oldest row per phone)
DELETE FROM whatsapp_users a
USING whatsapp_users b
WHERE a.phone = b.phone
  AND a.ctid > b.ctid;

ALTER TABLE whatsapp_users
  ADD CONSTRAINT whatsapp_users_phone_key UNIQUE (phone);
