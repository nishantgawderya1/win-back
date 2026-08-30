import { createContext, useCallback, useContext, useMemo, useState } from "react";

/**
 * Demo-only session.
 *
 * There is no users table, no password hashing and no server session behind
 * this — it exists so the product can be walked end to end. Any credentials
 * are accepted.
 *
 * The Razorpay key SECRET is deliberately never stored. It is accepted by the
 * onboarding form, used to mark the account connected, and then dropped. Only
 * the masked key id survives, which is all any screen needs to display.
 */
const KEY = "winback.session";

const AuthContext = createContext(null);

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "null");
  } catch {
    return null;
  }
}

function write(session) {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch {
    /* private mode / blocked storage — session is then in-memory only */
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(read);

  const update = useCallback((next) => {
    setSession(next);
    write(next);
  }, []);

  const value = useMemo(
    () => ({
      session,
      isAuthed: Boolean(session),
      isOnboarded: Boolean(session?.onboarded),
      signIn: (email) =>
        update({
          email: email || "merchant@example.com",
          onboarded: false,
          keyIdMasked: null,
          mode: null,
        }),
      // Called at the end of onboarding step 1. `secret` is intentionally
      // received and discarded — see the note above.
      connectRazorpay: (keyId) =>
        update({
          ...(session || {}),
          keyIdMasked: keyId
            ? `${keyId.slice(0, 9)}${"*".repeat(4)}${keyId.slice(-4)}`
            : null,
        }),
      chooseMode: (mode) => update({ ...(session || {}), mode }),
      finishOnboarding: () => update({ ...(session || {}), onboarded: true }),
      signOut: () => update(null),
    }),
    [session, update]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
