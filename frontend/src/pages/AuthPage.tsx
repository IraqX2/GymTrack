import { useState, type FormEvent } from "react";
import { login, register, type AuthUser } from "../services/api";

interface AuthPageProps {
  onAuthenticated: (user: AuthUser) => void;
}

export default function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const user = mode === "login"
        ? await login(email, password)
        : await register(fullName, email, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function changeMode(nextMode: "login" | "register") {
    setMode(nextMode);
    setError("");
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-brand">
          <span className="brand-icon">GT</span>
          <div><strong>GymTrack</strong><small>GYM MANAGEMENT WORKSPACE</small></div>
        </div>

        <p className="eyebrow auth-eyebrow">YOUR GYM, ORGANIZED</p>
        <h1>{mode === "login" ? "Welcome back." : "Create your account."}</h1>
        <p className="auth-description">
          {mode === "login"
            ? "Sign in to continue to your GymTrack workspace."
            : "Create a GymTrack account to get started. New accounts have the standard user role."}
        </p>

        <div className="auth-tabs" role="tablist" aria-label="Authentication">
          <button
            type="button"
            className={mode === "login" ? "auth-tab selected" : "auth-tab"}
            onClick={() => changeMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === "register" ? "auth-tab selected" : "auth-tab"}
            onClick={() => changeMode("register")}
          >
            Sign up
          </button>
        </div>

        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && (
            <>
              <label htmlFor="auth-name">Full name</label>
              <input
                id="auth-name"
                type="text"
                autoComplete="name"
                minLength={2}
                maxLength={100}
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your name"
                required
              />
            </>
          )}

          <label htmlFor="auth-email">Email address</label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />

          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "register" ? 8 : undefined}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={mode === "register" ? "At least 8 characters" : "Enter your password"}
            required
          />

          {error && <p className="auth-error" role="alert">{error}</p>}

          <button className="auth-submit" type="submit" disabled={busy}>
            {busy ? "Please wait..." : mode === "login" ? "Log in to GymTrack" : "Create account"}
          </button>
        </form>

        <p className="auth-footnote">
          {mode === "login"
            ? "Access is protected by short-lived tokens and server-side permissions."
            : "Public registration creates a standard user account. Administrator accounts are provisioned separately."}
        </p>
      </section>
      <p className="auth-copyright">GYMTRACK · CSE309 PROJECT</p>
    </main>
  );
}
