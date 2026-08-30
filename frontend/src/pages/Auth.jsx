import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Auth() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = (e) => {
    e.preventDefault();
    signIn(email);
    navigate("/onboarding/connect");
  };

  return (
    <div className="auth-card">
      <div className="auth-brand">
        <span className="wordmark">
          WinBack<span className="wordmark-ai">AI</span>
        </span>
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

        <button type="submit" className="btn btn-primary btn-block">
          Enter WinBack
        </button>
      </form>

      <p className="auth-note mono dim">
        Demo build — no account is created and no credential is checked or stored.
      </p>

      <p className="auth-alt mono">
        <Link to="/onboarding/connect">New to WinBack? Connect your Razorpay account →</Link>
      </p>
      <p className="auth-alt mono">
        <Link className="dim" to="/">
          ← Back to site
        </Link>
      </p>
    </div>
  );
}
