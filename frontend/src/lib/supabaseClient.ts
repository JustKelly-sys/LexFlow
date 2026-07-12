import { createClient } from '@supabase/supabase-js';

// Keys loaded from environment variables (set in .env or hosting platform)
// NOTE: The Supabase anon key is designed to be public (like a Firebase API key).
// It only grants access through Row Level Security policies — no real data is
// exposed without a valid authenticated session. The service key is NEVER
// shipped to the browser.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY environment variables. ' +
    'Copy .env.example to .env and fill in your Supabase project values.'
  );
}

export const supabase = createClient(supabaseUrl ?? '', supabaseAnonKey ?? '');
