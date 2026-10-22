import { FormEvent, useState } from "react";
import { createUserWithEmailAndPassword, sendPasswordResetEmail, signInWithEmailAndPassword } from "firebase/auth";
import { getFirebaseServices } from "../firebase";
import { Icon, Logo } from "../icons";
import { Link } from "../router";

function friendly(code: string): string {
  if (code.includes("invalid-credential") || code.includes("wrong-password") || code.includes("user-not-found")) return "Email or password is incorrect.";
  if (code.includes("email-already-in-use")) return "An account with this email already exists. Sign in instead.";
  if (code.includes("weak-password")) return "Use at least 6 characters for your password.";
  if (code.includes("invalid-email")) return "That email address doesn't look right.";
  if (code.includes("network")) return "You seem to be offline. Check your connection and try again.";
  if (code.includes("too-many-requests")) return "Too many attempts. Please wait a moment and try again.";
  return "We couldn't sign you in. Please try again.";
}

export default function LoginPage() {
  const [mode, setMode] = useState<"signin" | "signup">(new URLSearchParams(window.location.search).has("new") ? "signup" : "signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setNotice(""); setBusy(true);
    try {
      const { auth } = getFirebaseServices();
      if (mode === "signup") await createUserWithEmailAndPassword(auth, email, password);
      else await signInWithEmailAndPassword(auth, email, password);
    } catch (cause) {
      setError(friendly((cause as { code?: string }).code ?? ""));
      setBusy(false);
    }
  }

  async function reset() {
    if (!email) { setError("Enter your email first, then press “Forgot password”."); return; }
    try {
      await sendPasswordResetEmail(getFirebaseServices().auth, email);
      setNotice(`If an account exists for ${email}, a reset link is on its way.`);
    } catch (cause) {
      setError(friendly((cause as { code?: string }).code ?? ""));
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-art">
        <video src="/showcase/movie-lipsync.mp4" poster="/showcase/movie-lipsync.jpg" autoPlay muted loop playsInline />
        <div className="auth-art-copy">
          <Logo />
          <h2>Movies, stories and reels from a single idea.</h2>
          <p>In your language, with your brand, ready for Instagram.</p>
        </div>
      </div>
      <div className="auth-side">
        <Link to="/" className="back-link"><Icon name="arrowRight" className="icon flip" /> Back to home</Link>
        <form className="auth-form" onSubmit={submit}>
          <h1>{mode === "signin" ? "Welcome back" : "Create your account"}</h1>
          <p>{mode === "signin" ? "Sign in to your studio." : "Start turning ideas into videos in minutes."}</p>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete={mode === "signin" ? "current-password" : "new-password"} minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} required />
          {mode === "signin" && <button type="button" className="link-btn" onClick={() => void reset()}>Forgot password?</button>}
          {error && <div role="alert" className="message error">{error}</div>}
          {notice && <div role="status" className="message success">{notice}</div>}
          <button className="btn btn-primary btn-lg" type="submit" disabled={busy}>
            {busy ? <span className="spinner" /> : mode === "signin" ? "Sign in" : "Create account"}
          </button>
          <button type="button" className="link-btn center" onClick={() => { setError(""); setMode(mode === "signin" ? "signup" : "signin"); }}>
            {mode === "signin" ? "New here? Create an account" : "Already have an account? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
