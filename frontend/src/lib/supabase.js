import { createClient } from "@supabase/supabase-js";

/**
 * Supabase client, or null when the app has no credentials configured.
 *
 * A clean checkout has no keys, and the demo must still run — so this returns
 * null rather than throwing, and AuthContext falls back to a clearly-labelled
 * demo session. `isSupabaseAuth` is what the UI checks before claiming that
 * sign-in is real.
 *
 * The anon key is designed to be public: it identifies the project and carries
 * no privileges beyond what row-level security allows. The service_role key is
 * the dangerous one and must never appear in frontend code.
 */
const url = import.meta.env.VITE_SUPABASE_URL || "";
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export const isSupabaseAuth = Boolean(url && anonKey);

export const supabase = isSupabaseAuth
  ? createClient(url, anonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false,
      },
    })
  : null;

/** Current access token, or null. Read fresh so a refreshed token is picked up. */
export async function getAccessToken() {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token ?? null;
}
