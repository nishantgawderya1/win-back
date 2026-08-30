import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import Logo from "../components/Logo.jsx";

export default function Auth() {
  const { signIn, mode } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error: err } = await signIn(email, password);
    if (err) {
      setError(err);
      setBusy(false);
      return;
    }
    navigate("/onboarding/connect");
  };

  return (
    <div className="auth-card">
      <div className="auth-brand">
        <Logo size={28} />
        <span className="dot dot-on" aria-hidden="true" />
      </div>

      <form onSubmit={submit} className="auth-form">
        <label className="field">
          <span className="field-label mono">EMAIL</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@merchant.in"
            autoComplete="email"
          />
        </label>

        <label className="field">
          <span className="field-label mono">PASSWORD</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </label>

        {error && <p className="error mono">{error}</p>}

        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Signing in…" : "Enter WinBack"}
        </button>
      </form>

      {/* State which mode is in play rather than implying a protection that
          is not there. In demo mode the API answers anonymous callers. */}
      <p className="auth-note mono dim">
        {mode === "supabase"
          ? "Secured by Supabase. The API verifies your token on every request."
          : "Demo mode — no credentials configured, any input is accepted, and the API is open."}
      </p>

      <p className="auth-alt mono">
        <Link className="dim" to="/">
          ← Back to site
        </Link>
      </p>
    </div>
  );
}
