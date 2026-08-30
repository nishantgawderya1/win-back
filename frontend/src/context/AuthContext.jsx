import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { isSupabaseAuth, supabase } from "../lib/supabase.js";

/**
 * Session state, backed by Supabase when it is configured.
 *
 * Two modes, and the UI is told which is in play rather than pretending:
 *
 *   real  — Supabase email/password. The access token is attached to every API
 *           call and the backend verifies it, so signing out actually revokes
 *           access rather than hiding a button.
 *   demo  — no credentials configured. Any input is accepted and the session
 *           lives in localStorage. The API is open in this mode; the app says
 *           so instead of implying a protection that is not there.
 *
 * The Razorpay key secret is never stored in either mode. Onboarding accepts
 * it, uses it to mark the account connected, and drops it — only the masked
 * key id is kept, which is all any screen displays.
 */
const KEY = "winback.session";

const AuthContext = createContext(null);

function readLocal() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "null");
  } catch {
    return null;
  }
}

function writeLocal(session) {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch {
    /* private mode / blocked storage — session is then in-memory only */
  }
}

export function AuthProvider({ children }) {
  // Profile data (onboarding progress, masked key id) is ours either way; the
  // identity underneath it is Supabase's when configured.
  const [profile, setProfile] = useState(readLocal);
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!isSupabaseAuth);

  useEffect(() => {
    if (!supabase) return undefined;
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setUser(data?.session?.user ?? null);
      setReady(true);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (!session) {
        setProfile(null);
        writeLocal(null);
      }
    });

    return () => {
      active = false;
      sub?.subscription?.unsubscribe();
    };
  }, []);

  const update = useCallback((next) => {
    setProfile(next);
    writeLocal(next);
  }, []);

  const value = useMemo(() => {
    const isAuthed = isSupabaseAuth ? Boolean(user) : Boolean(profile);
    const email = user?.email || profile?.email || null;

    return {
      mode: isSupabaseAuth ? "supabase" : "demo",
      ready,
      isAuthed,
      isOnboarded: Boolean(profile?.onboarded),
      session: profile ? { ...profile, email } : email ? { email } : null,

      /** Returns { error } so the form can show why a sign-in failed. */
      signIn: async (emailInput, password) => {
        if (!supabase) {
          update({
            email: emailInput || "merchant@example.com",
            onboarded: false,
            keyIdMasked: null,
            mode: null,
          });
          return { error: null };
        }
        const { data, error } = await supabase.auth.signInWithPassword({
          email: emailInput,
          password,
        });
        if (error) return { error: error.message };
        setUser(data.user);
        if (!readLocal()) {
          update({ email: emailInput, onboarded: false, keyIdMasked: null, mode: null });
        }
        return { error: null };
      },

      signUp: async (emailInput, password) => {
        if (!supabase) return { error: "Sign-up needs Supabase credentials." };
        const { error } = await supabase.auth.signUp({ email: emailInput, password });
        return { error: error ? error.message : null };
      },

      // `secret` is received and deliberately discarded — see the note above.
      connectRazorpay: (keyId) =>
        update({
          ...(profile || {}),
          email,
          keyIdMasked: keyId
            ? `${keyId.slice(0, 9)}${"*".repeat(4)}${keyId.slice(-4)}`
            : null,
        }),
      chooseMode: (m) => update({ ...(profile || {}), email, mode: m }),
      finishOnboarding: () => update({ ...(profile || {}), email, onboarded: true }),

      signOut: async () => {
        if (supabase) await supabase.auth.signOut();
        setUser(null);
        update(null);
      },
    };
  }, [profile, user, ready, update]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
